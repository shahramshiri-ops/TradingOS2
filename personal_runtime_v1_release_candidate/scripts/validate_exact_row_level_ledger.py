import json, sys
from pathlib import Path
root = Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
ledger = json.loads((root/'ledger'/'candidate_observation_ledger_v1_exact.json').read_text(encoding='utf-8'))
assert ledger['candidate_count'] == 4
assert ledger['lifecycle_count'] == 4
assert ledger['row_quality_counts']['exact_current_sot02_row'] == 4
assert ledger['row_quality_counts']['aggregate_resolved_row_shell'] == 0
assert ledger['status_counts'].get('final_outcome_recorded') == 3
assert ledger['status_counts'].get('active_tracking') == 1
for k,v in ledger['boundary'].items():
    assert v is True, k
print('PRV1A exact row ledger validation passed: 4 exact rows, 0 shell rows, display-only boundaries intact.')
