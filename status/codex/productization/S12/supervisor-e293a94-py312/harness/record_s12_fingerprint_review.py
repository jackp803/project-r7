from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent;project=base.parent
prefix='workspaces/project-r7-productization-master-20261002/'
files={
 prefix+'src/strategy/v02/capabilities.py':'3afe1d0dae8cadd9c6870e9c4492bb5e0b9f794e420772f0088da95d3adcd326',
 prefix+'tests/strategy/test_v02_capabilities.py':'9586f93eefa2cec5c89177bc677f6166ab1887a6bebf781d0dec85110bb8cb44',
 prefix+'docs/product/v0_2/SOURCE_IDENTITY_TRAVERSAL_REMEDIATION.md':'d2ee472361d4fb174aaaf49a2db3f7d1bd4475e21fc4996dc8d102447bc4c2bc',
 'artifacts/S12-source-fingerprint-remediation-plan.md':'743d33a6697c07606e45273e24ff1091c12ba7b9534f424c07bd22f8cc70d359',
 'artifacts/benchmark_s12_fresh_fingerprint.py':'3f4fe6cf158650984171aad16da3e8bda00a5c1b8e5b935d6f536d3c92ddabb3',
 'artifacts/run_s12_fingerprint_remediation.py':'7585df92c2f349c2b41dde7b06a376cbedc7f6c8ab99a1c6f9c099c8cf3d28b3',
 'artifacts/s12_fingerprint_proof.py':'3c6d0820f618bbf4d1d5f540741180aa9a9205b0d6977e8f79bb74c24ae4fa3b',
 'artifacts/test_s12_fingerprint_proof.py':'bb1005e20834d354e9167856ead522ebc84241625308194424865abdd4fac651',
 'artifacts/run_s12_fingerprint_proof.py':'09e1b187e2cb69d3296a09199b84a929c5537b6f1646fd65d1ae917d78204daa'}
target=base/'S12-runtime-supervision-fingerprint-independent-review.json';assert not target.exists()
for ref,expected in files.items():assert hashlib.sha256((project/ref).read_bytes()).hexdigest()==expected
facts=dict(kind='INDEPENDENT_BOUNDED_READ_ONLY_FRESH_SOURCE_IDENTITY_AND_DIAGNOSTIC_PROOF_REVIEW',
 reviewer='/root/qualification_review',reviewer_execution='NONE',remaining_critical=0,remaining_important=0,
 reviewed_files={ref:'sha256:'+value for ref,value in files.items()},
 resolved_important=['Retained diagnostic PASS now requires owned reaping and unchanged full input/source/implementation bindings'],
 limits=['Read-only bounded review; not whole-branch/native/browser/production release approval',
        'Reviewer did not independently execute timing or regression tests'])
target.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Recorded exact independently reviewed9-file inventory')
