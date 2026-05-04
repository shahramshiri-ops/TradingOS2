#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def main():
    root = Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
    required = [
        'reports/candidate_detection_report.json',
        'reports/candidate_registry_update_report.json',
        'reports/candidate_lifecycle_seed_report.json',
        'panel/panel_payload_after_candidate_detection.json',
        'proofs/candidate_detection_secret_redaction_proof.json',
        'proofs/candidate_detection_no_action_surface_proof.json',
        'proofs/candidate_detection_boundary_proof.json',
        'proofs/candidate_detection_local_validation_result.json',
    ]
    missing=[x for x in required if not (root/x).exists()]
    report = read(root/'reports/candidate_detection_report.json') if not missing else {}
    val = read(root/'proofs/candidate_detection_local_validation_result.json') if not missing else {}
    secret = read(root/'proofs/candidate_detection_secret_redaction_proof.json') if not missing else {}
    action = read(root/'proofs/candidate_detection_no_action_surface_proof.json') if not missing else {}
    boundary = read(root/'proofs/candidate_detection_boundary_proof.json') if not missing else {}
    result = {
        'program':'PRV1E-01',
        'artifact':'candidate_detection_strict_validation_result',
        'validation_passed': (not missing and val.get('validation_passed') is True and report.get('valid_cache_surface_count',0)>0 and secret.get('api_key_requested_or_read') is False and secret.get('api_key_value_written') is False and action.get('action_surface_absent') is True and boundary.get('status')=='passed'),
        'missing_files': missing,
        'valid_cache_surface_count': report.get('valid_cache_surface_count'),
        'new_observation_candidate_count': report.get('new_observation_candidate_count'),
        'existing_duplicate_count': report.get('existing_duplicate_count'),
        'secret_redaction_passed': secret.get('verdict','').startswith('passed'),
        'no_action_surface_passed': action.get('action_surface_absent') is True,
        'boundary_status': boundary.get('status')
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result['validation_passed'] else 1)
if __name__=='__main__': main()
