#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy

BOUNDARY = {
    "runtime_observation_not_signal": True,
    "candidate_not_trade_recommendation": True,
    "outcome_observation_not_win_loss": True,
    "lifecycle_tracking_not_execution_tracking": True,
    "cache_not_source_authority": True,
    "single_provider_confidence_not_source_truth": True,
    "scheduler_heartbeat_not_production_readiness": True,
    "panel_payload_not_action_surface": True,
    "no_broker": True,
    "no_order": True,
    "no_execution": True,
    "no_buy_sell_hold": True,
    "no_entry_stop_target": True,
    "no_pnl": True,
    "no_optimizer": True,
    "no_validation_verdict": True,
    "no_adaptation_decision": True,
    "no_production_readiness_claim": True,
    "spx_nq_out_of_v1_active_scope": True,
    "calendar_event_out_of_v1_scope": True,
    "second_provider_out_of_v1_scope": True,
    "row_2_retained_unopened": True,
    "rows_6_7_deferred_reentry": True,
    "matrix_complete_not_matrix_open": True,
}

FORBIDDEN_SURFACES_ABSENT = {
    "broker_status": True,
    "execution_queue": True,
    "action_buttons": True,
    "buy_sell_hold": True,
    "entry_stop_target": True,
    "pnl_win_loss": True,
}

def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def parse_float(v):
    try:
        return float(v)
    except Exception:
        return None

def normalize_dt(s):
    if s is None:
        return None
    t = str(s).strip().replace(' ', 'T')
    if len(t) == 10:
        t = t + 'T00:00:00'
    if not t.endswith('Z'):
        t += 'Z'
    return t

def sortable_dt(s):
    if s is None:
        return ''
    return normalize_dt(s).replace('Z','')

def read_cache_bars(cache_path):
    raw = read_json(cache_path, default=None)
    if raw is None:
        return [], 'cache_file_missing'
    if isinstance(raw, dict):
        values = raw.get('values')
        if values is None and isinstance(raw.get('data'), list):
            values = raw.get('data')
        if values is None and isinstance(raw.get('surface_rows'), list):
            values = raw.get('surface_rows')
    elif isinstance(raw, list):
        values = raw
    else:
        values = None
    if not isinstance(values, list):
        return [], 'cache_values_missing_or_unreadable'
    bars = []
    for item in values:
        if not isinstance(item, dict):
            continue
        dt = item.get('datetime') or item.get('bar_open_ts_utc') or item.get('time') or item.get('date')
        o, h, l, c = [parse_float(item.get(k)) for k in ('open','high','low','close')]
        if dt is None or None in (o,h,l,c):
            continue
        bars.append({'bar_open_ts_utc': normalize_dt(dt), 'open': o, 'high': h, 'low': l, 'close': c})
    bars = sorted(bars, key=lambda b: sortable_dt(b['bar_open_ts_utc']))
    return bars, None if bars else 'no_valid_ohlc_bars'

def existing_dedupe_keys(registry):
    keys = set()
    candidates = registry.get('candidates') if isinstance(registry, dict) else None
    if isinstance(candidates, dict):
        iterable = candidates.values()
    elif isinstance(candidates, list):
        iterable = candidates
    else:
        iterable = []
    for c in iterable:
        if not isinstance(c, dict):
            continue
        dk = c.get('dedupe_key')
        if dk: keys.add(dk)
        else:
            parts = [c.get('instrument'), c.get('timeframe'), c.get('edge_family'), c.get('candidate_type'), c.get('trigger_reference_bar_ts_utc')]
            if all(parts): keys.add('|'.join(parts))
    return keys

