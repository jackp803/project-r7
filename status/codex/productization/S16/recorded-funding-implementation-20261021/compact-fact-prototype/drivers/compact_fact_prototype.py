"""FINITE NON-AUTHORITATIVE FORMAT EXPERIMENT. Never a product DB or PASS port.

Reads an actual source snapshot readonly; copies every original cell/index into
experimental formats, verifies exact readback. No product source/schema changes.
"""
from collections import OrderedDict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import argparse,base64,ctypes,hashlib,json,re,sqlite3,struct,time,zlib

MAX_PAYLOAD=16*1024**2
MAX_ROWS=30000
MAX_REFS=64
MAX_DEPTH=127
MAX_CACHE_BYTES=64*1024**2
HOT=frozenset(('paper_process_effects','paper_process_checkpoints','paper_process_operations','paper_process_publications',
    'paper_process_published_prefixes','paper_position_lifecycle_projections','paper_position_lifecycle_execution_bindings'))
_HEX=re.compile(r'(.{0,64}?)([0-9a-f]{64})\Z',re.DOTALL)
_CLOCK=re.compile(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,6}))?(Z|\+00:00)\Z')
_EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)

def fail():raise ValueError('FINITE_COMPACT_PROTOTYPE_INVALID')
def sha(raw):return hashlib.sha256(raw).digest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def quote(value):return '"'+value.replace('"','""')+'"'
def uvar(value):
    if type(value) is not int or value<0:fail()
    raw=bytearray()
    while value>=128:raw.append((value&127)|128);value>>=7
    raw.append(value);return bytes(raw)
def readvar(raw,at):
    start=at;value=shift=0
    for _ in range(10):
        if at>=len(raw):fail()
        byte=raw[at];at+=1;value|=(byte&127)<<shift
        if byte<128:
            if raw[start:at]!=uvar(value):fail()
            return value,at
        shift+=7
    fail()
def inflate(raw,maximum):
    decoder=zlib.decompressobj()
    try:value=decoder.decompress(raw,maximum+1)
    except zlib.error:fail()
    if len(value)>maximum or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:fail()
    return value
def smaller(raw):
    compressed=zlib.compress(raw)
    return (1,compressed) if len(compressed)<len(raw) else (0,raw)
def prefix(a,b):
    low=0;high=min(len(a),len(b))
    while low<high:
        mid=(low+high+1)//2
        if a[:mid]==b[:mid]:low=mid
        else:high=mid-1
    return low


