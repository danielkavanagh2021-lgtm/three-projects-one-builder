"""Prepare only local test-state/message files. Never contacts Kit or writes GitHub."""
import argparse
import json
from pathlib import Path
from notifier import BASE,digest
from integration import initial_state,config_guard
from run import latest,parse_config

def proposal(observation,config):
    config_guard(config,'test')
    msg={'subject':'[OWNER-AUTHORIZED TEST] MrMagic Suite website notifications',
         'text':'This is the single controlled test of MrMagic Suite website notifications. No new project milestone is being announced.\n\nView the portfolio:\n'+BASE+'\n\nUse Kit’s footer link to unsubscribe.',
         # The reviewed Classic template supplies its native unsubscribe/address footer.
         'html':'<p>This is the single controlled test of MrMagic Suite website notifications. No new project milestone is being announced.</p><p>View the portfolio:<br><a href="'+BASE+'">'+BASE+'</a></p><p>Use Kit’s footer link to unsubscribe.</p>'}
    state=initial_state(observation);target=digest({'test':msg,'config':config})
    state['outbox']={'key':target,'target':target,'observation':observation,'assets':state['assets'],
                    'message':msg,'phase':'prepared','broadcast_id':None,'payload':None,'config_digest':digest(config)}
    return state,digest(msg)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    try:
        state,message_hash=proposal(latest(),parse_config(a.config));out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
        (out/'test-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'test-message.txt').write_text(state['outbox']['message']['text'],encoding='utf-8')
        print('Prepared locally; not sent. Message SHA-256: '+message_hash)
    except Exception:raise SystemExit('Test preparation refused; no message was sent.')
