#!/usr/bin/env python3
import json, sys
from pathlib import Path

def read_json(path):
    with open(path, 'r', encoding='utf-8') as f: return json.load(f)

def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    required = [
        'reports/candidate_detection_report.json',
        'reports/candidate_registry_update_report.json',
        'reports/candidate_lifecycle_seed_report.json',
        'panel/panel_payload_after_candidate_detection.json',
        'proofs/candidate_detection_secret_redaction_proof.json',
        'proofs/candidate_detection_no_action_surface_proof.json',
        'proofs/candidate_detection_boundary_proof.json',
        'proofs/candidate_detection_local_validation_result.json',
        'ledger/candidate_lifecycle_rows_v1_after_candidate_detection.json',
        'state/prv1e_candidate_detection/candidate_detection_new_rows_v1.json'
    ]
    missing = [p for p in required if not (root/p).exists()]
    result = {'program':'PRV1E-01','artifact':'candidate_detection_validation_review','missing_files':missing}
    if missing:
        result.update({'validation_passed':False,'boundary_status':'failed_missing_files'})
        print(json.dumps(result, indent=2)); sys.exit(1)
    val = read_json(root/'proofs/candidate_detection_local_validation_result.json')
    secret = read_json(root/'proofs/candidate_detection_secret_redaction_proof.json')
    no_action = read_json(root/'proofs/candidate_detection_no_action_surface_proof.json')
    boundary = read_json(root/'proofs/candidate_detection_boundary_proof.json')
    passed = bool(val.get('validation_passed') and secret.get('api_key_value_written') is False and no_action.get('action_surface_absent') is True and boundary.get('status') == 'passed')
    result.update({
        'validation_passed': passed,
        'candidate_detection_performed': val.get('candidate_detection_performed'),
        'new_observation_candidate_count': val.get('new_observation_candidate_count'),
        'existing_duplicate_count': val.get('existing_duplicate_count'),
        'secret_redaction_passed': secret.get('verdict','').startswith('passed'),
        'no_action_surface_passed': no_action.get('action_surface_absent') is True,
        'boundary_status': 'passed' if passed else 'failed_or_requires_review'
    })
    print(json.dumps(result, indent=2))
    sys.exit(0 if passed else 1)
if __name__ == '__main__': main()
