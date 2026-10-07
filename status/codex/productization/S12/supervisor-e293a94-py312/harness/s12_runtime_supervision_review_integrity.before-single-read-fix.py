"""Exact bounded review inventories and primary executed proof, without PASS imports."""
import hashlib
from pathlib import Path

from s13_installer_acceptance_integrity import read_bound_report
from s14_feedback_acceptance_core import require_artifact


def _bind(path, expected, bound, project):
    path=Path(path)
    require_artifact(path.parent,path.name,expected)
    reference=path.relative_to(project).as_posix()
    if reference in bound and bound[reference]!=expected:
        raise ValueError('Conflicting primary artifact commitment')
    bound[reference]=expected


def validate_review_inventory(review, *, kind, files, bound, project):
    if (not files or review.get('kind')!=kind or review.get('reviewer')!='/root/qualification_review'
            or review.get('reviewer_execution')!='NONE'
            or type(review.get('remaining_critical')) is not int or review['remaining_critical']!=0
            or type(review.get('remaining_important')) is not int or review['remaining_important']!=0
            or not isinstance(review.get('reviewed_files'),dict) or set(review['reviewed_files'])!=set(files)):
        raise ValueError('Complete exact independent review inventory required')
    for reference,path in files.items():
        _bind(path,review['reviewed_files'][reference],bound,project)


def validate_primary_proof(folder, stem, count, *, inputs, input_fields, bound, project):
    from application.qualification import parse_result
    proof=read_bound_report(folder,stem+'.json',bound,project)
    before,after=input_fields
    if (proof.get('passed') is not True or proof.get('tree_reaped') is not True
            or proof.get('harness_binding')!='BEFORE_AND_AFTER_EXECUTION'
            or proof.get('exit_code')!=0 or proof.get('tests_run')!=count
            or any(proof.get(key)!=0 for key in ('failures','errors','skipped'))
            or not inputs or proof.get(before)!=proof.get(after)
            or not isinstance(proof.get(before),dict) or set(proof[before])!=set(inputs)):
        raise ValueError('Complete bound executed regression required')
    log=Path(folder)/(stem+'.log')
    _bind(log,proof['log_sha256'],bound,project)
    parsed=parse_result(log.read_text(encoding='utf-8'),returncode=proof['exit_code'])
    if not parsed.passed or parsed.tests_run!=count or parsed.failures or parsed.errors or parsed.skipped:
        raise ValueError('Primary execution log/count mismatch')
    for name,path in inputs.items():
        _bind(path,proof[before][name],bound,project)
    return proof
