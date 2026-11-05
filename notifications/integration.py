"""Durable production state machine; dependencies are injected for offline tests."""
from datetime import datetime,timedelta,timezone
import copy
import html
from pathlib import PurePosixPath
import re
from notifier import (BASE,PAGES,Refused,canonical,digest,privacy,changes,email,deployment_gate,asset_review)
from services import SENDER,audience,Rejected

def maps(files):
    result={}
    for f in files:
        p=f['file']
        if not re.fullmatch(r'[A-Za-z0-9._/-]+',p) or any(x in ('','..','.') for x in p.split('/')) or p in result:
            raise Refused('Inventory paths invalid')
        if not re.fullmatch('[0-9a-f]{64}',f['sha256']):raise Refused('Inventory hash invalid')
        result[p]=f['sha256']
    return result

def asset_map(files):
    return {p:{'physical':h,'semantic':h} for p,h in maps(files).items()
            if PurePosixPath(p).suffix.lower() in {'.pdf','.png','.jpg','.jpeg','.webp','.svg','.avif'}}

def identity(snap,assets):return digest({'snapshot':snap,'assets':{p:v['semantic'] for p,v in assets.items()}})

def initial_state(observation):
    a=asset_map(observation['files']);key=identity(observation['snapshot'],a)
    return {'schema':2,'generation':0,'last_announced':None,'baseline':copy.deepcopy(observation),
            'assets':a,'history':{key:{'status':'baseline_only','sha':observation['receipt']['sha']}},
            'outbox':None,'last_evaluated_sha':observation['receipt']['sha'],
            'evaluated_inventory':observation['receipt']['inventory_sha256']}

def checked_notes(notes,observation,oldfiles):
    if not notes:return {}
    if set(notes)!={'schema','site_inventory_sha256','changes'} or not isinstance(notes['changes'],list):
        raise Refused('Unexpected release-note fields')
    if notes.get('schema')!=1 or notes.get('site_inventory_sha256')!=observation['receipt']['inventory_sha256']:
        raise Refused('Release notes are not bound to this verified site')
    current=maps(observation['files']);old=maps(oldfiles);result={}
    for item in notes.get('changes',[]):
        if set(item)!={'file','project_page','before_sha256','after_sha256','kind','summary'}:
            raise Refused('Unexpected release-description fields')
        path=item.get('file');page=item.get('project_page')
        if path in result or page not in PAGES or path not in old.keys()|current.keys():raise Refused('Unapproved note path')
        if item.get('before_sha256')!=old.get(path) or item.get('after_sha256')!=current.get(path) or old.get(path)==current.get(path):
            raise Refused('Release note evidence mismatch')
        if item.get('kind') not in ('meaningful','maintenance'):raise Refused('Note classification missing')
        summary=item.get('summary','')
        if not isinstance(summary,str) or not 10<=len(summary)<=600:raise Refused('Release description must be short and complete')
        privacy(summary)
        result[path]=dict(item)
    return result

def describe(state,observation,notes):
    baseline=state['last_announced'] or state['baseline']
    # Asset maintenance uses a physical baseline independent of the last mailing.
    previous_files=copy.deepcopy(baseline['files']);byname={r['file']:r for r in previous_files}
    for p,a in state['assets'].items():byname[p]={'file':p,'sha256':a['physical']}
    validated=checked_notes(notes,observation,list(byname.values()))
    newassets=asset_map(observation['files']);extra=[]
    for p in state['assets'].keys()|newassets.keys():
        old=state['assets'].get(p);new=newassets.get(p)
        if old and new and old['physical']==new['physical']:
            newassets[p]['semantic']=old['semantic'];continue
        note=validated.get(p)
        if not note:raise Refused('Changed image or PDF requires hash-bound public release description')
        if note['kind']=='maintenance':
            if not old or not new:raise Refused('Asset additions/removals cannot be classified as maintenance')
            newassets[p]['semantic']=old['semantic']
        else:
            extra.append({'project':PAGES[note['project_page']], 'url':BASE+note['project_page'], 'summary':note['summary']})
    # Reviewed notes can summarize big HTML edits; they cannot suppress actual text changes as maintenance.
    adjusted=copy.deepcopy(observation['snapshot'])
    note_text=[]
    for p,note in validated.items():
        if p in PAGES and baseline['snapshot'][p]!=adjusted[p]:
            if note['kind']!='meaningful':raise Refused('Text changes cannot be hidden as maintenance')
            adjusted[p]=copy.deepcopy(baseline['snapshot'][p])
            note_text.append({'project':PAGES[p],'url':BASE+p,'summary':note['summary']})
    items=changes(baseline['snapshot'],adjusted)+note_text+extra
    unique=[]
    for item in items:
        if item not in unique:unique.append(item)
    if sum(len(x['summary']) for x in unique)>2400:raise Refused('Summary too long; reviewed concise release notes required')
    return unique,newassets

def message_for(items):
    msg=email(items)
    # Explicit direct home link in addition to each precise updated page link.
    msg['text']+='\n\nView the portfolio: '+BASE
    msg['html']+='<p><a href="'+BASE+'">View the MrMagic Suite portfolio</a></p>'
    return msg

def payload_for(msg,key,config,now):
    return {'email_template_id':config['template_id'],'email_address':SENDER,'subject':msg['subject'],
            'content':msg['html'],'description':'mrmagic-announcement:'+key,'public':False,
            'send_at':(now+timedelta(minutes=2)).replace(microsecond=0).isoformat(),
            'subscriber_filter':audience(config)}

