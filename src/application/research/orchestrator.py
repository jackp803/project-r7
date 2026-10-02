from application.datasets.catalog import canonical,digest
from application.research.evidence import now_utc

class ResearchOrchestrator:
    """Resume immutable stages; completed results are never overwritten."""
    def __init__(self,journal,owner_id): self.journal=journal; self.owner_id=owner_id
    def execute(self,run_id,stage,inputs,operation):
        input_hash=digest(canonical(inputs).encode())
        cached=self.journal.result(run_id,stage)
        if cached is not None:
            completed=[row for row in self.journal.attempts(run_id) if row['stage']==stage and row['status']=='COMPLETE'][-1]
            if completed['input_hash']!=input_hash:
                from application.research.evidence import ResearchEvidenceConflict
                raise ResearchEvidenceConflict('Cached stage has different inputs')
            return cached
        claim=self.journal.claim(run_id,stage,input_hash,self.owner_id,now_utc(),lease_seconds=300)
        try: result=operation(claim)
        except Exception as error:
            # A bounded reason, never exception text containing local paths/input.
            reason=getattr(error,'code',type(error).__name__)
            import re
            if not isinstance(reason,str) or not re.fullmatch('[A-Za-z_]{1,64}',reason): reason=type(error).__name__
            self.journal.finish(claim,{'reason_codes':[reason]},now_utc(),status='FAILED',reason_codes=(reason,))
            raise
        self.journal.finish(claim,result,now_utc())
        return result