class PrototypeStore:
    def __init__(self,db,candidate):
        if candidate not in ('B','C','D'):fail()
        self.db=db;self.candidate=candidate;self.atoms=OrderedDict();self.cache=OrderedDict();self.cache_bytes=0;self.previous={}
        db.executescript('''
          CREATE TABLE atoms(id INTEGER PRIMARY KEY,encoded BLOB NOT NULL,lexical BLOB NOT NULL UNIQUE);
          CREATE TABLE blobs(id INTEGER PRIMARY KEY,kind INTEGER NOT NULL,identity INTEGER NOT NULL,lineage INTEGER NOT NULL,
            raw_hash BLOB NOT NULL,raw_size INTEGER NOT NULL,mode INTEGER NOT NULL,depth INTEGER NOT NULL,
            previous INTEGER,data BLOB NOT NULL,UNIQUE(kind,identity,lineage,raw_hash));
          CREATE TABLE model(table_name TEXT PRIMARY KEY,description BLOB NOT NULL);
        ''')
        if candidate=='D':
            db.execute('DROP TABLE atoms');db.execute('CREATE TABLE atoms(id INTEGER PRIMARY KEY,encoded BLOB NOT NULL UNIQUE)')

    @staticmethod
    def _encoded(text):
        raw=text.encode('utf-8');encoded=b'S'+raw;match=_HEX.fullmatch(text)
        if match:return b'H'+uvar(len(match[1].encode()))+match[1].encode()+bytes.fromhex(match[2])
        clock=_CLOCK.fullmatch(text)
        if clock:
            try:
                at=datetime.fromisoformat(text.replace('Z','+00:00'));elapsed=at-_EPOCH
                micros=elapsed.days*86400000000+elapsed.seconds*1000000+elapsed.microseconds
                encoded=b'D'+bytes((len(clock[2] or ''),int(clock[3]=='Z')))+struct.pack('>q',micros)
            except (ValueError,OverflowError):pass
        return encoded

    def atom(self,text):
        if type(text) is not str:fail()
        raw=text.encode('utf-8');cached=self.atoms.get(raw)
        if cached is not None:self.atoms.move_to_end(raw);return cached
        encoded=self._encoded(text)
        row=self.db.execute('SELECT id FROM atoms WHERE '+('encoded' if self.candidate=='D' else 'lexical')+'=?',
            (encoded if self.candidate=='D' else raw,)).fetchone()
        if row is None:
            if self.candidate=='D':reference=self.db.execute('INSERT INTO atoms(encoded) VALUES(?)',(encoded,)).lastrowid
            else:reference=self.db.execute('INSERT INTO atoms(encoded,lexical) VALUES(?,?)',(encoded,raw)).lastrowid
            row=(reference,)
        self.atoms[raw]=row[0]
        while len(self.atoms)>8192:self.atoms.popitem(last=False)
        return row[0]

    def text(self,reference):
        row=self.db.execute('SELECT encoded'+('' if self.candidate=='D' else ',lexical')+' FROM atoms WHERE id=?',(reference,)).fetchone()
        if row is None:fail()
        raw=row[0];lexical=None if self.candidate=='D' else row[1]
        try:
            if raw[:1]==b'S':value=raw[1:].decode()
            elif raw[:1]==b'H':
                size,at=readvar(raw,1)
                if len(raw)!=at+size+32:fail()
                value=raw[at:at+size].decode()+raw[at+size:].hex()
            elif raw[:1]==b'D' and len(raw)==11:
                precision,zulu=raw[1],raw[2]
                if precision>6 or zulu not in (0,1):fail()
                at=_EPOCH+timedelta(microseconds=struct.unpack('>q',raw[3:])[0])
                value=f'{at.year:04d}-{at.month:02d}-{at.day:02d}T{at.hour:02d}:{at.minute:02d}:{at.second:02d}'
                if precision:value+='.'+f'{at.microsecond:06d}'[:precision]
                value+='Z' if zulu else '+00:00'
            else:fail()
        except (ValueError,UnicodeError,OverflowError):fail()
        if self._encoded(value)!=raw or lexical is not None and value.encode()!=lexical:fail()
        return value

    def clear_cache(self):self.cache.clear();self.cache_bytes=0
    def _remember(self,key,value):
        if len(value)>MAX_CACHE_BYTES:return
        if key in self.cache:self.cache_bytes-=len(self.cache.pop(key))
        self.cache[key]=value;self.cache_bytes+=len(value)
        while len(self.cache)>128 or self.cache_bytes>MAX_CACHE_BYTES:
            _,removed=self.cache.popitem(last=False);self.cache_bytes-=len(removed)

    def payload(self,raw,kind,identity,lineage=''):
        if type(raw) is not bytes or len(raw)>MAX_PAYLOAD:fail()
        keys=tuple(self.atom(value) for value in (kind,identity,lineage));digest=sha(raw)
        old=self.db.execute('SELECT id FROM blobs WHERE kind=? AND identity=? AND lineage=? AND raw_hash=?',(*keys,digest)).fetchone()
        if old:return old[0]
        mode,data=smaller(raw);depth=0;previous=None;family=(kind,lineage)
        if self.candidate!='B':
            if kind=='OUTCOME':
                template=self._template(raw)
                if template is not None and len(template)<len(data):mode,data=3,template
            elif kind=='STATE_ENVELOPE':
                packet=self._state_packet(raw)
                if packet is not None and len(packet)<len(data):mode,data=4,packet
            elif kind.startswith('CANON:') and family in self.previous:
                parent,base,parent_depth=self.previous[family]
                if parent_depth<MAX_DEPTH:
                    left=prefix(raw,base);right=prefix(raw[left:][::-1],base[left:][::-1]);middle=raw[left:len(raw)-right if right else len(raw)]
                    patch=uvar(left)+uvar(right)+middle;compressed=zlib.compress(patch)
                    # Includes predecessor/hash/depth column costs; no false win.
                    if len(compressed)+40<len(data):mode,data,previous,depth=2,compressed,parent,parent_depth+1
        ref=self.db.execute('INSERT INTO blobs(kind,identity,lineage,raw_hash,raw_size,mode,depth,previous,data) VALUES(?,?,?,?,?,?,?,?,?)',
            (*keys,digest,len(raw),mode,depth,previous,data)).lastrowid
        if self.candidate!='B' and kind.startswith('CANON:'):self.previous[family]=(ref,raw,depth)
        self._remember(ref,raw);return ref

    def _template(self,raw):
        try:value=json.loads(raw)
        except (ValueError,UnicodeError):return None
        if type(value) is not dict or canonical(value)!=raw or type(value.get('effects')) is not list or len(value['effects'])>MAX_REFS:return None
        output=bytearray(uvar(len(value['effects'])));cursor=0
        identities={'POSITION_PROJECTION':'lifecycle_projection_id','LIFECYCLE_EXECUTION_BINDING':'lifecycle_execution_binding_id',
            'RISK_DECISION':'risk_decision_id','APPROVED_TRADE_PLAN':'trade_plan_id','POSITION_ACTION':'position_action_id',
            'ORDER_REQUEST':'order_request_id','ORDER_RESULT':'order_request_id','FILL':'fill_id','FUNDING_EVIDENCE':'funding_evidence_id','TRADE_RESULT':'trade_result_id'}
        for item in value['effects']:
            if type(item) is not dict or set(item)!={'kind','payload'} or item['kind'] not in identities:return None
            payload=item['payload'];needle=canonical(payload);label=b'"payload":'+needle;at=raw.find(label,cursor)
            if at<cursor:return None
            at+=len(b'"payload":');literal=raw[cursor:at];kind='CANON:'+item['kind']
            identity=payload.get(identities[item['kind']]);lineage=payload.get('position_id') or payload.get('trade_plan_id') or ''
            if type(identity) is not str or type(lineage) is not str:return None
            ref=self.payload(needle,kind,identity,lineage)
            output+=uvar(len(literal))+literal+uvar(ref)
            for token in (kind,identity,lineage):output+=uvar(self.atom(token))
            output+=sha(needle);cursor=at+len(needle)
        tail=raw[cursor:];output+=uvar(len(tail))+tail
        return bytes(output)

    def _state_packet(self,raw):
        try:
            value=json.loads(raw)
            if canonical(value)!=raw or value['codec']!='r7-paper-state-zlib-delta-v0.1':return None
            data=base64.b64decode(value.pop('data'),validate=True)
            header=canonical({key:self.atom(item) if type(item) is str else item for key,item in value.items()})
            return uvar(len(header))+header+data
        except (ValueError,KeyError,TypeError):return None

    def raw(self,ref,*,expected=None,_stack=()):
        if type(ref) is not int or ref in _stack or len(_stack)>MAX_DEPTH+1:fail()
        row=self.db.execute('SELECT kind,identity,lineage,raw_hash,raw_size,mode,depth,previous,CASE WHEN length(data)<=? THEN data ELSE NULL END FROM blobs WHERE id=?',(MAX_PAYLOAD,ref)).fetchone()
        if row is None:fail()
        kind,identity,lineage,digest,size,mode,depth,previous,data=row
        names=tuple(self.text(token) for token in (kind,identity,lineage))
        if expected is not None and names!=expected:fail()
        if type(size) is not int or not 0<=size<=MAX_PAYLOAD or not 0<=depth<=MAX_DEPTH or data is None:fail()
        cached=self.cache.get(ref)
        if cached is not None:
            self.cache.move_to_end(ref)
            if len(cached)!=size or sha(cached)!=digest:fail()
            return cached
        if mode==0:value=data
        elif mode==1:value=inflate(data,size)
        elif mode==2:
            parent=self.db.execute('SELECT kind,lineage,depth FROM blobs WHERE id=?',(previous,)).fetchone()
            if parent!=(kind,lineage,depth-1) or not names[0].startswith('CANON:'):fail()
            base=self.raw(previous,_stack=(*_stack,ref));patch=inflate(data,MAX_PAYLOAD)
            left,at=readvar(patch,0);right,at=readvar(patch,at)
            if left+right>len(base) or left+right+len(patch)-at!=size:fail()
            value=base[:left]+patch[at:]+(base[len(base)-right:] if right else b'')
        elif mode==3:
            if names[0]!='OUTCOME' or depth or previous is not None:fail()
            count,at=readvar(data,0)
            if count>MAX_REFS:fail()
            parts=[];used=0
            for _ in range(count):
                length,at=readvar(data,at)
                if at+length>len(data) or used+length>size:fail()
                parts.append(data[at:at+length]);at+=length;used+=length
                child,at=readvar(data,at);tokens=[]
                for _ in range(3):token,at=readvar(data,at);tokens.append(self.text(token))
                if at+32>len(data):fail()
                wanted=data[at:at+32];at+=32
                if not tokens[0].startswith('CANON:'):fail()
                child_size=self.db.execute('SELECT raw_size FROM blobs WHERE id=?',(child,)).fetchone()
                if child_size is None or type(child_size[0]) is not int or not 0<=child_size[0]<=MAX_PAYLOAD or used+child_size[0]>size:fail()
                payload=self.raw(child,expected=tuple(tokens),_stack=(*_stack,ref))
                if sha(payload)!=wanted:fail()
                parts.append(payload);used+=len(payload)
            length,at=readvar(data,at)
            if at+length!=len(data) or used+length!=size:fail()
            parts.append(data[at:]);value=b''.join(parts)
        elif mode==4:
            if names[0]!='STATE_ENVELOPE' or depth or previous is not None:fail()
            length,at=readvar(data,0);header=json.loads(data[at:at+length]);at+=length
            strings={'codec','run_id','kind','payload_hash','base_hash'}
            for key in strings & set(header):header[key]=self.text(header[key])
            header['data']=base64.b64encode(data[at:]).decode();value=canonical(header)
        else:fail()
        if len(value)!=size or sha(value)!=digest:fail()
        self._remember(ref,value);return value


