"""Persist actual Codex tool TTY enrollment observation; no auth database writes."""
from s09_owner_worker_native_regression import BASE,OwnedProof,sha,stamp
from s09_local_paper_control_native_regression import read_input
import json,sys,re
revision,scenario,observed_session=sys.argv[1:]
assert re.fullmatch('[0-9a-f]{40}',revision) and scenario in ('positive','oos-loss','insufficient-oos')
folder=BASE/f'r7-native-S09-forward-ui-user-flow-{revision[:7]}-{scenario}'
session=int(observed_session);assert session>0
raw=read_input(folder/'native-normal-fixture-flow.json',8*1024**2)
prepared=json.loads(raw)
assert prepared['phase']=='AWAITING_OBSERVED_NATIVE_TTY'
assert prepared['executable_revision']==revision and prepared['scenario']==scenario
transcript='本機密碼（至少 12 字元）: [HIDDEN INPUT]\n再次輸入本機密碼: [HIDDEN INPUT]\n{"status": "OWNER_CONFIGURED", "namespace": "FIXTURE"}\n'
with OwnedProof(folder/'observed-native-tty-enrollment.log') as owner:
    owner.stream.write(transcript.encode('utf-8'));owner.stream.flush();owner.require_owned()
with OwnedProof(folder/'observed-native-tty-enrollment.json') as owner:
    owner.persist(dict(status='OWNER_CONFIGURED',namespace='FIXTURE',command='PUBLIC_ENROLL_OWNER',
      actual_tool_tty=True,password_echoed=False,exit_code=0,credentials='NONE',
      synthetic_local_login='EPHEMERAL_FIXTURE_ONLY',observed_tool_session=session,observed_at_utc=stamp(),
      evidence_origin='ACTUAL_INTERACTIVE_CODEX_EXEC_COMMAND_AND_TWO_WRITE_STDIN_RESULTS;SANITIZED_OBSERVER_RECORD',
      native_build_identity=prepared['native_build_identity'],config_sha256=prepared['initial_profile_sha256'],
      observed_transcript_sha256=sha(transcript.encode('utf-8')),observer_launcher_sha256=sha(read_input(__import__('pathlib').Path(__file__),1024**2))))
print('OBSERVED_NATIVE_TTY_ENROLLMENT_RETAINED;NO_PASSWORD_OR_AUTH_DATABASE_PUBLICATION')