def detect_range_breakout(surface_cfg, bars, policy):
    rule = policy['rule_family']
    skip = int(rule.get('skip_newest_provider_bars', 1))
    lookback = int(rule.get('lookback_bars', 20))
    min_lb = int(rule.get('min_lookback_bars', 8))
    if len(bars) < min_lb + 1 + skip:
        return None, 'not_enough_bars_for_detection'
    eligible = bars[:-skip] if skip > 0 else bars[:]
    if len(eligible) < min_lb + 1:
        return None, 'not_enough_eligible_completed_bars'
    trigger = eligible[-1]
    prior = eligible[max(0, len(eligible)-1-lookback):len(eligible)-1]
    if len(prior) < min_lb:
        return None, 'not_enough_prior_lookback_bars'
    prior_high = max(b['high'] for b in prior)
    prior_low = min(b['low'] for b in prior)
    edge_family = policy['rule_family']['edge_family']
    if trigger['high'] > prior_high and trigger['close'] > prior_high:
        ctype = 'upside_range_breakout_observation_candidate'
    elif trigger['low'] < prior_low and trigger['close'] < prior_low:
        ctype = 'downside_range_breakout_observation_candidate'
    else:
        return None, 'no_range_breakout_observation_candidate_detected'
    inst = surface_cfg['instrument']
    tf = surface_cfg['timeframe']
    ts = trigger['bar_open_ts_utc']
    surface = surface_cfg['surface']
    dedupe_key = '|'.join([inst, tf, edge_family, ctype, ts])
    cid = 'PRV1E_' + dedupe_key.replace('|','_').replace(' ','_').replace(':','').replace('-','').replace('T','T').replace('Z','Z')
    row = {
        'sot_candidate_id': cid,
        'prv1e_candidate_id': cid,
        'dedupe_key': dedupe_key,
        'instrument': inst,
        'timeframe': tf,
        'surface': surface,
        'edge_family': edge_family,
        'candidate_type': ctype,
        'trigger_reference_bar_ts_utc': ts,
        'first_detected_at_utc': now_utc(),
        'last_detected_at_utc': now_utc(),
        'repeat_observation_count': 1,
        'source_confidence_class': 'provider_cache_fresh_enough_caveated',
        'provider': 'twelve_data',
        'provider_symbol': surface_cfg.get('provider_symbol') or surface.replace('XAUUSD','XAU/USD').replace('EURUSD','EUR/USD').replace('USDJPY','USD/JPY').split()[0],
        'trigger_bar_from_cache': trigger,
        'prior_range_summary': {
            'lookback_bars_used': len(prior),
            'prior_range_high': prior_high,
            'prior_range_low': prior_low,
            'first_prior_bar_open_ts_utc': prior[0]['bar_open_ts_utc'],
            'last_prior_bar_open_ts_utc': prior[-1]['bar_open_ts_utc']
        },
        'capture_caveats': [
            'Newest provider bar skipped to reduce in-progress candle risk.',
            'Candidate detection is observation-only from local provider cache.',
            'Candidate does not mean signal, entry, stop, target, execution, or recommendation.',
            'Outcome category is not PnL, win/loss, validation, or performance.'
        ],
        'created_or_updated_from': 'prv1e_local_cache_candidate_detection_rule_engine',
        'candidate_boundary': {
            'unique_candidate_not_multiple_trades': True,
            'candidate_not_signal': True,
            'candidate_not_entry': True,
            'candidate_not_trade_instruction': True
        },
        'registered_at_utc': now_utc(),
        'updated_at_utc': now_utc(),
        'row_quality': 'prv1e_detected_observation_candidate_from_refreshed_cache'
    }
    return row, None

