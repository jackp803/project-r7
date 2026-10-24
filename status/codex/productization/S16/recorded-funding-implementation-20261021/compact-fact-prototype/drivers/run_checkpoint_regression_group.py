"""Fixed serial regression groups; each child has the original300s hard budget."""
import json,sys
from run_compact_trade_corpus_drained import bounded

groups={
    'identity-worker':('tests.application.test_runtime_identity_read','tests.application.test_native_paper_release_adapter',
        'tests.application.test_native_paper_release_observation','tests.application.test_control_process_supervision',
        'tests.application.test_paper_owner_worker','tests.application.test_paper_history_worker'),
    'encoded-funding':('tests.product.test_paper_encoded_checkpoint_consumers','tests.product.test_paper_recorded_funding',
        'tests.product.test_paper_history_gates'),
    'legacy-runtime':('tests.product.test_paper_runtime_v02',),
}
if len(sys.argv)!=2 or sys.argv[1] not in groups:raise ValueError('Fixed group required')
group=sys.argv[1]
code,raw,wall=bounded([sys.executable,'-m','unittest','-v',*groups[group]])
sys.stdout.buffer.write(raw);print(json.dumps(dict(controller_status='REAPED',group=group,exit_code=code,wall_seconds=wall)),flush=True)
raise SystemExit(code)
