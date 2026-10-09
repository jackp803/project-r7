"""Closed public input/log sets, checked before any proof-supplied reference read."""
import re

def original_names(revision):
    short=revision[:7]
    names=['s09_public_research_setup_native_regression.py','s09_local_paper_control_native_regression.py',
        's09_owner_worker_native_regression.py','s12_storage_native_paper_reader.py','s13_native_access_integrity.py',
        's14_feedback_cli_native_paper.py','S14LocalFakeRclone.exe','S14LocalFakeRclone.cs',
        's09_owner_worker_source_qualify.py','s09_public_research_setup_source_qualify.py',
        'local_windows_qualification_awake.py','s09_native_public_research_setup_probe.py','s09_native_long_backup_probe.py']
    return {'artifacts/'+name for name in names}|{
        'workspaces/project-r7-productization-master-20261002/'+name for name in
        ['src/application/platform/_loopback_probe.py','tools/build_product.py','tools/verify_native_product.py']}|{
        f'artifacts/r7-productization-S09-public-research-setup-qualified-{short}-long-path-fixed/'+name
        for name in ['qualification.json','qualification-context.json']}

def continuation_names(revision,*,guarded):
    names=['s09_native_long_backup_continuation.py','s09_native_long_backup_probe.py',
        's09_native_long_backup_probe.original-import-failure.py',
        f'S09-public-research-setup-{revision[:7]}-native-regression.json',
        's09_owner_worker_native_regression.py','s09_owner_worker_source_qualify.py',
        's09_local_paper_control_native_regression.py','local_windows_qualification_awake.py']
    if guarded:names+=['s09_native_evidence_guards.py']
    return {'artifacts/'+name for name in names}

def binding(value,names,*,aggregate_required):
    before=value['input_hashes_before']
    assert isinstance(before,dict) and set(before)==names,'EXACT_PUBLIC_INPUT_SET_REQUIRED'
    assert all(isinstance(v,str) and re.fullmatch('sha256:[0-9a-f]{64}',v) for v in before.values())
    if aggregate_required:assert 'input_hashes_after' in value and value.get('source_inputs_unchanged') is True
    if 'input_hashes_after' in value:assert value['input_hashes_after']==before,'EXPLICIT_INPUT_DRIFT_REJECTED'
    if 'source_inputs_unchanged' in value:assert value['source_inputs_unchanged'] is True,'EXPLICIT_SOURCE_DRIFT_REJECTED'

def original_binding(value,revision):
    binding(value,original_names(revision),aggregate_required=False)
    assert value['executable_revision']==revision and value['passed'] is False
    assert [c['label'] for c in value['commands']]==['build','smoke','historical-paper','paper-reader','public-setup','long-backup']
    for row in value['commands']:
        assert row['log']==f'S09-public-research-setup-{revision[:7]}-native-{row["label"]}.log'

def continuation_binding(value,revision,*,guarded,label):
    assert label in ('fixed','private-fixed','bounded-fixed')
    binding(value,continuation_names(revision,guarded=guarded),aggregate_required=True)
    assert value['executable_revision']==revision
    assert value['log']==f'S09-public-research-setup-{revision[:7]}-native-long-backup-{label}.log'