def config_guard(config,mode):
    for field in ('account_id','segment_id','template_id'):
        if type(config.get(field))!=int or config[field]<1:raise Refused('Account/audience/template not configured')
    required=('audience_rules_reviewed','sender_reply_to_reviewed','footer_reviewed','owner_authorized')
    if any(config.get(k) is not True for k in required):raise Refused('Owner-approved configuration required')
    if mode=='test':
        if config.get('test_only') is not True or config.get('expected_test_recipients')!=1:
            raise Refused('Single-recipient test authorization required')
        if type(config.get('production_segment_id'))!=int or config['production_segment_id']==config['segment_id']:
            raise Refused('Test segment must be separate from the production audience')
    elif mode=='production':
        if config.get('email_only_test_passed') is not True or config.get('test_only') is not False:
            raise Refused('Production test/activation approval missing')
    else:raise Refused('Delivery mode refused')
    audience(config)

class Controller:
    def __init__(self,store,kit,config,mode,enabled=False,clock=lambda:datetime.now(timezone.utc)):
        self.store=store;self.kit=kit;self.config=config;self.mode=mode;self.enabled=enabled;self.clock=clock
    def prepare(self,observation,notes=None):
        receipt=observation['receipt'];deployment_gate(receipt,receipt['sha'],receipt['inventory_sha256'])
        state,revision=self.store.read()
        if state['outbox']:return 'pending'
        if state['last_evaluated_sha']==receipt['sha'] and state.get('evaluated_inventory')==receipt['inventory_sha256']:
            return 'no_announcement'
        items,assets=describe(state,observation,notes)
        target=identity(observation['snapshot'],assets)
        if target in state['history'] or not items:
            if state['assets']==assets and state['last_evaluated_sha']==receipt['sha']:
                return 'no_announcement'
            state['assets']=assets;state['last_evaluated_sha']=receipt['sha']
            state['evaluated_inventory']=receipt['inventory_sha256']
            self.store.save(state,revision);return 'no_announcement'
        base=state['last_announced'] or state['baseline']
        key=digest({'from':base['receipt']['sha'],'to':target,'mode':self.mode})
        message=message_for(items)
        if self.mode=='test':
            message['subject']='[OWNER-AUTHORIZED TEST] '+message['subject']
            message['text']='Controlled subscription-system test.\n\n'+message['text']
            message['html']='<p><strong>Controlled subscription-system test.</strong></p>'+message['html']
        state['outbox']={'key':key,'target':target,'observation':observation,'assets':assets,'message':message,
                         'phase':'prepared','broadcast_id':None,'payload':None,'config_digest':digest(self.config)}
        self.store.save(state,revision);return 'prepared'
    def send(self,live_check,expected_message_digest=None):
        if not self.enabled:raise Refused('Email delivery disabled')
        config_guard(self.config,self.mode)
        state,revision=self.store.read();out=state['outbox']
        if not out:return 'nothing_pending'
        if out['phase']!='prepared':return self.reconcile()
        if out['config_digest']!=digest(self.config):raise Refused('Audience/configuration changed after preview')
        if self.mode=='test' and expected_message_digest!=digest(out['message']):raise Refused('Exact test message approval required')
        self.kit.preflight(self.config)
        checked=live_check();r=checked['receipt']
        deployment_gate(r,r['sha'],r['inventory_sha256'])
        if r['sha']!=out['observation']['receipt']['sha'] or r['inventory_sha256']!=out['observation']['receipt']['inventory_sha256']:
            # Safe to abandon only before any provider request; recompute latest later.
            state['outbox']=None;self.store.save(state,revision);return 'superseded_before_send'
        payload=payload_for(out['message'],out['key'],self.config,self.clock())
        out['payload']=payload;out['phase']='intent';self.store.save(state,revision)
        # State must be durable before the one irreversible operation. No POST retries.
        try:bid=self.kit.create(payload)
        except Rejected:
            self.mark('rejected');return 'rejected'
        except Exception:
            # Includes malformed responses/timeouts; intent already survives a state outage.
            self.mark('unknown');return 'unknown'
        self.mark('submitted',bid)
        return self.reconcile()
    def mark(self,phase,bid=None):
        state,revision=self.store.read();out=state['outbox']
        if not out:raise Refused('Outbox unexpectedly missing')
        out['phase']=phase
        if bid is not None:out['broadcast_id']=bid
        self.store.save(state,revision)
    def reconcile(self):
        state,revision=self.store.read();out=state['outbox']
        if not out:return 'nothing_pending'
        if not out.get('payload'):return 'prepared'
        found=self.kit.find(out['payload'],out.get('broadcast_id'))
        if not found:return 'review_required'
        out['broadcast_id']=found['id'];out['phase']=found['status']
        if found['status']=='completed':
            state['last_announced']=out['observation'];state['assets']=out['assets']
            state['history'][out['target']]={'status':'completed','key':out['key'],
                       'sha':out['observation']['receipt']['sha'],'broadcast_id':found['id']}
            state['last_evaluated_sha']=out['observation']['receipt']['sha'];state['outbox']=None
            state['evaluated_inventory']=out['observation']['receipt']['inventory_sha256']
        self.store.save(state,revision)
        return found['status']
