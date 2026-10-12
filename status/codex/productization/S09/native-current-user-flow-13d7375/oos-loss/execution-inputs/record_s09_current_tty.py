"""Sanitized observer of actual hidden tool TTY results, not an auth fixture seam."""
import json,sys
from s09_owner_worker_native_regression import BASE,OwnedProof,sha,stamp
from s09_local_paper_control_native_regression import read_input
from pathlib import Path
source,scenario,session=sys.argv[1:]
assert scenario in ('positive','oos-loss','insufficient-oos')
folder=BASE/f'r7-native-S09-current-user-flow-13d7375-{scenario}'
p=json.loads(read_input(folder/'native-normal-fixture-flow.json',8*1024**2))
assert p['source_revision']==source and p['phase']=='AWAITING_OBSERVED_NATIVE_TTY'
transcript='本機密碼（至少 12 字元）: [HIDDEN INPUT]\n再次輸入本機密碼: [HIDDEN INPUT]\n{"status": "OWNER_CONFIGURED", "namespace": "FIXTURE"}\n'
with OwnedProof(folder/'observed-native-tty-enrollment.log') as proof:
    proof.stream.write(transcript.encode());proof.stream.flush();proof.require_owned()
with OwnedProof(folder/'observed-native-tty-enrollment.json') as proof:
    proof.persist(dict(actual_tool_tty=True,password_echoed=False,exit_code=0,credentials='NONE',
        command='PUBLIC_ENROLL_OWNER',status='OWNER_CONFIGURED',namespace='FIXTURE',observed_tool_session=int(session),
        config_sha256=p['initial_profile_sha256'],native_build_identity=p['native_build_identity'],observed_at_utc=stamp(),
        observed_transcript_sha256=sha(transcript.encode()),observer_sha256=sha(read_input(Path(__file__),65536)),
        evidence_origin='ACTUAL_CODEX_EXEC_COMMAND_TTY_AND_TWO_WRITE_STDIN_RESULTS;SANITIZED_OBSERVER_RECORD'))
print('ACTUAL_TTY_OBSERVATION_RETAINED;NO_PASSWORD_PUBLICATION')