def run(source,output,candidate):
    from tools.verify_public_archive_volume import peak_memory
    from storage.paper_state_codec import decode_state
    if output.exists() or not source.is_file() or source.stat().st_size>128*1024**2:fail()
    from application.platform.private_files import create_private_directory
    create_private_directory(output);target=output/'non-authoritative-format.sqlite'
    before=sha(source.read_bytes());started=time.perf_counter();cpu=time.process_time();end=started+270
    source_db=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);source_db.execute('PRAGMA query_only=ON')
    db=sqlite3.connect(target);db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA synchronous=FULL')
    store=PrototypeStore(db,candidate);models=[];rows=0
    def deadline():
        if time.perf_counter()>=end:raise RuntimeError('FINITE_PROTOTYPE_DEADLINE_NO_SCOPE_EXPANSION')
    names=[r[0] for r in source_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    names.sort(key=lambda n:(n!='paper_process_effects',n))
    try:
        for number,name in enumerate(names):
            deadline();columns=list(source_db.execute('PRAGMA table_info('+quote(name)+')'));index_rows=list(source_db.execute('PRAGMA index_list('+quote(name)+')'))
            indexes=[]
            for index in index_rows:
                fields=[r[2] for r in source_db.execute('PRAGMA index_info('+quote(index[1])+')')]
                if any(field is None for field in fields) and (name!='product_dispatch_intents' or index[1]!='product_dispatch_account_claim_inventory'):fail()
                indexes.append(dict(unique=index[2],origin=index[3],partial=index[4],fields=fields))
            json_fields={r[1] for r in columns if name in HOT and r[2].upper()=='TEXT' and r[1].endswith('_json')}
            meta_fields={r[1] for r in columns if name in HOT and r[2].upper()=='TEXT' and r[1] not in json_fields}
            primary=[r[1] for r in sorted(columns,key=lambda r:r[5]) if r[5]]
            physical='c'+str(number);definitions=[quote(r[1])+(' INTEGER' if r[1] in meta_fields|json_fields else ' '+(r[2] or 'BLOB')) for r in columns]
            definitions.append('_source_ordinal INTEGER NOT NULL UNIQUE')
            lexical=candidate=='D' and name in ('paper_process_operations','paper_process_effects','paper_process_publications')
            if lexical:definitions.append('_operation_lexical TEXT NOT NULL')
            if primary:definitions.append('PRIMARY KEY('+','.join(map(quote,primary))+')')
            db.execute('CREATE TABLE '+physical+'('+','.join(definitions)+')'+(' WITHOUT ROWID' if primary and name in HOT else ''))
            for i,index in enumerate(indexes):
                if index['origin']=='pk':continue
                predicate=''
                if index['partial']:
                    sql=source_db.execute('SELECT sql FROM sqlite_master WHERE name=?',(index_rows[i][1],)).fetchone()[0]
                    if (name!='paper_runtime_objects' or index['fields']!=['client_order_id'] or
                            not re.search(r"WHERE\s+object_kind\s*=\s*'ORDER_REQUEST'\s+AND\s+client_order_id\s+IS\s+NOT\s+NULL\s*\Z",sql,re.I)):fail()
                    predicate=" WHERE object_kind='ORDER_REQUEST' AND client_order_id IS NOT NULL"
                expressions=[quote(field) if field is not None else "json_extract(request_json,'$.role')" for field in index['fields']]
                db.execute('CREATE '+('UNIQUE ' if index['unique'] else '')+'INDEX '+physical+'_i'+str(i)+' ON '+physical+'('+','.join(expressions)+')'+predicate)
            if lexical:
                middle='base_revision,' if name=='paper_process_operations' else 'checkpoint_revision,' if name=='paper_process_effects' else ''
                db.execute('CREATE INDEX '+physical+'_logical_lexical ON '+physical+'(run_id,'+middle+'_operation_lexical)')
            model=dict(name=name,physical=physical,columns=[r[1] for r in columns],json_fields=sorted(json_fields),meta_fields=sorted(meta_fields),indexes=indexes)
            db.execute('INSERT INTO model VALUES(?,?)',(name,canonical(model)));models.append(model)
            for ordinal,row in enumerate(source_db.execute('SELECT * FROM '+quote(name)),1):
                if rows>=MAX_ROWS:fail()
                values=dict(zip(model['columns'],row));encoded=[]
                for column,value in values.items():
                    if value is None:encoded.append(None)
                    elif column in meta_fields:encoded.append(store.atom(value))
                    elif column in json_fields:
                        kind=name+'.'+column;identity=str(ordinal);lineage=name
                        if candidate!='B':
                            if name=='paper_process_effects' and column=='outcome_json':kind,identity,lineage='OUTCOME',values['operation_id'],values['run_id']
                            elif name=='paper_process_checkpoints' and column=='state_json':kind,identity,lineage='STATE_ENVELOPE',str(values['revision']),values['run_id']
                            elif name in ('paper_position_lifecycle_projections','paper_position_lifecycle_execution_bindings') and column=='payload_json':
                                kind='CANON:'+('POSITION_PROJECTION' if name.endswith('projections') else 'LIFECYCLE_EXECUTION_BINDING')
                                identity=values['lifecycle_projection_id' if name.endswith('projections') else 'lifecycle_execution_binding_id'];lineage=values['position_id']
                        encoded.append(store.payload(value.encode(),kind,identity,lineage))
                    else:encoded.append(value)
                final=(*encoded,ordinal,values['operation_id']) if lexical else (*encoded,ordinal)
                db.execute('INSERT INTO '+physical+' VALUES('+','.join('?' for _ in final)+')',final);rows+=1
                if rows%128==0:deadline();db.commit()
            db.commit()
        build_wall=time.perf_counter()-started;build_cpu=time.process_time()-cpu;store.clear_cache();verified=0;read_started=time.perf_counter();read_cpu=time.process_time()
        for model in models:
            original=source_db.execute('SELECT * FROM '+quote(model['name']))
            for row in db.execute('SELECT '+','.join(map(quote,model['columns']))+' FROM '+model['physical']+' ORDER BY _source_ordinal'):
                actual=[]
                for column,value in zip(model['columns'],row):
                    actual.append(None if value is None else store.text(value) if column in model['meta_fields'] else store.raw(value).decode() if column in model['json_fields'] else value)
                expected=original.fetchone()
                if tuple(actual)!=expected or tuple(map(type,actual))!=tuple(map(type,expected)):raise RuntimeError('EXACT_ORIGINAL_CELL_MISMATCH:'+model['name'])
                verified+=1
                if verified%128==0:deadline()
            if original.fetchone() is not None:fail()
        verify_wall=time.perf_counter()-read_started;verify_cpu=time.process_time()-read_cpu
        checkpoint=next(m for m in models if m['name']=='paper_process_checkpoints');tip=source_db.execute('SELECT run_id,max(revision),state_hash FROM paper_process_checkpoints').fetchone()
        run_id,revision=tip[:2];run=store.atom(run_id)
        def physical(at):
            row=db.execute('SELECT state_json,state_hash FROM '+checkpoint['physical']+' WHERE run_id=? AND revision=?',(run,at)).fetchone()
            if row is None:fail()
            return store.raw(row[0]).decode(),store.text(row[1])
        store.clear_cache();began=time.perf_counter();encoded,expected=physical(revision)
        logical=decode_state(encoded,run_id=run_id,revision=revision,expected_hash=expected,read_previous=physical)
        cold=time.perf_counter()-began
        if 'sha256:'+sha(logical.encode()).hex()!=expected:fail()
        db.commit();pages=db.execute('PRAGMA page_count').fetchone()[0];page_size=db.execute('PRAGMA page_size').fetchone()[0]
        result=dict(status='EXACT_ALL_ROWS_FINITE_FORMAT_PROTOTYPE_ONLY_NOT_PRODUCTION_OR30DAY_PASS',candidate=candidate,
            source_sha256='sha256:'+before.hex(),source_bytes=source.stat().st_size,source_tables=len(models),source_rows=rows,verified_rows=verified,
            actual_sqlite_bytes=pages*page_size,build_wall_seconds=build_wall,build_cpu_seconds=build_cpu,
            exact_readback_wall_seconds=verify_wall,exact_readback_cpu_seconds=verify_cpu,decoded_cache_empty_warm_sqlite_checkpoint_decode_seconds=cold,
            current_revision=revision,current_semantic_hash=expected,atoms=db.execute('SELECT count(*) FROM atoms').fetchone()[0],
            byte_objects=db.execute('SELECT count(*) FROM blobs').fetchone()[0],modes=db.execute('SELECT mode,count(*),sum(length(data)) FROM blobs GROUP BY mode').fetchall(),
            source_index_count=sum(len(m['indexes']) for m in models),conservative_partial_indexes=sum(i['partial'] for m in models for i in m['indexes']),
            complexity='TYPED_METADATA_AND_INDEPENDENT_BINARY_BLOBS' if candidate=='B' else 'TYPED_METADATA_SHARED_DATA_ONLY_REFS_BOUNDED_DELTAS_OUTCOME_TEMPLATE_EXISTING_INNER_STATE_CODEC',
            actual_provider_requests=0,authority='NONE_NONAUTHORITATIVE_FORMAT_EXPERIMENT',elapsed_credit='NONE',native='NOT_QUALIFIED',
            timing_scope='BULK_CLONE_AND_CODEC_READ_ONLY_NOT_ACTUAL_OWNER_WRITE_OR_PROTECTION_LATENCY',**peak_memory())
        if sha(source.read_bytes())!=before:raise RuntimeError('SOURCE_CHANGED')
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result),flush=True)
    finally:db.close();source_db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--candidate',choices=('B','C','D'),required=True);args=parser.parse_args()
    try:
        if not ctypes.windll.kernel32.SetThreadExecutionState(0x80000001):raise ctypes.WinError()
        run(args.source.absolute(),args.output.absolute(),args.candidate)
    finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