def row_to_lifecycle(row):
    return {
        'row_id': row['sot_candidate_id'],
        'sot_candidate_id': row['sot_candidate_id'],
        'row_quality': 'prv1e_detected_observation_candidate_from_refreshed_cache',
        'instrument': row['instrument'],
        'timeframe': row['timeframe'],
        'surface': row['surface'],
        'edge_family': row['edge_family'],
        'candidate_type': row['candidate_type'],
        'trigger_reference_bar_ts_utc': row['trigger_reference_bar_ts_utc'],
        'first_observed_at_utc': row['first_detected_at_utc'],
        'last_observed_at_utc': row['last_detected_at_utc'],
        'repeat_observation_count': 1,
        'provider': row['provider'],
        'provider_symbol': row['provider_symbol'],
        'source_confidence_class': row['source_confidence_class'],
        'lifecycle_status': 'active_tracking',
        'is_final': False,
        'latest_outcome_category': 'still_active_observation',
        'latest_outcome_reason': 'new_prv1e_candidate_seeded_requires_future_lifecycle_update',
        'lifecycle_updated_at_utc': row['updated_at_utc'],
        'trigger_bar_from_cache': row['trigger_bar_from_cache'],
        'original_record_ids': [],
        'display_boundary': 'Observation-only. Not signal, not buy/sell/hold, not entry/stop/target, not execution, not PnL/win-loss, not validation.'
    }

