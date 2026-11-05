"""Restricted production HTTP clients. No call occurs merely by importing this module."""
import base64
from datetime import datetime
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, parse_qs
from urllib.request import Request, build_opener, HTTPRedirectHandler
from notifier import REPO, Refused, canonical, digest

SENDER = 'mrmagicsuite@gmail.com'

class Unavailable(Refused): pass
class Uncertain(Refused): pass
class Rejected(Refused): pass
class Conflict(Refused): pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Unavailable('HTTP redirect refused')

class Transport:
    """Fixed origins, endpoint allowlist, bounded GET retry, NEVER retry writes."""
    def __init__(self, service, token, *, writes=False, opener=None, sleep=time.sleep, clock=time.monotonic):
        if service not in ('kit','github') or not token: raise Refused('Credential not configured')
        self.service=service; self._token=token; self.writes=writes
        self.origin='https://api.kit.com' if service=='kit' else 'https://api.github.com'
        self.opener=opener or build_opener(NoRedirect()); self.sleep=sleep; self.clock=clock; self.last=None
    def permitted(self, method, path):
        if not isinstance(path,str) or not path.startswith('/') or path.startswith('//') or '\\' in path:
            raise Refused('Endpoint refused')
        u=urlsplit(path)
        if u.scheme or u.netloc or u.fragment or '..' in u.path.split('/'): raise Refused('Endpoint refused')
        q=parse_qs(u.query,strict_parsing=True) if u.query else {}
        if self.service=='kit':
            allowed_get=bool(re.fullmatch(r'/v4/(account|segments|email_templates|broadcasts(?:/\d+(?:/stats)?)?)',u.path))
            allowed_write=method=='POST' and u.path=='/v4/broadcasts' and not q
            if set(q)-{'after','per_page'} or any(len(v)!=1 for v in q.values()): raise Refused('Query refused')
        else:
            prefix='/repos/'+REPO+'/contents/'
            allowed_get=u.path in (prefix+'state.json',prefix+'test-state.json') and q=={'ref':['notification-state']}
            allowed_write=method=='PUT' and u.path in (prefix+'state.json',prefix+'test-state.json') and not q
        if method=='GET' and allowed_get:return
        if allowed_write and self.writes:return
        raise Refused('Request not authorized')
    def __call__(self,method,path,payload=None):
        self.permitted(method,path)
        if method=='GET' and payload is not None:raise Refused('GET body refused')
        if method=='POST':
            if payload.get('public') is not False or not payload.get('send_at') or payload.get('email_address')!=SENDER:
                raise Refused('Only dedicated-sender email-only broadcasts are allowed')
        if self.service=='github' and method=='PUT':
            if payload.get('branch')!='notification-state':raise Refused('State branch refused')
        headers={'Accept':'application/json','Content-Type':'application/json','User-Agent':'MrMagic-notifications/2'}
        if self.service=='kit':headers['X-Kit-Api-Key']=self._token
        else:headers.update({'Authorization':'Bearer '+self._token,'X-GitHub-Api-Version':'2026-03-10'})
        data=None if payload is None else canonical(payload).encode()
        for attempt in range(3 if method=='GET' else 1):
            if self.last is not None:self.sleep(max(0,1-(self.clock()-self.last)))
            self.last=self.clock()
            try:
                with self.opener.open(Request(self.origin+path,data=data,headers=headers,method=method),timeout=30) as response:
                    if response.geturl()!=self.origin+path:raise Unavailable('Redirect refused')
                    raw=response.read(4*1024*1024+1)
                    if len(raw)>4*1024*1024:raise ValueError('limit')
                    result=json.loads(raw)
                    if not isinstance(result,dict):raise ValueError('schema')
                    return result
            except HTTPError as exc:
                code=exc.code
                # Never consume, echo or persist provider error bodies.
                if method=='GET' and (code==429 or code>=500) and attempt<2:
                    try:delay=min(30,max(1,int(exc.headers.get('Retry-After','2'))))
                    except (ValueError,AttributeError):delay=2
                    self.sleep(delay*(attempt+1));continue
                if self.service=='github' and code==409:raise Conflict('State conflict') from None
                if method=='POST' and code in (400,401,403,404,422):raise Rejected('Broadcast rejected; review required') from None
                if method!='GET':raise Uncertain('Write outcome unknown; reconciliation required') from None
                raise Unavailable('Service read unavailable') from None
            except (URLError,TimeoutError,OSError,ValueError,Unavailable):
                if method=='GET' and attempt<2:self.sleep(2**attempt);continue
                if method!='GET':raise Uncertain('Write outcome unknown; reconciliation required') from None
                raise Unavailable('Service read unavailable') from None
        raise Unavailable('Service unavailable')

def paginate(call,path,key):
    items=[];seen=set()
    for _ in range(100):
        page=call('GET',path,None)
        if not isinstance(page.get(key),list):raise Refused('Provider schema mismatch')
        items.extend(page[key]);pagination=page.get('pagination',{})
        if pagination.get('has_next_page') is False:return items
        cursor=pagination.get('end_cursor')
        if not isinstance(cursor,str) or not cursor or cursor in seen:raise Refused('Pagination incomplete')
        seen.add(cursor);path=path.split('?')[0]+'?'+urlencode({'after':cursor,'per_page':500})
    raise Refused('Pagination limit reached; no send')

