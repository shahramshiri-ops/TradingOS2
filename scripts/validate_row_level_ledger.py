#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
ledger_path = root / 'ledger' / 'candidate_observation_ledger_v1.json'
proof_path = root / 'proofs' / 'row_level_boundary_proof.json'
ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
rows = ledger['rows']
summary = ledger['summary']
assert len(rows) == 4, f"expected 4 rows, got {len(rows)}"
assert summary['active_tracking_count'] == 1, summary
assert summary['final_outcome_count'] == 3, summary
assert summary['outcome_counts'] == {
    'favorable_observation': 1,
    'invalidated_observation': 1,
    'still_active_observation': 1,
    'unfavorable_observation': 1,
}, summary['outcome_counts']
proof = json.loads(proof_path.read_text(encoding='utf-8'))
assert proof['count_reconciliation_passed'] is True
print(json.dumps({
    'status': 'row_level_ledger_validation_passed_with_caveats',
    'rows': len(rows),
    'exact_rows': ledger['row_detail_completion']['exact_rows_resolved'],
    'aggregate_shell_rows': ledger['row_detail_completion']['aggregate_shell_rows'],
    'boundary': 'display_only_no_signal_no_execution'
}, indent=2))
