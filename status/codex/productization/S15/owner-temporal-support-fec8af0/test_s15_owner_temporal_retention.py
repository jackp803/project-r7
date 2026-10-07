"""Regression for retained-path compatibility without losing exact crosslinks."""
import ast,copy,json,unittest
import retain_s15_owner_temporal_support as tool
class OwnerTemporalRetentionTests(unittest.TestCase):
    def setUp(self):
        self.index=tool.decode(tool.capture(tool.base/'S15-executed-case-index-fec8af0.json'))
        self.matrix=tool.decode(tool.capture(tool.repo/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json'))
        root=tool.repo/'status/codex/productization/S15/scoped-source-support-fec8af0'
        self.old={f'S15-{g}-support-{s}-fec8af0.json':tool.capture(root/f'S15-{g}-support-{s}-fec8af0.json')
            for g in ('strategy','cloud','data-research') for s in ('selection','draft')}
    def current(self,group,stem):return tool.decode(tool.capture(tool.base/f'S15-{group}-support-{stem}-fec8af0.json'))
    def tactical(self,mode):
        stem='S15-tactical-owner-target-reason-'+mode
        tree=ast.parse(tool.capture(tool.base/'s15_tactical_owner_acceptance_cases.py'))
        names=[m.name for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='TacticalOwnerAcceptanceTests'
            for m in c.body if isinstance(m,ast.FunctionDef) and m.name.startswith('test_')]
        return tool.decode(tool.capture(tool.base/(stem+'.json'))),tool.capture(tool.base/(stem+'.log')),names
    def test_actual_prior_retained_snapshot_preserves_original_case_crosslinks(self):
        ids,cases=tool.validate_prior_support(self.index,self.matrix,self.old)
        self.assertEqual(28,len(ids));self.assertEqual(111,len(cases))
    def test_current_untransformed_drafts_preserve_original_case_crosslinks(self):
        union=set()
        for group in ('temporal','lifecycle-trading'):
            union.update(tool.validate_support(self.index,self.matrix,self.current(group,'selection'),self.current(group,'draft')))
        self.assertEqual(94,len(union))
    def test_changed_retained_command_is_not_accepted_as_path_sanitization(self):
        changed=dict(self.old);name='S15-strategy-support-draft-fec8af0.json';draft=tool.decode(changed[name])
        draft['requirements'][0]['supporting_executed_cases'][0]['command'].append('--arbitrary-command')
        changed[name]=json.dumps(draft).encode()
        with self.assertRaises(AssertionError):tool.validate_prior_support(self.index,self.matrix,changed)
    def test_changed_source_line_cannot_reuse_original_case_identity(self):
        selection=self.current('temporal','selection');draft=self.current('temporal','draft')
        draft['requirements'][0]['supporting_executed_cases'][0]['line']+=1
        with self.assertRaises(AssertionError):tool.validate_support(self.index,self.matrix,selection,draft)
    def test_actual_normal_and_mutation_reports_have_distinct_expected_outcomes(self):
        for mode in ('NORMAL','MUTATION_CONTROL'):
            proof,log,names=self.tactical(mode);outcomes=tool.validate_tactical(proof,log,mode,names)
            self.assertEqual(5,len(outcomes));self.assertEqual(0 if mode=='NORMAL' else 3,list(outcomes.values()).count('FAIL'))
    def test_same_aggregate_counts_with_wrong_named_suite_are_rejected(self):
        proof,log,names=self.tactical('NORMAL');altered=log.replace(names[0].encode(),b'test_unreviewed_case')
        proof['log_sha256']=tool.digest(altered)
        with self.assertRaises(AssertionError):tool.validate_tactical(proof,altered,'NORMAL',names)
    def test_changed_fixture_input_cannot_reuse_success_report(self):
        proof,log,names=self.tactical('NORMAL');proof=copy.deepcopy(proof)
        first=next(iter(proof['input_sha256_after']));proof['input_sha256_after'][first]='sha256:'+'0'*64
        with self.assertRaises(AssertionError):tool.validate_tactical(proof,log,'NORMAL',names)
if __name__=='__main__':unittest.main()