def normalized_filter(value):
    if not isinstance(value,list) or len(value)!=1:raise Refused('Unexpected audience filter')
    result={}
    for key in ('all','any','none'):
        values=value[0].get(key) or []
        result[key]=sorted([{'type':v['type'],'ids':sorted(v.get('ids',[]))} for v in values],key=canonical)
    if set(value[0])-{'all','any','none'}:raise Refused('Unexpected audience filter')
    return result

def audience(config):
    segment=config.get('segment_id');exclude=config.get('exclude_segment_ids',[])
    if type(segment)!=int or segment<1 or not isinstance(exclude,list) or any(type(x)!=int or x<1 or x==segment for x in exclude):
        raise Refused('Audience IDs require review')
    # Kit V4 permits one filter group only. Never silently drop exclusions.
    if exclude:
        raise Refused('Exclusions must be incorporated into the reviewed Kit segment; combined API groups are unsupported')
    return [{'all':[{'type':'segment','ids':[segment]}]}]

def normalized_time(value):
    if not isinstance(value,str):raise Refused('Missing schedule')
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:raise Refused('Schedule timezone missing')
    return int(dt.timestamp())

def broadcast_matches(record,payload):
    try:
        template=record.get('email_template',{}).get('id')
        return (record['public'] is False and not record.get('public_url')
                and all(record[k]==payload[k] for k in ('subject','content','description','email_address'))
                and template==payload['email_template_id']
                and normalized_time(record['send_at'])==normalized_time(payload['send_at'])
                and normalized_filter(record['subscriber_filter'])==normalized_filter(payload['subscriber_filter']))
    except (KeyError,TypeError,ValueError,Refused):return False

class Kit:
    def __init__(self,call):self.call=call
    def preflight(self,config):
        account=self.call('GET','/v4/account',None).get('account',{})
        if account.get('id')!=config.get('account_id'):raise Refused('Unexpected Kit account')
        if not any(s.get('email_address')==SENDER and s.get('is_verified') is True and s.get('from_name')=='MrMagic Suite'
                   for s in account.get('sending_addresses',[])):raise Refused('Dedicated sender not verified')
        segments=paginate(self.call,'/v4/segments?per_page=500','segments')
        expected={str(config['segment_id']):config['segment_name'],**config.get('excluded_segment_names',{})}
        if set(expected)!={str(config['segment_id'])}|{str(x) for x in config.get('exclude_segment_ids',[])}:
            raise Refused('Audience configuration incomplete')
        for sid,name in expected.items():
            if not any(s.get('id')==int(sid) and s.get('name')==name for s in segments):raise Refused('Audience metadata changed')
        templates=paginate(self.call,'/v4/email_templates?per_page=500','email_templates')
        template=next((t for t in templates if t.get('id')==config['template_id']),None)
        if not template or template.get('name')!=config['template_name'] or template.get('category')!='HTML':
            raise Refused('Approved template not available')
        # Plan identifiers can change: compare to an owner-reviewed expected value.
        if account.get('plan_type')!=config.get('expected_plan_type'):raise Refused('Account plan changed; review cost/eligibility')
        audience(config)
        return {'account_match':True,'sender_verified':True,'audience_metadata_match':True,'template_match':True,
                'audience_rules':'owner-reviewed; not exposed by segment API'}
    def create(self,payload):
        record=self.call('POST','/v4/broadcasts',payload).get('broadcast',{})
        if type(record.get('id'))!=int or record['id']<1:raise Uncertain('Broadcast ID unavailable')
        return record['id']
    def find(self,payload,broadcast_id=None):
        if broadcast_id:
            records=[self.call('GET',f'/v4/broadcasts/{int(broadcast_id)}',None).get('broadcast',{})]
        else:
            # Search all lifecycle states; a failed list/read never means safe to resend.
            records=[r for r in paginate(self.call,'/v4/broadcasts?per_page=500','broadcasts')
                     if r.get('description')==payload['description']]
        if len(records)!=1 or not broadcast_matches(records[0],payload):return None
        result=records[0]
        stats=self.call('GET',f"/v4/broadcasts/{result['id']}/stats",None).get('broadcast',{}).get('stats',{})
        status=stats.get('status')
        if status not in ('draft','scheduled','sending','completed','aborted'):return None
        if result.get('status')!=status:return None
        return {'id':result['id'],'status':status}

class GitHubStore:
    def __init__(self,call,test=False):
        self.call=call;self.path='/repos/'+REPO+'/contents/'+('test-state.json' if test else 'state.json')
    def read(self):
        obj=self.call('GET',self.path+'?ref=notification-state',None)
        try:
            raw=base64.b64decode(obj['content'],validate=False)
            state=json.loads(raw)
            if len(raw)>900000 or state.get('schema')!=2 or type(state.get('generation'))!=int:raise ValueError()
            return state,obj['sha']
        except (KeyError,ValueError,TypeError):raise Refused('Notification state missing or invalid') from None
    def save(self,state,revision):
        if not revision:raise Refused('State must be bootstrapped separately')
        raw=canonical(state).encode()
        if len(raw)>900000:raise Refused('State size requires archival review; never erase history')
        # A monotonic generation defeats an identical-content ABA claim.
        state['generation']+=1;raw=canonical(state).encode()
        obj=self.call('PUT',self.path,{'message':'Record notification checkpoint','branch':'notification-state',
                    'sha':revision,'content':base64.b64encode(raw).decode()})
        return obj['content']['sha']
