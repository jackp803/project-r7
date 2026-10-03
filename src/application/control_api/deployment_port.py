"""Exact E6 deployment control; browser close/pause never means flatness."""
import json
from application.control_api.approval_port import ApprovalControlPort
from application.control_api.errors import APIError
from registry import StrategyIdentity,StrategyPlatformService,ConcurrencyConflict,EvidenceGateError
from registry.models import InvalidTransition


class DeploymentControlPort(ApprovalControlPort):
    def _subject(self,e6,identity,resource=None):
        if not isinstance(e6,StrategyPlatformService) or e6.research_namespace!=self.namespace:
            raise APIError('NOT_CONFIGURED','ACTUAL_SAME_NAMESPACE_E6_REQUIRED',503)
        subject=e6.deployment_control_subject(identity)
        if resource is not None and (subject is None or resource!='deployment:'+subject.deployment_id):
            raise APIError('CONFLICT','EXACT_DEPLOYMENT_SUBJECT_REQUIRED',409)
        return subject

    def strategy_subject(self,identity):
        with self._factory() as e6:subject=self._subject(e6,identity)
        if subject is None:return None
        envelope=json.loads(subject.envelope_json)
        return dict(deployment_id=subject.deployment_id,strategy_id=identity.strategy_id,strategy_version=identity.strategy_version,
            strategy_content_hash=subject.strategy_content_hash,registry_revision=subject.registry_revision,namespace=subject.namespace,
            lifecycle_state=subject.lifecycle_state,approval_record_id=subject.approval_record_id,envelope_hash=subject.envelope_hash,
            envelope=envelope,release=envelope['release'],activation_evidence_id=subject.activation_evidence_id,
            observed_at=subject.observed_at,financial_confirmation_available=self.namespace=='LOCAL_RESEARCH',
            reason_codes=['FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN'] if self.namespace=='FIXTURE' else ['CURRENT_ACTIVATION_OWNER_CHECK_REQUIRED'])

    def revision(self,resource,arguments):
        identity=StrategyIdentity(arguments['strategy_id'],arguments['strategy_version'])
        with self._factory() as e6:return self._subject(e6,identity,resource).registry_revision

    def execute(self,operation,resource,arguments,*,actor,human,command_id,expected_revision):
        if operation=='DEPLOYMENT_ACTIVATE':
            if self.namespace=='FIXTURE':raise APIError('AUTHORIZATION_REQUIRED','FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN',403)
            if self.issuer is None or self.issuer.authorize(human)!=actor:
                raise APIError('AUTHORIZATION_REQUIRED','SERVER_BOUND_ACTOR_REQUIRED',403)
        elif operation!='DEPLOYMENT_PAUSE':raise APIError('INVALID_INPUT','DEPLOYMENT_OPERATION_REQUIRED',422)
        identity=StrategyIdentity(arguments['strategy_id'],arguments['strategy_version'])
        try:
            with self._factory() as e6:
                self._subject(e6,identity,resource)
                if operation=='DEPLOYMENT_PAUSE':
                    result=e6.degrade(identity,actor=actor,reason_codes=('USER_ENTRY_PAUSE',),command_id=command_id,expected_revision=expected_revision)
                else:
                    result=e6.activate_selected_deployment(identity,evidence_ref=arguments['evidence_ref'],authenticated_human=human,
                        command_id=command_id,expected_revision=expected_revision)
                audit=e6.lifecycle_command_audit(command_id)
                if audit is None:raise APIError('UNAVAILABLE','ACTUAL_DEPLOYMENT_RECEIPT_REQUIRED',503)
            return dict(command_id=command_id,actor=actor,resource=resource,expected_revision=expected_revision,
                resource_revision=result.registry_revision,status='PAUSED' if operation=='DEPLOYMENT_PAUSE' else 'COMPLETE',
                effect_ref='e6-transition:'+audit.transition_id,observed_at=audit.recorded_at,
                reason_codes=['NEW_ENTRIES_DISABLED_MANAGEMENT_RETAINED'] if operation=='DEPLOYMENT_PAUSE' else ['DEPLOYMENT_OWNER_ACCEPTED_RUNTIME_ATTACHMENT_REQUIRED'])
        except (ConcurrencyConflict,InvalidTransition):
            raise APIError('CONFLICT','DEPLOYMENT_OWNER_COMMAND_CONFLICT',409) from None
        except EvidenceGateError:
            raise APIError('INSUFFICIENT_EVIDENCE','CURRENT_DEPLOYMENT_AUTHORITY_REQUIRED',409) from None
