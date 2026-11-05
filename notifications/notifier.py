"""Offline notification engine. No network transport or live-send CLI is installed.

Only public, approved website snapshots may enter this engine. A production caller
must independently verify the deployment receipt and live bytes before calling it.
"""
from __future__ import annotations
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import threading
import unicodedata
from urllib.parse import urljoin, urlsplit

BASE = 'https://danielkavanagh2021-lgtm.github.io/three-projects-one-builder/'
REPO = 'danielkavanagh2021-lgtm/three-projects-one-builder'
WORKFLOW = 'Owner-authorized Pages release'
PAGES = {
    'index.html': 'MrMagic Suite',
    'big-poppa.html': 'Magic’s Mining Command',
    'magics-decision-desk.html': 'Magic’s Decision Desk',
    'formula-none-fitness.html': 'Magic’s Fitness Companion',
    'behind-the-build.html': 'Behind the Build',
    'updates.html': 'Project Milestones',
}

class Refused(Exception):
    """Safe error: never includes input, credentials or subscriber information."""

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def norm(text):
    # Preserve case, punctuation and numbers: those can change factual meaning.
    return ' '.join(unicodedata.normalize('NFKC', text).split())

def privacy(text):
    """Defense in depth, NOT a substitute for the owner's publication review."""
    patterns = [
        r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', r'\b(?:gh[pousr]_|github_pat_)[\w]+',
        r'-----BEGIN .*PRIVATE KEY', r'\b(?:api[_ -]?key|password|secret|token)\s*[:=]',
        r'\b(?:10\.|127\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.)\d',
        r'\b[a-z]:[\\/]', r'\b(?:localhost|tailscale|\.internal)\b',
        r'\b0x[a-f0-9]{40}\b', r'\bbc1[a-z0-9]{25,}\b',
        r'\b(?:my|your|personal)\s+(?:weight|body fat|balance|account number)\s*[:=]',
        r'\{[{%]',  # Do not allow public content to inject Liquid into emails.
    ]
    if any(re.search(p, text, re.I) for p in patterns):
        raise Refused('Privacy review required; content suppressed')
    if any(not url.startswith(BASE) for url in re.findall(r'https?://[^\s<>]+',text)):
        raise Refused('External URL requires editorial review')

def public_link(value):
    url = urljoin(BASE, value)
    parsed = urlsplit(url)
    if not url.startswith(BASE) or parsed.query or parsed.username or parsed.password:
        raise Refused('Unapproved announcement link')
    if '..' in parsed.path.split('/') or '%2e' in parsed.path.lower():
        raise Refused('Unsafe announcement path')
    return url

class MainContent(HTMLParser):
    """Extract semantic blocks from main, ignoring layout attributes/scripts/nav."""
    blocks = {'h1','h2','h3','h4','p','li','figcaption'}
    void = {'img','br','hr','input','meta','link','source','wbr','area','base','embed','param','track','col'}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []; self.current = None; self.rows = []; self.links = set(); self.main = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        hidden = (self.stack[-1][1] if self.stack else False) or tag in {'script','style','nav','footer','dialog','noscript'} or 'hidden' in a or a.get('aria-hidden') == 'true'
        if tag == 'main': self.main = True
        if tag not in self.void: self.stack.append((tag, hidden))
        if not self.main or hidden: return
        if tag in self.blocks and self.current is None: self.current = [tag, []]
        if tag == 'br' and self.current: self.current[1].append(' ')
        if tag == 'a' and a.get('href'):
            url = urljoin(BASE, a['href'])
            # External signup destinations are not copied into notification links.
            if url.startswith(BASE): self.links.add(public_link(url))
    def handle_data(self, data):
        if self.main and self.current and not (self.stack and self.stack[-1][1]):
            self.current[1].append(data)
    def handle_endtag(self, tag):
        if self.current and self.current[0] == tag:
            text = norm(''.join(self.current[1]))
            if text: self.rows.append([tag, text])
            self.current = None
        if tag == 'main': self.main = False
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]; break

