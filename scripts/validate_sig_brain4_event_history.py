#!/usr/bin/env python3
"""Validate official Brain4 event history. Display-only proof."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone

def parse_dt(v):
    if not v: return None
    try:
        d=datetime.fromisoformat(str(v).replace('Z','+00:00'))
        if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:
        return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='.'); ap.add_argument('--history',default='panel/brain4/sig_brain4_event_history_current.json')
    args=ap.parse_args(); root=Path(args.repo_root); path=root/args.history
    failures=[]
    try: h=json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        failures.append(f'history_unreadable:{e}'); h={}
    ids=set()
    for i,e in enumerate(h.get('events',[]) or []):
        eid=e.get('event_id')
        if not eid: failures.append(f'row_{i}_missing_event_id')
        elif eid in ids: failures.append(f'duplicate_event_id:{eid}')
        ids.add(eid)
        for k in ['memory_id','instrument','timeframe','activated_at_utc','expires_at_utc','status']:
            if not e.get(k): failures.append(f'row_{i}_missing_{k}')
        a=parse_dt(e.get('activated_at_utc')); x=parse_dt(e.get('expires_at_utc'))
        if a and x and x <= a: failures.append(f'row_{i}_expiry_not_after_activation')
        if str(e.get('status')) not in ['ACTIVE','EXPIRED']:
            failures.append(f'row_{i}_bad_status:{e.get("status")}')
    if h.get('signal_authorized') is not False: failures.append('signal_authorized_not_false')
    if h.get('action_surface_authorized') is not False: failures.append('action_surface_authorized_not_false')
    out={'validation_status':'PASS' if not failures else 'FAIL','failures':failures,'event_count':len(h.get('events',[]) or []),'active_event_count':len(h.get('active_events',[]) or []),'signal_authorized':False,'action_surface_authorized':False}
    (root/'proofs').mkdir(exist_ok=True)
    (root/'proofs/sig_brain4_event_history_validation_result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
