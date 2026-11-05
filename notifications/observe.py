"""Read-only production deployment observer; never calls Kit or writes GitHub.

Fetches public website bytes and GitHub metadata. Does not execute source from
the deployment being inspected. Output contains only public release information.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.request import Request, build_opener
from urllib.error import HTTPError
from urllib.parse import urlsplit
from notifier import BASE, REPO, WORKFLOW, PAGES, Refused, snapshot, deployment_gate
from services import NoRedirect

APPROVED_WORKFLOW_HASH = 'defc1d6f8647f98f5064a9f896c220deda5f3f9f8b703519926e8cdf8b7698d6'
RAW = 'https://raw.githubusercontent.com/'+REPO+'/'

def get_public(url):
    if not (url.startswith(BASE) or url.startswith(RAW)): raise Refused('Unexpected fetch destination')
    request = Request(url,headers={'User-Agent':'MrMagic-read-only-notification-prototype','Cache-Control':'no-cache'})
    with build_opener(NoRedirect()).open(request,timeout=30) as response:
        if urlsplit(response.url).netloc != urlsplit(url).netloc: raise Refused('Unexpected redirect')
        result=response.read(12*1024*1024+1)
        if len(result)>12*1024*1024: raise Refused('Public asset too large')
        return result

def gh(path):
    executable=shutil.which('gh') or r'C:\Program Files\GitHub CLI\gh.exe'
    proc=subprocess.run([executable,'api','repos/'+REPO+'/'+path],capture_output=True,text=True,encoding='utf-8')
    if proc.returncode: raise Refused('Read-only GitHub API request failed; details suppressed')
    return json.loads(proc.stdout)

def observe(run_id, output=None):
    if not re.fullmatch(r'\d+',str(run_id)):raise Refused('Numeric run ID required')
    run=gh('actions/runs/'+str(run_id))
    if any([run.get('name')!=WORKFLOW,run.get('event')!='workflow_dispatch',run.get('head_branch')!='main',
            run.get('status')!='completed',run.get('conclusion')!='success',
            run.get('head_repository',{}).get('full_name')!=REPO,
            run.get('actor',{}).get('login')!=REPO.split('/')[0]]):raise Refused('Run is not an approved production release')
    sha=run['head_sha']
    if not re.fullmatch('[0-9a-f]{40}',sha):raise Refused('Unexpected commit')
    workflow=get_public(RAW+sha+'/.github/workflows/pages.yml')
    if hashlib.sha256(workflow).hexdigest()!=APPROVED_WORKFLOW_HASH:raise Refused('Deployment workflow changed; review required')
    jobs=gh('actions/runs/'+str(run_id)+'/jobs?per_page=100')['jobs']
    if not any(j['name']=='deploy' and j['conclusion']=='success' for j in jobs):raise Refused('Pages deployment job did not succeed')
    latest=gh('actions/workflows/pages.yml/runs?status=success&branch=main&per_page=1')['workflow_runs'][0]
    if latest['head_sha']!=sha:raise Refused('Superseded production release')
    manifest=json.loads(get_public(RAW+sha+'/release-manifest.json'))
    records=manifest['files'];names=[r['file'] for r in records]
    if len(names)!=len(set(names)) or not set(PAGES)<=set(names):raise Refused('Invalid inventory')
    for r in records:
        name=r['file']
        if not re.fullmatch('[A-Za-z0-9._/-]+',name) or any(x in ('','..','.') for x in name.split('/')):raise Refused('Unsafe public file path')
        if not re.fullmatch('[0-9a-f]{64}',r['sha256']):raise Refused('Invalid file hash')
    canonical=''.join(r['file']+'\t'+r['sha256']+'\n' for r in sorted(records,key=lambda r:r['file']))
    inv=hashlib.sha256(canonical.encode()).hexdigest()
    if inv!=manifest['site_inventory_sha256']:raise Refused('Manifest mismatch')
    total=0
    with tempfile.TemporaryDirectory() as temp:
        for r in records:
            content=get_public(BASE+r['file']);total+=len(content)
            if total>60*1024*1024:raise Refused('Website size limit exceeded')
            if len(content)!=r['bytes'] or hashlib.sha256(content).hexdigest()!=r['sha256']:raise Refused('Live website differs from release inventory')
            if r['file'] in PAGES:(Path(temp)/r['file']).write_bytes(content)
        snap=snapshot(temp)
    # Recheck after all bytes are fetched to detect a deployment during observation.
    newest=gh('actions/workflows/pages.yml/runs?status=success&branch=main&per_page=1')['workflow_runs'][0]
    if newest['head_sha']!=sha:raise Refused('Production changed during observation')
    event={'repository':REPO,'workflow':WORKFLOW,'event':'workflow_dispatch','branch':'main','conclusion':'success',
           'environment':'github-pages','sha':sha,'latest_production_sha':sha,'inventory_sha256':inv,
           'live_inventory_sha256':inv,'owner_publication_authorized':True,'run_id':int(run_id)}
    deployment_gate(event,sha,inv)
    try: notes=json.loads(get_public(RAW+sha+'/notification-release-notes.json'))
    except HTTPError as exc:
        if exc.code!=404:raise Refused('Release notes unavailable') from None
        notes=None
    result={'receipt':event,'verified_files':len(records),'bytes':total,'snapshot':snap,'files':records,'notes':notes}
    if output is not None:
        output.mkdir(parents=True,exist_ok=True)
        (output/'verified-production.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'mode':'read_only','run_id':run_id,'sha':sha,'verified_files':len(records),'site_inventory_sha256':inv}))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',type=int,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:observe(args.run_id,args.output)
    except Exception:
        # Never print HTTP response bodies, process environments or credentials.
        raise SystemExit('Observation refused or unavailable. No notification or production change was made.')