def snapshot(site):
    result = {}
    for page in PAGES:
        path = Path(site) / page
        if not path.is_file() or path.is_symlink(): raise Refused('Required public page missing or unsafe')
        parser = MainContent(); parser.feed(path.read_text(encoding='utf-8'))
        if not parser.rows: raise Refused('No public content found')
        # Sets avoid duplicate responsive markup / ordering-only announcements.
        result[page] = {'blocks': sorted({tuple(x) for x in parser.rows}), 'links': sorted(parser.links)}
    return json.loads(canonical(result))

def inventory(site):
    records = []
    for p in sorted(Path(site).rglob('*')):
        if p.is_symlink(): raise Refused('Symlink refused')
        if p.is_file(): records.append({'file':p.relative_to(site).as_posix(), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    raw = ''.join(x['file']+'\t'+x['sha256']+'\n' for x in records)
    return hashlib.sha256(raw.encode()).hexdigest(), records

def asset_review(old_records, new_records):
    """Byte changes alone cannot distinguish new evidence from recompression."""
    old={x['file']:x['sha256'] for x in old_records}
    new={x['file']:x['sha256'] for x in new_records}
    suffixes={'.pdf','.png','.jpg','.jpeg','.webp','.svg','.avif'}
    return sorted(p for p in old.keys()|new.keys()
                  if Path(p).suffix.lower() in suffixes and old.get(p)!=new.get(p))

def plan_release(engine, observation, previous_records):
    """Conservative release entry point: no binary-only change is auto-announced."""
    changed_assets=asset_review(previous_records,observation['files'])
    if changed_assets:
        return {'status':'asset_review_required','files':changed_assets}
    event=observation['receipt']
    return engine.prepare(observation['snapshot'],event,event['sha'],event['inventory_sha256'])

def changes(old, new):
    if set(old) != set(PAGES) or set(new) != set(PAGES): raise Refused('Page policy requires review')
    result = []
    for page, project in PAGES.items():
        before, after = old[page], new[page]
        if before == after: continue
        added = [r for r in after['blocks'] if r not in before['blocks']]
        removed = [r for r in before['blocks'] if r not in after['blocks']]
        # Never quote removed claims or infer a working feature from a screenshot.
        prose = [r[1] for r in added if r[0] in {'p','li','figcaption'}]
        for _, text in added: privacy(text)
        if any(len(x) > 650 for x in prose) or len(prose) > 5:
            raise Refused('Large content change requires editorial review')
        if not added and not removed:
            added_links=[x for x in after['links'] if x not in before['links']]
            removed_links=[x for x in before['links'] if x not in after['links']]
            summary = 'Updated the page’s links ('+str(len(added_links))+' added, '+str(len(removed_links))+' removed).'
        elif not prose:
            headings=[r[1] for r in added if r[0].startswith('h')]
            summary = ('Updated headings: '+ '; '.join(headings)+'.') if headings else 'Removed '+str(len(removed))+' text passage(s) from the page.'
        else:
            summary = 'Updated the public project description: ' + ' '.join(prose)
        if len(summary) > 1400: raise Refused('Summary requires editorial review')
        result.append({'project':project, 'url':public_link(page), 'summary':summary})
    return result

def email(change_list):
    text = ['MrMagic Suite — Website update', '', 'I’ve updated my public project portfolio. Here’s what changed:', '']
    body = ['<p>I’ve updated my public project portfolio. Here’s what changed:</p>','<ul>']
    for c in change_list:
        text += [c['project'] + ': ' + c['summary'], c['url'], '']
        body.append('<li><strong>'+html.escape(c['project'])+'</strong>: '+html.escape(c['summary'])+' <a href="'+html.escape(c['url'],quote=True)+'">Read the update</a></li>')
    footer = 'These are personal, noncommercial projects. Design concepts, testing and deployed functionality remain separately identified on the website.'
    text += [footer, '', 'Unsubscribe using the link provided by Kit in this email’s footer.']
    body += ['</ul>', '<p>'+footer+'</p>', '<p><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>', '<p>{{ address }}</p>']
    return {'subject':text[0], 'text':'\n'.join(text), 'html':'\n'.join(body)}

def kit_payload(message, key, segment_id, template_id):
    if type(segment_id) is not int or segment_id < 1 or type(template_id) is not int or template_id < 1:
        raise Refused('Explicit audience segment and approved template required')
    # Template supplies the reviewed footer. A production adapter must verify
    # these Liquid tokens render once correctly in the selected template.
    return {'subject':message['subject'], 'content':message['html'],
            'description':'mrmagic-announcement:'+key, 'public':False, 'send_at':None,
            'email_address':'mrmagicsuite@gmail.com', 'email_template_id':template_id,
            'subscriber_filter':[{'all':[{'type':'segment','ids':[segment_id]}]}]}

def schedule_payload(message, key, segment_id, template_id):
    payload=kit_payload(message,key,segment_id,template_id)
    payload['send_at']=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
    return payload

def deployment_gate(event, sha, inv):
    expected = {'repository':REPO, 'workflow':WORKFLOW, 'event':'workflow_dispatch',
                'branch':'main', 'conclusion':'success', 'environment':'github-pages',
                'sha':sha, 'latest_production_sha':sha, 'inventory_sha256':inv,
                'live_inventory_sha256':inv, 'owner_publication_authorized':True}
    if any(event.get(k) != v for k,v in expected.items()): raise Refused('Production deployment gate failed')
    if not re.fullmatch('[0-9a-f]{40}', sha) or not re.fullmatch('[0-9a-f]{64}',inv): raise Refused('Invalid deployment identity')

class JsonStore:
    """Local durable CAS. Exclusive lock and atomic replace; no secrets stored."""
    def __init__(self, path): self.path = Path(path)
    def read(self):
        raw = self.path.read_text(encoding='utf-8')
        return json.loads(raw), hashlib.sha256(raw.encode()).hexdigest()
    def save(self, state, revision):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix('.lock')
        try: fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError: raise Refused('Concurrent state writer; retry read-only')
        try:
            actual = self.read()[1] if self.path.exists() else None
            if revision != actual: raise Refused('State conflict; no provider action allowed')
            temporary = self.path.with_suffix('.tmp')
            with temporary.open('w', encoding='utf-8', newline='\n') as f:
                f.write(canonical(state)); f.flush(); os.fsync(f.fileno())
            os.replace(temporary, self.path)
        finally:
            os.close(fd); lock.unlink()
        return self.read()[1]

class GitHubStateStore:
    """Durable GitHub Contents CAS adapter; transport must be supplied explicitly.

    No transport is bundled. Use only a separately approved public metadata branch.
    The branch contains public snapshots/IDs, never subscriber data or secrets.
    """
    def __init__(self, transport): self.transport = transport
    def read(self):
        import base64
        result = self.transport('GET', '/repos/'+REPO+'/contents/state.json?ref=notification-state', None)
        return json.loads(base64.b64decode(result['content'])), result['sha']
    def save(self, state, revision):
        import base64
        if not revision: raise Refused('Production state must be explicitly bootstrapped')
        payload = {'message':'Record notification state', 'branch':'notification-state', 'sha':revision,
                   'content':base64.b64encode(canonical(state).encode()).decode()}
        result = self.transport('PUT','/repos/'+REPO+'/contents/state.json',payload)
        return result['content']['sha']

def bootstrap(store, snap, sha):
    state = {'schema':1,'last_announced':{'sha':sha, 'snapshot':snap, 'digest':digest(snap), 'baseline_only':True},
             'history':{digest(snap):{'sha':sha,'baseline_only':True}},'outbox':None}
    store.save(state,None)

class Engine:
    def __init__(self, store): self.store = store
    def prepare(self, snap, event, sha, inv):
        deployment_gate(event,sha,inv)
        state, revision = self.store.read()
        if state['outbox']: return {'status':'pending_reconciliation'}
        target = digest(snap); last = state['last_announced']
        if target == last['digest']: return {'status':'no_meaningful_change'}
        if target in state['history']: return {'status':'previously_announced_content'}
        change_list = changes(last['snapshot'],snap)
        if not change_list: return {'status':'no_meaningful_change'}
        key = digest({'from':last['digest'],'to':target})
        message = email(change_list)
        state['outbox'] = {'key':key,'target':target,'sha':sha,'inventory':inv,'snapshot':snap,
                           'phase':'prepared','broadcast_id':None,'message':message}
        self.store.save(state,revision)
        return {'status':'prepared','key':key,'changes':change_list,'email':message}
    def deliver_to_simulator(self, provider, segment_id=123, template_id=456, *, current_production_sha):
        # Hard type barrier: this method cannot use a real transport accidentally.
        if type(provider) is not SyntheticKit: raise Refused('Live delivery is not installed')
        state, rev = self.store.read(); out = state['outbox']
        if not out: return 'nothing_pending'
        if out['phase'] != 'prepared': return 'reconciliation_required'
        if current_production_sha != out['sha']: raise Refused('Production changed before send; reconciliation required')
        payload = schedule_payload(out['message'],out['key'],segment_id,template_id)
        out['request_digest'] = digest(payload)
        out['phase'] = 'intent_persisted'; rev = self.store.save(state,rev)
        # Simulate scheduled create (one POST), not draft+PUT. Never auto retry POST.
        try: broadcast_id = provider.create_and_schedule(payload)
        except DefinitiveRejection:
            out['phase'] = 'rejected'; self.store.save(state,rev); return 'rejected'
        except Exception:
            # Safe fixed text, no provider response/error content in logs or state.
            out['phase'] = 'unknown'; self.store.save(state,rev); return 'unknown'
        out['broadcast_id'] = broadcast_id; out['phase'] = 'scheduled'
        self.store.save(state,rev)
        return 'scheduled'
    def reconcile_simulator(self, provider):
        if type(provider) is not SyntheticKit: raise Refused('Live delivery is not installed')
        state, rev = self.store.read(); out = state['outbox']
        if not out: return 'nothing_pending'
        matches = provider.find(out['key'])
        if len(matches) != 1: return 'manual_reconciliation_required'
        item = matches[0]
        if item['request_digest'] != out.get('request_digest'): return 'manual_reconciliation_required'
        out['broadcast_id'] = item['id']
        if item['status'] != 'completed':
            out['phase'] = item['status']; self.store.save(state,rev); return item['status']
        state['last_announced'] = {k:out[k] for k in ('sha','snapshot')}
        state['last_announced'].update({'digest':out['target'],'broadcast_id':item['id']})
        state['history'][out['target']] = {'sha':out['sha'],'broadcast_id':item['id'],'key':out['key']}
        state['outbox'] = None; self.store.save(state,rev)
        return 'completed'
    def approve_retry_after_rejection(self, key):
        state, rev = self.store.read(); out = state['outbox']
        if not out or out['key'] != key or out['phase'] != 'rejected': raise Refused('Retry is unsafe')
        out['phase'] = 'prepared'; self.store.save(state,rev)

class DefinitiveRejection(Exception): pass

class SyntheticKit:
    """In-memory fake ONLY. No subscriber email is stored in the engine's ledger."""
    def __init__(self, subscribers):
        if any(not s['email'].endswith('@example.invalid') for s in subscribers): raise Refused('Synthetic addresses only')
        self.subscribers = copy.deepcopy(subscribers); self.broadcasts = []; self.calls = 0; self.mode = 'normal'
        self.lock = threading.Lock()
    def create_and_schedule(self, payload):
        with self.lock:
            if not payload.get('send_at') or payload.get('public') is not False:
                raise DefinitiveRejection('Email-only schedule required')
            self.calls += 1
            if self.mode == 'reject': raise DefinitiveRejection('Synthetic rejection')
            if self.mode == 'timeout_before': raise TimeoutError('Synthetic timeout')
            item = {'id':len(self.broadcasts)+1,'key':payload['description'].split(':',1)[1],
                    'request_digest':digest(payload),'status':'scheduled','recipients':0}
            self.broadcasts.append(item)
            if self.mode == 'timeout_after': raise TimeoutError('Synthetic timeout')
            return item['id']
    def find(self,key): return [copy.deepcopy(x) for x in self.broadcasts if x['key'] == key]
    def finish(self):
        for b in self.broadcasts:
            if b['status'] == 'scheduled':
                b['recipients'] = sum(s['confirmed'] and s['opted_in'] and s['status']=='active' for s in self.subscribers)
                b['status'] = 'completed'
