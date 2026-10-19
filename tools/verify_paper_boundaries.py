"""Actual installed component checks, separate from final PQR receipt issuance."""
from verify_paper_product import PublicFixture


REQUIRED_ASSERTIONS=(
    'ACTUAL_SOFTWARE_STORE_MISSING_DENIED','ACTUAL_SOFTWARE_RECEIPT_MISSING_DENIED',
    'ACTUAL_DIAGNOSTIC_RECEIPT_REPLAY','ACTUAL_DIAGNOSTIC_RECEIPT_CONFLICT_DENIED',
    'ACTUAL_RECEIPT_NAMESPACE_DENIED','ACTUAL_PARTIAL_DOCTOR_RECEIPT_NOT_QUALIFIED',
    'ACTUAL_RUNTIME_MISSING_DENIED','ACTUAL_NATIVE_SUPERVISOR_CURRENT_READ',
    'ACTUAL_NATIVE_RUNTIME_WRONG_CONFIG_DENIED','ACTUAL_NATIVE_RUNTIME_STOPPED_DENIED',
    'ACTUAL_COMPONENT_ARTIFACT_MUTATION_DENIED',
    'SUBJECT_DENIED_EXECUTABLE_REVISION','SUBJECT_DENIED_IMPLEMENTATION_HASH',
    'SUBJECT_DENIED_BUILD_HASH','SUBJECT_DENIED_PLATFORM_ID','SUBJECT_DENIED_CAPABILITY_HASH',
    'SYNTHETIC_MISSING_MEMBER_DENIED','SYNTHETIC_REORDERED_MEMBERS_DENIED',
    'SYNTHETIC_ZERO_TEST_DENIED','SYNTHETIC_UNREAPED_DENIED',
    'SYNTHETIC_OBSERVATION_PENDING_DENIED','SYNTHETIC_OBSERVATION_OLD_AGE_DENIED',
    'SYNTHETIC_OBSERVATION_WRONG_RECEIPT_DENIED','SYNTHETIC_OBSERVATION_WRONG_SELECTION_GENERATION_DENIED',
    'SYNTHETIC_OBSERVATION_WRONG_OWNER_DENIED','SYNTHETIC_OBSERVATION_CALLER_EXTRA_DENIED',
)


class NativeBoundaryFlow(PublicFixture):
    def __init__(self,package,output,*,expected_identity=None):
        super().__init__(package,output,'component-boundaries',expected_identity=expected_identity)
        self.observation.update(namespace='LOCAL_RESEARCH',scoped_native_boundaries_passed=False,
            qualification_complete=False,financial_selection='NONE',paper='NOT_STARTED')

    def run(self):
        self.command('init',['init-profile','--config',self.config,'--data-root',self.data,
            '--instance-id','native-component-boundaries'])
        result=self.command('boundary-diagnostic',['_paper-native-boundary-check','--config',self.config],timeout=180)
        names=result.get('assertions',[])
        if (result.get('schema_version')!='r7-native-boundary-diagnostic-v1'
                or result.get('status')!='COMPONENT_CHECKS_PASS' or type(names) is not list
                or any(type(name) is not str for name in names) or len(names)!=len(set(names))
                or result.get('actual_assertions')!=len(names) or not set(REQUIRED_ASSERTIONS).issubset(names)
                or result.get('qualification_complete') is not False or result.get('completed_pqr_groups')!=0
                or result.get('software_eligibility')!='NOT_QUALIFIED'
                or result.get('diagnostic_all_recorded_checks_passed') is not True
                or result.get('synthetic_models')!='IN_MEMORY_ONLY_NEVER_STORED'
                or result.get('synthetic_represented_members_not_executed')!=7
                or result.get('financial_selection')!='NONE' or result.get('paper')!='NOT_STARTED'
                or result.get('provider_requests')!=0 or result.get('provider_mutation')!=0
                or result.get('credentials')!='NONE' or result.get('capital')!='NONE'
                or any(result.get('subject',{}).get(key)!=value for key,value in self.identity.items())):
            raise ValueError('Actual installed non-authoritative boundary checks incomplete')
        self.guard()
        self.observation.update(diagnostic=result,scoped_native_boundaries_passed=True)
        self.persist()
        return self.observation


def verify_slice(package,output,identity):
    flow=NativeBoundaryFlow(package,output/'component-boundaries',expected_identity=identity)
    try:return [flow.run()]
    except Exception as error:
        flow.observation.update(passed=False,scoped_native_boundaries_passed=False,error_type=type(error).__name__)
        flow.persist()
        return [flow.observation]
