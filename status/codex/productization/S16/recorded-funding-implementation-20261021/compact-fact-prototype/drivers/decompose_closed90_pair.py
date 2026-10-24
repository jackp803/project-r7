"""Allocation-only RAM copies; original and measured prototype files readonly."""
from pathlib import Path
import hashlib,json,sqlite3,time
from compact_fact_prototype import quote
from tools.verify_public_archive_volume import peak_memory

art=Path(__file__).parent
output=art/'compact-closed90-pair-decomposition-20261024'
if output.exists():raise RuntimeError('Fresh output required')
output.mkdir();started=time.perf_counter();samples=[]
for label in ('before','after'):
    folder=art/f'compact-facts-D-closed90-{label}-20261024'
    path=folder/'non-authoritative-format.sqlite';before=hashlib.sha256(path.read_bytes()).hexdigest()
    result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    original=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);original.execute('PRAGMA query_only=ON')
    db=sqlite3.connect(':memory:');original.backup(db)
    try:
        models={json.loads(row[0])['physical']:json.loads(row[0]) for row in db.execute('SELECT description FROM model')}
        page_size=db.execute('PRAGMA page_size').fetchone()[0]
        def used():return (db.execute('PRAGMA page_count').fetchone()[0]-db.execute('PRAGMA freelist_count').fetchone()[0])*page_size
        initial=used()
        for number,(name,model) in enumerate(models.items()):
            sql=db.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0]
            marker='_source_ordinal INTEGER NOT NULL UNIQUE'
            if sql.count(marker)!=1:raise RuntimeError('Only experiment ordinal UNIQUE may be removed')
            indices=[row[0] for row in db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",(name,))]
            shadow='scratch_'+str(number)
            db.execute('CREATE TABLE '+shadow+sql[sql.index('('):].replace(marker,'_source_ordinal INTEGER NOT NULL'))
            count=db.execute('SELECT count(*) FROM '+name).fetchone()[0]
            db.execute('INSERT INTO '+shadow+' SELECT * FROM '+name)
            db.execute('DROP TABLE '+name);db.execute('ALTER TABLE '+shadow+' RENAME TO '+name)
            for index_sql in indices:db.execute(index_sql)
            if db.execute('SELECT count(*) FROM '+name).fetchone()[0]!=count:raise RuntimeError('Row loss in RAM')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('RAM integrity')
        samples.append(dict(label=label,source_sha256=result['source_sha256'],prototype_sha256='sha256:'+before,
            source_rows=result['source_rows'],measured_bytes=result['actual_sqlite_bytes'],used_bytes_before=initial,
            used_bytes_without_experiment_unique=used(),experiment_indices_removed_in_ram=len(models)))
    finally:db.close();original.close()
    if hashlib.sha256(path.read_bytes()).hexdigest()!=before:raise RuntimeError('Readonly prototype changed')
first,last=samples;increment=last['used_bytes_without_experiment_unique']-first['used_bytes_without_experiment_unique']
credit=(last['source_rows']-first['source_rows'])*9
value=dict(status='PAIRED_MATURE_HISTORY_RAM_ONLY_ATTRIBUTION_NOT30DAY_PASS',samples=samples,
    controlled_operations=154,measured_used_increment_without_experiment_unique=increment,
    generous_ordinal_column_increment_credit=credit,
    optimistic_fixed_mature_state_linear_journal_increment_30day=(increment-credit)*3110400/154,
    measured_archive_bytes=3622328474,complete_backup_limit_bytes=16*1024**3,
    omitted='Original initial/static data, later trade growth, additional timeframe and backup overhead; not actual30day generation',
    source_writes=0,measured_prototype_writes=0,actual_provider_requests=0,native='NOT_QUALIFIED',
    wall_seconds=time.perf_counter()-started,**peak_memory())
value['optimistic_linear_increment_plus_measured_archive_bytes']=value['optimistic_fixed_mature_state_linear_journal_increment_30day']+value['measured_archive_bytes']
(output/'result.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(value),flush=True)
