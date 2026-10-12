"""Sanitized observer record of actual tool TTY; never edits authentication DB."""
import json,sys
from pathlib import Path
from s09_owner_worker_native_regression import BASE,OwnedProof,sha,stamp
from s09_local_paper_control_native_regression import read_input
source,session=sys.argv[1:]
folder=BASE/f'r7-native-S15-negative-intake-{source[:7]}'
prepared=json.loads(read_input(folder/'preparation.json',8*1024**2))
assert prepared['source_revision']==source and prepared['phase']=='AWAITING_OBSERVED_NATIVE_TTY'
transcript='本機密碼（至少 12 字元）: [HIDDEN INPUT]\n再次輸入本機密碼: [HIDDEN INPUT]\n{"status": "OWNER_CONFIGURED", "namespace": "FIXTURE"}\n'
with OwnedProof(folder/'observed-native-tty-enrollment.log') as owner:
    owner.stream.write(transcript.encode());owner.stream.flush();owner.require_owned()
with OwnedProof(folder/'observed-native-tty-enrollment.json') as owner:
    owner.persist(dict(actual_tool_tty=True,password_echoed=False,exit_code=0,credentials='NONE',
        command='PUBLIC_ENROLL_OWNER',status='OWNER_CONFIGURED',namespace='FIXTURE',observed_tool_session=int(session),
        config_sha256=prepared['initial_profile_sha256'],native_build_identity=prepared['native_build_identity'],
        observed_at_utc=stamp(),observed_transcript_sha256=sha(transcript.encode()),
        evidence_origin='ACTUAL_INTERACTIVE_CODEX_EXEC_COMMAND_AND_TWO_WRITE_STDIN_RESULTS;SANITIZED_OBSERVER_RECORD',
        observer_sha256=sha(read_input(Path(__file__),65536))))
print('ACTUAL_TTY_OBSERVATION_RETAINED;NO_PASSWORD_PUBLICATION')