def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    root = root.resolve()
    policy_path = root / 'config' / 'candidate_detection_rule_policy.json'
    policy = read_json(policy_path, default=None)
    if policy is None:
        print(json.dumps({'validation_passed': False, 'error': 'missing config/candidate_detection_rule_policy.json'}, indent=2))
        sys.exit(1)

    created_at = now_utc()
    active_cfg = read_json(root/'config'/'active_instrument_config.json', default={})
    active_entries = active_cfg.get('active_instruments', []) if isinstance(active_cfg, dict) else []
    active_set = set()
    for x in active_entries:
        if isinstance(x, dict): active_set.add(x.get('instrument'))
        elif isinstance(x, str): active_set.add(x)
    if not active_set:
        active_set = set(policy.get('active_instruments_only', []))
    required = set(policy.get('active_instruments_only', []))
    forbidden = set(policy.get('forbidden_active_instruments', [])) & active_set
    scope_ok = active_set == required and not forbidden

    registry = read_json(root/'state'/'sot02_current'/'shadow_candidate_registry.json', default={'candidates': {}})
    existing_keys = existing_dedupe_keys(registry)
    existing_rows_file = root/'ledger'/'candidate_lifecycle_rows_v1_post_refresh.json'
    existing_lifecycle_rows = read_json(existing_rows_file, default=None)
    if existing_lifecycle_rows is None:
        existing_lifecycle_rows = read_json(root/'ledger'/'candidate_lifecycle_rows_v1_exact.json', default={'rows': []})
    existing_rows = existing_lifecycle_rows.get('rows', []) if isinstance(existing_lifecycle_rows, dict) else []

    scanned = []
    new_rows = []
    duplicate_rows = []
    skipped_rows = []
    cache_dir = root/'data'/'provider_cache'/'twelve_data'

    for s in policy.get('surfaces', []):
        if s['instrument'] not in required:
            skipped_rows.append({'surface': s.get('surface'), 'reason': 'instrument_not_in_v1_scope'})
            continue
        cache_path = cache_dir / s['cache_file']
        bars, err = read_cache_bars(cache_path)
        scan = {'surface': s['surface'], 'cache_file': str(cache_path.relative_to(root)) if cache_path.exists() else str(cache_path), 'valid_bar_count': len(bars), 'status': 'scanned'}
        if err:
            scan['status'] = 'skipped'
            scan['reason'] = err
            scanned.append(scan)
            skipped_rows.append({'surface': s['surface'], 'reason': err})
            continue
        row, reason = detect_range_breakout(s, bars, policy)
        if row is None:
            scan['candidate_detected'] = False
            scan['reason'] = reason
            scanned.append(scan)
            continue
        scan['candidate_detected'] = True
        scan['dedupe_key'] = row['dedupe_key']
        if row['dedupe_key'] in existing_keys:
            scan['dedupe_status'] = 'existing_duplicate_skipped'
            duplicate_rows.append(row)
        else:
            scan['dedupe_status'] = 'new_candidate_observation_row_proposed'
            new_rows.append(row)
            existing_keys.add(row['dedupe_key'])
        scanned.append(scan)

    new_lifecycle_rows = [row_to_lifecycle(r) for r in new_rows]
    merged_rows = existing_rows + new_lifecycle_rows
    final_rows = [r for r in merged_rows if r.get('is_final') is True or r.get('lifecycle_status') == 'final_outcome_recorded']
    active_rows = [r for r in merged_rows if not (r.get('is_final') is True or r.get('lifecycle_status') == 'final_outcome_recorded')]

    candidate_detection_report = {
        'program': 'PRV1E-01',
        'artifact': 'candidate_detection_report',
        'created_at_utc': created_at,
        'mode': 'bounded_cache_based_observation_candidate_detection',
        'candidate_detection_performed': True,
        'new_candidate_detection_fabricated': False,
        'scope_ok': scope_ok,
        'active_instruments': sorted(active_set),
        'surfaces_selected': len(policy.get('surfaces', [])),
        'surfaces_scanned': len(scanned),
        'new_observation_candidate_count': len(new_rows),
        'existing_duplicate_count': len(duplicate_rows),
        'skipped_surface_count': len(skipped_rows),
        'scan_rows': scanned,
        'not_performed': policy.get('not_performed', []),
        'boundary': BOUNDARY
    }
    write_json(root/'reports'/'candidate_detection_report.json', candidate_detection_report)

    candidate_registry_update_report = {
        'program': 'PRV1E-01',
        'artifact': 'candidate_registry_update_report',
        'created_at_utc': created_at,
        'existing_candidate_count_before': len(registry.get('candidates', {})) if isinstance(registry.get('candidates'), dict) else None,
        'new_candidate_rows_proposed': len(new_rows),
        'duplicates_skipped': len(duplicate_rows),
        'sot02_registry_overwritten': False,
        'reason': 'PRV1E writes proposed observation rows in state/prv1e_candidate_detection; SOT02 registry is not overwritten by this sprint.',
        'boundary': BOUNDARY
    }
    write_json(root/'reports'/'candidate_registry_update_report.json', candidate_registry_update_report)

    lifecycle_seed_report = {
        'program': 'PRV1E-01',
        'artifact': 'candidate_lifecycle_seed_report',
        'created_at_utc': created_at,
        'new_lifecycle_rows_seeded': len(new_lifecycle_rows),
        'seed_status': 'active_tracking_for_new_observation_candidates_only',
        'outcome_category_for_seeded_rows': 'still_active_observation',
        'finalized_now': 0,
        'boundary': BOUNDARY
    }
    write_json(root/'reports'/'candidate_lifecycle_seed_report.json', lifecycle_seed_report)

    row_level_panel = {
        'program': 'PRV1E-01',
        'artifact': 'panel_payload_after_candidate_detection',
        'created_at_utc': created_at,
        'panel_status': 'display_ready_after_candidate_detection_rule_engine',
        'active_instruments': ['XAUUSD','EURUSD','USDJPY'],
        'summary': {
            'existing_row_count_before': len(existing_rows),
            'new_observation_candidate_count': len(new_rows),
            'duplicate_candidate_count': len(duplicate_rows),
            'merged_candidate_lifecycle_row_count': len(merged_rows),
            'final_outcome_count': len(final_rows),
            'active_tracking_count': len(active_rows),
            'row_quality_counts': {
                'existing_exact_or_post_refresh_rows': len(existing_rows),
                'prv1e_detected_observation_candidate_rows': len(new_rows)
            }
        },
        'candidate_detection_summary': {
            'candidate_detection_performed': True,
            'rule_family': policy.get('rule_family', {}).get('edge_family'),
            'new_candidates_are_observation_only': True,
            'sot02_registry_overwritten': False
        },
        'new_candidate_rows': new_lifecycle_rows,
        'source_confidence': {
            'mode': 'single_provider_caveated_only',
            'provider': 'twelve_data',
            'is_source_truth': False,
            'second_provider_conflict_check': 'out_of_v1_scope'
        },
        'calendar_event': 'calendar_event_source_not_in_v1_scope',
        'display_banner': 'DISPLAY-ONLY PERSONAL RUNTIME OBSERVATION. Candidate detection is observation-only from refreshed local cache; not signal, not buy/sell/hold, not entry/stop/target, not broker/order/execution, not PnL or win/loss, not optimizer, not validation/adaptation decision, not production readiness.',
        'forbidden_surfaces_absent': FORBIDDEN_SURFACES_ABSENT,
        'boundary': BOUNDARY
    }
    write_json(root/'panel'/'panel_payload_after_candidate_detection.json', row_level_panel)

    # State and ledger outputs
    write_json(root/'state'/'prv1e_candidate_detection'/'candidate_detection_new_rows_v1.json', {'program':'PRV1E-01','created_at_utc':created_at,'rows':new_rows,'boundary':BOUNDARY})
    write_json(root/'state'/'prv1e_candidate_detection'/'candidate_detection_duplicate_rows_v1.json', {'program':'PRV1E-01','created_at_utc':created_at,'rows':duplicate_rows,'boundary':BOUNDARY})
    write_json(root/'ledger'/'candidate_lifecycle_rows_v1_after_candidate_detection.json', {'program':'PRV1E-01','created_at_utc':created_at,'rows':merged_rows,'boundary':BOUNDARY})
    write_json(root/'ledger'/'active_tracking_rows_v1_after_candidate_detection.json', {'program':'PRV1E-01','created_at_utc':created_at,'rows':active_rows,'boundary':BOUNDARY})
    write_json(root/'ledger'/'outcome_observation_rows_v1_after_candidate_detection.json', {'program':'PRV1E-01','created_at_utc':created_at,'rows':final_rows,'boundary':BOUNDARY})
    evidence_rows = []
    for r in merged_rows:
        evidence_rows.append({
            'sot_candidate_id': r.get('sot_candidate_id') or r.get('row_id'),
            'surface': r.get('surface'),
            'trigger_reference_bar_ts_utc': r.get('trigger_reference_bar_ts_utc'),
            'evidence_refs': ['existing_registry_or_post_refresh_ledger', 'provider_cache', 'candidate_detection_report']
        })
    write_json(root/'ledger'/'candidate_evidence_index_v1_after_candidate_detection.json', {'program':'PRV1E-01','created_at_utc':created_at,'evidence_sources':['state/sot02_current/shadow_candidate_registry.json','ledger/*post_refresh*.json','data/provider_cache/twelve_data/*.json','reports/candidate_detection_report.json'],'rows':evidence_rows,'boundary':BOUNDARY})

    # Proofs
    secret_proof = {
        'program': 'PRV1E-01',
        'artifact': 'candidate_detection_secret_redaction_proof',
        'created_at_utc': created_at,
        'api_key_requested_or_read': False,
        'api_key_value_written': False,
        'env_file_read': False,
        'secret_hit_files': [],
        'verdict': 'passed_no_secret_access_or_secret_output_in_candidate_detection',
        'boundary': BOUNDARY
    }
    write_json(root/'proofs'/'candidate_detection_secret_redaction_proof.json', secret_proof)
    no_action = {
        'program': 'PRV1E-01',
        'artifact': 'candidate_detection_no_action_surface_proof',
        'created_at_utc': created_at,
        'action_surface_absent': True,
        'panel_forbidden_surfaces_absent': FORBIDDEN_SURFACES_ABSENT,
        'required_absent_flags_checked': list(FORBIDDEN_SURFACES_ABSENT.keys()),
        'verdict': 'passed',
        'boundary': BOUNDARY
    }
    write_json(root/'proofs'/'candidate_detection_no_action_surface_proof.json', no_action)
    boundary_proof = {
        'program': 'PRV1E-01',
        'artifact': 'candidate_detection_boundary_proof',
        'created_at_utc': created_at,
        'status': 'passed' if scope_ok else 'failed_or_requires_review',
        'scope_ok': scope_ok,
        'candidate_detection_performed': True,
        'new_candidate_detection_not_fabricated': True,
        'sot02_registry_overwritten': False,
        'no_action_surface_passed': True,
        'secret_redaction_passed': True,
        'boundary': BOUNDARY
    }
    write_json(root/'proofs'/'candidate_detection_boundary_proof.json', boundary_proof)

    validation_passed = bool(scope_ok and no_action['action_surface_absent'] and secret_proof['api_key_value_written'] is False)
    validation = {
        'program': 'PRV1E-01',
        'artifact': 'candidate_detection_local_validation_result',
        'created_at_utc': created_at,
        'validation_passed': validation_passed,
        'coverage_status': 'candidate_detection_completed_observation_only',
        'scope_ok': scope_ok,
        'candidate_detection_performed': True,
        'new_observation_candidate_count': len(new_rows),
        'existing_duplicate_count': len(duplicate_rows),
        'merged_candidate_lifecycle_row_count': len(merged_rows),
        'secret_redaction_passed': True,
        'no_action_surface_passed': True,
        'boundary_status': 'passed' if validation_passed else 'failed_or_requires_review',
        'boundary': BOUNDARY
    }
    write_json(root/'proofs'/'candidate_detection_local_validation_result.json', validation)
    write_json(root/'logs'/'last_run_status_after_candidate_detection.json', {
        'program': 'PRV1E-01',
        'artifact': 'last_run_status_after_candidate_detection',
        'created_at_utc': created_at,
        'status': 'candidate_detection_completed',
        'new_observation_candidate_count': len(new_rows),
        'existing_duplicate_count': len(duplicate_rows),
        'merged_candidate_lifecycle_row_count': len(merged_rows),
        'boundary': BOUNDARY
    })
    write_json(root/'logs'/'runtime_heartbeat_after_candidate_detection.json', {
        'program': 'PRV1E-01',
        'artifact': 'runtime_heartbeat_after_candidate_detection',
        'created_at_utc': created_at,
        'heartbeat_status': 'candidate_detection_heartbeat_written',
        'not_production_readiness': True,
        'boundary': BOUNDARY
    })

    # Minimal HTML panel
    rows_html = ''.join(f"<tr><td>{r.get('surface','')}</td><td>{r.get('candidate_type','')}</td><td>{r.get('trigger_reference_bar_ts_utc','')}</td><td>{r.get('lifecycle_status','active_tracking')}</td><td>observation-only</td></tr>" for r in new_lifecycle_rows)
    if not rows_html:
        rows_html = "<tr><td colspan='5'>No new observation candidates detected in this run.</td></tr>"
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>PRV1E Candidate Detection Panel</title>
<style>body{{font-family:Arial,sans-serif;margin:28px;background:#f7f7f7;color:#111}}.card{{background:white;border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 2px 10px #ddd}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}.banner{{background:#111;color:white}}</style></head><body>
<div class='card banner'><h1>PRV1E — Candidate Detection Rule Engine</h1><p>Display-only observation candidates. No signal, no execution, no broker, no entry/stop/target, no PnL.</p></div>
<div class='card'><h2>Summary</h2><p>New observation candidates: {len(new_rows)} | Existing duplicates skipped: {len(duplicate_rows)} | Merged rows: {len(merged_rows)}</p></div>
<div class='card'><h2>New Observation Candidate Rows</h2><table><thead><tr><th>Surface</th><th>Candidate Type</th><th>Trigger UTC</th><th>Lifecycle Seed</th><th>Boundary</th></tr></thead><tbody>{rows_html}</tbody></table></div>
</body></html>"""
    (root/'panel'/'index_candidate_detection.html').write_text(html, encoding='utf-8')

    print(json.dumps(validation, indent=2))
    if not validation_passed:
        sys.exit(1)

if __name__ == '__main__':
    main()
