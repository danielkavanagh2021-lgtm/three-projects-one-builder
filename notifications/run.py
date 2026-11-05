"""CLI used by the prepared Actions workflow; all production switches default off."""
import argparse
import copy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import tempfile
import time
from notifier import Refused,JsonStore,REPO,WORKFLOW,digest
from integration import Controller,config_guard,initial_state
from observe import observe,gh
from services import Transport,Kit,GitHubStore

def context_guard(mode):
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!=REPO or os.environ.get('GITHUB_REF')!='refs/heads/main':
        raise Refused('Only trusted main-branch Actions can access live service integration')
    eventname=os.environ.get('GITHUB_EVENT_NAME')
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    if eventname=='workflow_run':
        r=event.get('workflow_run',{})
        if mode!='production' or any((event.get('action')!='completed',r.get('conclusion')!='success',r.get('name')!=WORKFLOW,
             r.get('event')!='workflow_dispatch',r.get('head_branch')!='main',r.get('head_repository',{}).get('full_name')!=REPO)):
            raise Refused('Untrusted triggering run')
    elif eventname=='schedule':
        if mode!='production':raise Refused('Scheduled mode refused')
    elif eventname=='workflow_dispatch':
        if os.environ.get('GITHUB_ACTOR')!=REPO.split('/')[0]:raise Refused('Owner dispatch required')
    else:raise Refused('Unsupported trigger')

def latest_run():
    run=gh('actions/workflows/pages.yml/runs?status=success&branch=main&per_page=1')['workflow_runs'][0]
    return run

def latest():
    run=latest_run()
    return observe(run['id'])

def parse_config(path):
    obj=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(obj,dict):raise Refused('Configuration invalid')
    # Service identifiers stay out of public config files. Environment-scoped
    # secrets/variables are configured separately by the owner after review.
    for key,env in {'account_id':'KIT_ACCOUNT_ID','segment_id':'KIT_SEGMENT_ID','template_id':'KIT_TEMPLATE_ID',
                    'production_segment_id':'KIT_PRODUCTION_SEGMENT_ID'}.items():
        if os.environ.get(env):obj[key]=int(os.environ[env])
    for key,env in {'segment_name':'KIT_SEGMENT_NAME','template_name':'KIT_TEMPLATE_NAME',
                    'expected_plan_type':'KIT_EXPECTED_PLAN_TYPE'}.items():
        if os.environ.get(env):obj[key]=os.environ[env]
    if os.environ.get('KIT_EXCLUSION_CONFIG'):
        exclusions=json.loads(os.environ['KIT_EXCLUSION_CONFIG'])
        if not isinstance(exclusions,dict):raise Refused('Exclusion configuration invalid')
        obj['exclude_segment_ids']=[int(x) for x in exclusions];obj['excluded_segment_names']=exclusions
    for key,env in {'owner_authorized':'KIT_CONFIGURATION_APPROVED','audience_rules_reviewed':'KIT_AUDIENCE_REVIEWED',
                    'sender_reply_to_reviewed':'KIT_SENDER_REVIEWED','footer_reviewed':'KIT_FOOTER_REVIEWED',
                    'email_only_test_passed':'KIT_EMAIL_ONLY_TEST_PASSED'}.items():
        if env in os.environ:obj[key]=os.environ[env]=='true'
    return obj

def cycle(controller,observer,poll_seconds=30,limit=20):
    """Restart-safe cycle: reconcile before preparing any new broadcast."""
    state,_=controller.store.read()
    if state['outbox'] and state['outbox']['phase']!='prepared':
        status=controller.reconcile()
        if status not in ('completed','nothing_pending'):return status
    observation=observer()
    status=controller.prepare(observation,observation.get('notes'))
    if status=='no_announcement':return status
    status=controller.send(observer,os.environ.get('APPROVED_TEST_MESSAGE_SHA256'))
    for _ in range(limit):
        if status not in ('scheduled','sending','submitted','unknown'):break
        time.sleep(poll_seconds);status=controller.reconcile()
    return status

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['preview','validate','production','test','bootstrap-file'])
    parser.add_argument('--config',default='config.production.json')
    parser.add_argument('--output',default='review-output')
    args=parser.parse_args()
    if args.mode=='bootstrap-file':
        # Public read-only observation and a LOCAL file; never creates a branch.
        observation=latest();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
        (out/'state.json').write_text(json.dumps(initial_state(observation),ensure_ascii=False,indent=2),encoding='utf-8')
        print('Local baseline generated; no remote state was written.');return
    context_guard(args.mode)
    config=parse_config(args.config)
    if args.mode=='validate':
        kit=Kit(Transport('kit',os.environ.get('KIT_API_KEY',''),writes=False))
        result=kit.preflight(config)
        print(json.dumps(result));return
    if args.mode=='preview':
        # Reads public state but never attaches a Kit credential or writes remote state.
        store=GitHubStore(Transport('github',os.environ.get('GH_TOKEN',''),writes=False))
        state,_=store.read()
        with tempfile.TemporaryDirectory() as tmp:
            local=JsonStore(Path(tmp)/'state.json');local.save(state,None)
            c=Controller(local,None,config,'production',False)
            obs=latest();status=c.prepare(obs,obs.get('notes'));planned=local.read()[0]['outbox']
            print(json.dumps({'status':status,'message_sha256':digest(planned['message']) if planned else None}))
        return
    if args.mode=='production':
        if os.environ.get('NOTIFICATIONS_ENABLED')!='true':raise Refused('Production automation disabled')
    else:
        if os.environ.get('CONTROLLED_TEST_AUTHORIZED')!='true' or not os.environ.get('APPROVED_TEST_MESSAGE_SHA256'):
            raise Refused('Controlled test not authorized')
    config_guard(config,args.mode)
    state=GitHubStore(Transport('github',os.environ.get('GH_TOKEN',''),writes=True),test=args.mode=='test')
    kit=Kit(Transport('kit',os.environ.get('KIT_API_KEY',''),writes=True))
    controller=Controller(state,kit,config,args.mode,True)
    if args.mode=='test':
        # An explicit reviewed test proposal must already be in test-state.json.
        pending=state.read()[0]['outbox']
        if not pending:raise Refused('Controlled test proposal missing')
        result=controller.send(latest,os.environ['APPROVED_TEST_MESSAGE_SHA256'])
        for _ in range(20):
            if result not in ('scheduled','sending','unknown'):break
            time.sleep(30);result=controller.reconcile()
    else:
        stored,_=state.read()
        if not stored['outbox'] and latest_run()['head_sha']==stored['last_evaluated_sha']:
            result='no_new_deployment'
        else:result=cycle(controller,latest)
    print(json.dumps({'status':result,'mode':args.mode}))
    if result in ('unknown','review_required','rejected','aborted','draft'):raise Refused('Delivery held for owner review')

if __name__=='__main__':
    try:main()
    except Exception:
        # Fixed message only: HTTP bodies, credentials, subscriber data and inputs
        # never appear in tracebacks, workflow annotations or uploaded artifacts.
        raise SystemExit('Notification run stopped safely. Inspect the durable checkpoint privately; no blind retry was performed.')
