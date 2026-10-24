"""Read-only measured growth and explicit size estimates, no PASS authority."""
from pathlib import Path
import hashlib,json,sqlite3,zlib
art=Path(__file__).parent;source=art/'e6-3600second-growth-v2-20261024'
value=json.loads((source/'result.json').read_text());first,last=value['samples'][0],value['samples'][-1]
count=value['measured_operations'];target=value['projection_operations_30day'];rows=[]
for name,end in last['inventories'].items():
    start=first['inventories'].get(name,dict(rows=0,text_bytes=0))
    growth=end['text_bytes']-start['text_bytes']
    if growth:rows.append(dict(table=name,measured_rows=end['rows']-start['rows'],measured_text_growth_bytes=growth,projected30day_text_growth_bytes=growth*target//count))
rows.sort(key=lambda r:r['measured_text_growth_bytes'],reverse=True)
p=source/'controlled-source-snapshot.sqlite';before='sha256:'+hashlib.sha256(p.read_bytes()).hexdigest();compression=[]
with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
    for table,column in (('paper_process_effects','outcome_json'),('paper_position_lifecycle_projections','payload_json'),('paper_position_lifecycle_execution_bindings','payload_json')):
        plain=compressed=base64_bytes=records=0
        for raw, in db.execute('SELECT '+column+' FROM '+table):
            payload=raw.encode();size=len(zlib.compress(payload));plain+=len(payload);compressed+=size
            base64_bytes+=(size+2)//3*4;records+=1
        compression.append(dict(table=table,rows=records,actual_plain_bytes=plain,hypothetical_zlib_bytes=compressed,
            hypothetical_base64_bytes=base64_bytes,disclosure='COUNTERFACTUAL_BYTE_SIZES_ONLY_NO_ROW_CHANGED;EXCLUDES_ENVELOPES_INDEXES_PAGE_PACKING'))
if before!='sha256:'+hashlib.sha256(p.read_bytes()).hexdigest():raise RuntimeError('Readonly analysis changed source')
result=dict(status='MEASURED_GROWTH_PROJECTION_EXCEEDS_EXISTING_BOUND_NOT30DAY_ACCEPTANCE',actual_operations=count,
    actual_controlled_seconds=3600,actual_wall_seconds=value['wall_seconds'],actual_sqlite_bytes=last['sqlite_allocated_bytes'],
    measured_sqlite_growth_bytes=last['sqlite_allocated_bytes']-first['sqlite_allocated_bytes'],
    declared30day_operations=target,projected_sqlite_growth_bytes=value['projected30day_sqlite_growth_bytes'],
    prior_actual30day_archive_bytes=3622328474,existing_whole_product_backup_bound_bytes=16*1024**3,
    projected_sqlite_plus_prior_archive_bytes=value['projected30day_sqlite_growth_bytes']+3622328474,
    projected_component_text_growth=rows,counterfactual_compression=compression,
    source_snapshot_sha256=before,source_writes=0,projection='SAMPLE_PER_OPERATION_ONLY;NO_ACTUAL30DAY_GENERATION_OR_CAPACITY_PASS',
    financial_semantics='UNCHANGED',private_requests=0,provider_requests=0,elapsed_credit='NONE')
(source/'growth-analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result),flush=True)
