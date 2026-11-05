"""Read-only release validation. No networking, Git mutation or deployment."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
META={'.github/workflows/notifications.yml','.github/workflows/pages.yml','PUBLIC-UPDATE-POLICY.md','README.md','notification-release-notes.json','notifications/config.production.json','notifications/config.test.json','notifications/integration.py','notifications/notifier.py','notifications/observe.py','notifications/prepare_test.py','notifications/run.py','notifications/services.py','release-manifest.json','tools/check_release.py'}
def inventory_digest(files):
 canonical=''.join(x['file']+'\t'+x['sha256']+'\n' for x in sorted(files,key=lambda x:x['file']))
 return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
def verify(root,expected=None):
 root=root.resolve();site=root/'site';manifest=json.loads((root/'release-manifest.json').read_text(encoding='utf-8'))
 records=manifest['files'];actual={}
 for p in root.rglob('*'):
  rel=p.relative_to(root).as_posix()
  if rel=='.git' or rel.startswith('.git/'):continue
  if p.is_symlink():raise ValueError('Symlinks are not permitted: '+rel)
  if p.is_file() and not rel.startswith('site/') and rel not in META:raise ValueError('Unapproved repository file: '+rel)
 for p in site.rglob('*'):
  if p.is_file():actual[p.relative_to(site).as_posix()]=p
 names=[x['file'] for x in records]
 if len(names)!=len(set(names)):raise ValueError('Duplicate file records')
 if set(names)!=set(actual):raise ValueError('Site file set differs from the reviewed manifest')
 for rec in records:
  name=rec['file']
  if not re.fullmatch(r'[A-Za-z0-9._/-]+',name) or any(x in ('','..','.') for x in name.split('/')):raise ValueError('Unsafe manifest path')
  p=actual[name]
  if not p.resolve().is_relative_to(site.resolve()):raise ValueError('Path escapes site')
  if p.stat().st_size!=rec['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=rec['sha256']:raise ValueError('Changed file: '+name)
 digest=inventory_digest(records)
 if digest!=manifest['site_inventory_sha256']:raise ValueError('Manifest inventory digest mismatch')
 if expected is not None:
  if not re.fullmatch('[0-9a-f]{64}',expected) or digest!=expected:raise ValueError('Owner-confirmed site digest does not match')
 return {'files':len(records),'site_inventory_sha256':digest,'validated':True,'published':False}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--expected-site-digest');args=parser.parse_args()
 try:print(json.dumps(verify(ROOT,args.expected_site_digest),indent=2))
 except (ValueError,KeyError,OSError,json.JSONDecodeError) as exc:sys.exit('RELEASE REFUSED: '+str(exc))
