"""Offline JSON package authoring through the actual E2 parser.

No cloud connection, executable strategy, policy selection or financial
authority is created. Capability availability is distinct from execution.
"""
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path

from application.cloud.manifest import (PayloadSpec,byte_hash,canonical_bytes,load_json,
                                        parse_manifest,safe_component,verify_payload)
from application.cloud.protocol import CloudError
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.supervision import _local_path
from strategy import StrategyError,compute_content_hash,parse_strategy_definition
from strategy.v02.capabilities import build_capability_snapshot,check_compatibility


class AuthoringError(ValueError):
    def __init__(self,code,*,gaps=()):
        self.code,self.gaps=code,gaps
        super().__init__(code)


def emit_package(definition,destination,*,submission_id,package_version='0.2',created_at=None,
                 created_by='offline author',research_hypothesis='',requested_dataset_profile='unselected',
                 requested_validation_profile='unselected',requested_robustness_profile='unselected',
                 intent_class='EVERGREEN_STRATEGY',validity=None,notes=None):
    """Create a fresh local folder, payloads first and validated manifest last."""
    try:
        safe_component(submission_id)
        target=Path(destination).absolute()
        _local_path(target)
        if target.exists() or not target.parent.is_dir():
            raise AuthoringError('FRESH_AUTHORING_DESTINATION_REQUIRED')
        if package_version not in ('0.1','0.2'):
            raise AuthoringError('UNSUPPORTED_PACKAGE_VERSION')
        document=load_json(definition if isinstance(definition,bytes) else canonical_bytes(definition),256*1024)
        # The helper computes semantic identity; E2 remains the sole validator.
        document['content_hash']=compute_content_hash(document)
        snapshot=build_capability_snapshot()
        compatibility=None
        if document.get('runtime_compatibility',{}).get('runtime_version')=='0.2.0':
            compatibility=check_compatibility(document,snapshot)
            gaps=tuple(asdict(gap) for gap in compatibility.gaps if gap.reason!='EXECUTION_NOT_QUALIFIED')
            if gaps:
                raise AuthoringError('CAPABILITY_GAP',gaps=gaps)
        raw=canonical_bytes(document)
        parsed=parse_strategy_definition(raw)
        if package_version=='0.1' and parsed.runtime_version!='0.1.0':
            raise AuthoringError('PROFILE_UPGRADE_REQUIRED')
        manifest=dict(package_schema_version='r7-strategy-package-v'+package_version,submission_id=submission_id,
            strategy_id=parsed.strategy_id,strategy_version=parsed.strategy_version,strategy_content_hash=parsed.content_hash,
            created_at=created_at or datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),created_by=created_by,
            research_hypothesis=research_hypothesis,requested_dataset_profile=requested_dataset_profile,
            requested_validation_profile=requested_validation_profile,requested_robustness_profile=requested_robustness_profile)
        payloads={'strategy.json':raw}
        if package_version=='0.1':
            if notes is not None or intent_class!='EVERGREEN_STRATEGY' or validity not in (None,{'from':None,'until':None}):
                raise AuthoringError('PROFILE_UPGRADE_REQUIRED')
            manifest.update(strategy_definition_file='strategy.json',strategy_definition_sha256=byte_hash(raw))
        else:
            rows=[dict(role='strategy_definition',relative_path='strategy.json',media_type='application/json',byte_length=len(raw),sha256=byte_hash(raw))]
            if notes is not None:
                if not isinstance(notes,str):raise AuthoringError('NOTES_NOT_UTF8')
                note_raw=notes.encode('utf-8')
                spec=PayloadSpec('research_notes','research_notes.md','text/markdown',len(note_raw),byte_hash(note_raw))
                verify_payload(spec,note_raw)
                payloads['research_notes.md']=note_raw;rows.append(asdict(spec))
            manifest.update(required_runtime_profile=dict(runtime_family=parsed.runtime_family,runtime_version=parsed.runtime_version),
                capability_snapshot_hash=snapshot.snapshot_hash,payloads=rows,intent_class=intent_class,
                validity=validity if validity is not None else {'from':None,'until':None})
        manifest_raw=canonical_bytes(manifest)
        verified=parse_manifest(manifest_raw)
        create_private_directory(target)
        for name,payload in payloads.items():write_private_new(target/name,payload)
        write_private_new(target/'manifest.json',manifest_raw)
        return dict(status='AUTHORING_PACKAGE_CREATED',submission_id=submission_id,manifest_hash=verified.manifest_hash,
            strategy_content_hash=parsed.content_hash,payload_hashes={name:byte_hash(payload) for name,payload in payloads.items()},
            capability_snapshot_hash=snapshot.snapshot_hash,execution_evidence='NOT_RUN',financial_authority='NONE')
    except AuthoringError:
        raise
    except CloudError as error:
        raise AuthoringError(error.reason) from None
    except StrategyError:
        raise AuthoringError('E2_DEFINITION_REJECTED') from None
    except (OSError,TypeError,ValueError):
        raise AuthoringError('LOCAL_AUTHORING_FAILED') from None
