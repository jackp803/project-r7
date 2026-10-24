"""Bounded RAM-only allocation attribution; source/measured files stay readonly.

DROP/rebuild probes occur ONLY in an ephemeral in-memory copy of the explicitly
non-authoritative prototype, never in source/product/measured files. No new format.
"""
from pathlib import Path
import hashlib,json,sqlite3,time
from compact_fact_prototype import HOT,quote
from tools.verify_public_archive_volume import peak_memory

art=Path(__file__).parent;source=art/'compact-facts-prototype-D-v2-20261024/non-authoritative-format.sqlite'
output=art/'compact-facts-prototype-decomposition-20261024'
if output.exists():raise RuntimeError('Fresh output required')
output.mkdir();before=hashlib.sha256(source.read_bytes()).hexdigest();started=time.perf_counter()
original=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);original.execute('PRAGMA query_only=ON');db=sqlite3.connect(':memory:');original.backup(db)
models={json.loads(row[0])['physical']:json.loads(row[0]) for row in db.execute('SELECT description FROM model')}
page_size=db.execute('PRAGMA page_size').fetchone()[0]
def used():return (db.execute('PRAGMA page_count').fetchone()[0]-db.execute('PRAGMA freelist_count').fetchone()[0])*page_size
def allocations():
    result=[]
    for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        amount=used();db.execute('SAVEPOINT attribution');db.execute('DROP TABLE '+quote(name));freed=amount-used()
        db.execute('ROLLBACK TO attribution');db.execute('RELEASE attribution')
        result.append(dict(physical_table=name,logical_table=models.get(name,{}).get('name',name),bytes_including_all_owned_indices=freed))
    return result
try:
    if db.execute('PRAGMA auto_vacuum').fetchone()[0]!=0:raise RuntimeError('No automatic page compaction in attribution')
    before_used=used();parts_before=allocations();removed=0
    for number,(name,model) in enumerate(models.items()):
        sql=db.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0]
        marker='_source_ordinal INTEGER NOT NULL UNIQUE'
        if sql.count(marker)!=1:raise RuntimeError('Only experiment ordinal UNIQUE may be removed')
        indices=[row[0] for row in db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",(name,))]
        shadow='scratch_'+str(number);create='CREATE TABLE '+shadow+sql[sql.index('('):].replace(marker,'_source_ordinal INTEGER NOT NULL')
        count=db.execute('SELECT count(*) FROM '+name).fetchone()[0]
        db.execute(create);db.execute('INSERT INTO '+shadow+' SELECT * FROM '+name)
        db.execute('DROP TABLE '+name);db.execute('ALTER TABLE '+shadow+' RENAME TO '+name)
        for index_sql in indices:db.execute(index_sql)
        if db.execute('SELECT count(*) FROM '+name).fetchone()[0]!=count:raise RuntimeError('RAM attribution lost a row')
        removed+=1
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('RAM-only attribution integrity failed')
    after_used=used();parts_after=allocations()
    growing=sum(row['bytes_including_all_owned_indices'] for row in parts_after if row['logical_table'] in HOT or row['physical_table'] in ('atoms','blobs'))
    static=after_used-growing
    rows=28872;ordinal_column_best_credit=rows*9
    # Extremely favorable credit: remove ALL experiment ordinal bytes from the
    # growing component, even though some belong to static tables. Not a PASS.
    optimistic_journal=max(0,growing-ordinal_column_best_credit)*720+static
    value=dict(status='RAM_ONLY_EXPERIMENT_OVERHEAD_ATTRIBUTION_NOT_NEW_FORMAT_OR30DAY_PASS',
        measured_prototype_sha256='sha256:'+before,measured_file_bytes=source.stat().st_size,
        actual_used_bytes_before=before_used,actual_used_bytes_without_experiment_ordinal_unique=after_used,
        measured_experiment_unique_index_savings=before_used-after_used,experiment_indices_removed_in_ram=removed,
        allocations_before=parts_before,allocations_after=parts_after,growing_component_bytes=growing,static_component_bytes=static,
        generous_ordinal_column_credit=ordinal_column_best_credit,optimistic_projected_journal_bytes=optimistic_journal,
        measured_public_archive_bytes=3622328474,allowed_total_public_archive_bytes=8*1024**3,
        optimistic_journal_plus_measured_archive_bytes=optimistic_journal+3622328474,
        optimistic_journal_plus_allowed_archive_bytes=optimistic_journal+8*1024**3,
        complete_backup_bound_bytes=16*1024**3,source_writes=0,measured_prototype_writes=0,
        note='Exact RAM Btree/index attribution; linear sample assumptions remain, not actual30day volume; no original rows deleted or product limits changed',
        wall_seconds=time.perf_counter()-started,**peak_memory())
    if before!=hashlib.sha256(source.read_bytes()).hexdigest():raise RuntimeError('Measured prototype changed')
    (output/'result.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in value.items() if not k.startswith('allocations')}),flush=True)
finally:db.close();original.close()
