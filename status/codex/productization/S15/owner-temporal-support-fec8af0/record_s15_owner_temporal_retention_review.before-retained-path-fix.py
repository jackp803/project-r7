"""Record the observed independent pre-execution retention review."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
expected={
 'retain_s15_owner_temporal_support.py':'171316c761eba145e90abc007f384f9b9047e8b9748a39c57d0726d4731cd853',
 's14_feedback_cli_acceptance_core.py':'a3bd7e32bb805cebfdb5a26994cd712bc47b1bb995dae0c51dd7a09522a9c7b0',
 'S15-owner-temporal-semantic-review.json':'b89216f4092aa11ab93c397b077ebbf1abc6a2539c600c4ed7365a7df9d63a88'}
for name,value in expected.items():assert hashlib.sha256(read_local(base,name,1024*1024)).hexdigest()==value
receipt=dict(kind='INDEPENDENT_BOUNDED_READ_ONLY_PRE_EXECUTION_RETENTION_REVIEW',
    reviewer='/root/qualification_review',reviewer_execution='NONE',remaining_critical=0,remaining_important=0,remaining_minor=0,
    reviewed_original_artifacts={'artifacts/'+name:'sha256:'+value for name,value in expected.items() if name.endswith('.py')},
    semantic_review_sha256='sha256:'+expected['S15-owner-temporal-semantic-review.json'],
    tests_executed='NONE;NO_NEW_RETENTION_REGRESSION_CLAIM',
    limits='EVIDENCE_RETENTION_TOOL_REVIEW_ONLY;NO_REQUIREMENT_PLATFORM_FINANCIAL_OR_MASTER_ACCEPTANCE',
    recorded_at_utc=datetime.now(timezone.utc).isoformat())
target=base/'S15-owner-temporal-retention-review.json';assert not target.exists()
target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(review='0C_0I_0M',review_sha256='sha256:'+hashlib.sha256(target.read_bytes()).hexdigest())))
