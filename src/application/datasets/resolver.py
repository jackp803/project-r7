from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from decimal import Decimal,localcontext
from types import MappingProxyType

from application.datasets.catalog import DatasetCatalog,DatasetError,canonical,digest,fail,read_local,utc,z,text
from indicators.v02.common import finite_decimal,canonical_decimal,REFERENCE_CONTEXT
from market_data.candle import Candle
from market_data.errors import MarketDataError
from market_data.historical import validate_historical_sequence
from market_data.timeframes import timeframe_duration,is_timeframe_aligned

def candle_schema():
    import pyarrow as pa
    return pa.schema([pa.field(name,kind,nullable=nullable) for name,kind,nullable in [
        ('schema_version',pa.string(),False),('symbol',pa.string(),False),('timeframe',pa.string(),False),
        ('open_time',pa.timestamp('ms',tz='UTC'),False),('close_time',pa.timestamp('ms',tz='UTC'),False),
        *[(key,pa.string(),False) for key in ('open','high','low','close','volume')],
        ('is_closed',pa.bool_(),False),('source',pa.string(),False),
        ('received_at',pa.timestamp('ms',tz='UTC'),True),('source_record_id',pa.string(),True)]])

def _parquet_rows(root,container,schema,*,through=None,clock=None,inclusive=True):
    import pyarrow as pa
    import pyarrow.parquet as pq
    raw=read_local(root,container['path'],64*1024*1024)
    if digest(raw)!=container['byte_hash']: fail('CONTAINER_HASH_MISMATCH')
    try:
        file=pq.ParquetFile(pa.BufferReader(raw),thrift_string_size_limit=65536,thrift_container_size_limit=65536)
        if not file.schema_arrow.equals(schema,check_metadata=False): fail('PARQUET_SCHEMA_MISMATCH')
        if file.metadata.num_rows!=container['rows'] or file.num_row_groups>1024: fail('PARQUET_ROW_LIMIT')
        for i in range(file.num_row_groups):
            group=file.metadata.row_group(i)
            if group.num_rows>8192 or group.total_byte_size>8*1024*1024: fail('PARQUET_ROW_GROUP_LIMIT')
        groups=None
        if through is not None:
            import pyarrow.compute as pc
            epoch=datetime(1970,1,1,tzinfo=timezone.utc); elapsed=through-epoch
            bound=elapsed.days*86400000+elapsed.seconds*1000+elapsed.microseconds//1000
            compare=pc.less_equal if inclusive else pc.less
            groups=[]
            for index in range(file.num_row_groups):
                # Inspect only clocks to choose groups. Sealed-only price/rate
                # columns are not loaded. A straddling group is filtered before
                # conversion into any Python financial values or E1 objects.
                times=file.read_row_group(index,columns=[clock],use_threads=False).column(clock).cast(pa.int64())
                if pc.any(compare(times,pa.scalar(bound,pa.int64()))).as_py(): groups.append(index)
        for batch in file.iter_batches(batch_size=8192,use_threads=False,row_groups=groups):
            if batch.nbytes>8*1024*1024: fail('PARQUET_DECODED_SIZE_LIMIT')
            if through is not None:
                batch=batch.filter(compare(batch.column(clock).cast(pa.int64()),pa.scalar(bound,pa.int64())))
            # The pinned schema permits UTC only. Decode epoch milliseconds
            # directly, independent of a host's optional IANA timezone database.
            timestamps=[]
            for i,field in enumerate(schema):
                if pa.types.is_timestamp(field.type):
                    timestamps.append(field.name)
                    batch=batch.set_column(i,pa.field(field.name,pa.int64(),nullable=field.nullable),batch.column(i).cast(pa.int64()))
            epoch=datetime(1970,1,1,tzinfo=timezone.utc)
            for row in batch.to_pylist():
                for name in timestamps:
                    if row[name] is not None: row[name]=epoch+timedelta(milliseconds=row[name])
                yield row
    except DatasetError: raise
    except (ValueError,TypeError,OSError): fail('INVALID_PARQUET')

@dataclass(frozen=True)
class RecordedFundingModel:
    events: tuple
    source_hash: str
    version: str='r7-recorded-funding-v0.2'
    def cost(self,position_side,quantity,entry_fill_price,opened_at,closed_at):
        if position_side not in ('LONG','SHORT'): fail('INVALID_FUNDING_SIDE')
        with localcontext(REFERENCE_CONTEXT):
            rate=sum((rate for event,rate in self.events if opened_at<=event<closed_at),Decimal(0))
            raw=quantity*entry_fill_price*rate
            return raw if position_side=='LONG' else -raw
    def assumptions(self):
        return dict(version=self.version,source_hash=self.source_hash,mode='RECORDED_RATES',
                    notional_basis='ENTRY_FILL_PRICE_X_BASE_QUANTITY',notional_method='REPLAY_ESTIMATE',
                    event_window='OPENED_AT_INCLUSIVE_CLOSED_AT_EXCLUSIVE',event_count=len(self.events))

@dataclass(frozen=True)
class ResolvedDataset:
    dataset_id: str
    dataset_version: str
    manifest_hash: str
    logical_hash: str
    namespace: str
    symbol: str
    availability_model: str
    information_cutoff: object
    candles_by_timeframe: object
    container_hashes: tuple
    funding_model: RecordedFundingModel | None
    promotion_data_ready: bool
    reason_codes: tuple
    manifest_json: str
    verification_scope: str='FULL_LOGICAL_VERIFIED'
    @property
    def start(self): return max(rows[0].open_time for rows in self.candles_by_timeframe.values())
    @property
    def end(self): return min(rows[-1].close_time for rows in self.candles_by_timeframe.values())

class DatasetResolver:
    def __init__(self,catalog):
        if not isinstance(catalog,DatasetCatalog): raise TypeError('DatasetCatalog required')
        self.catalog=catalog
    def resolve(self,relative):
        return self._resolve(relative)
    def resolve_development(self,relative,through):
        if not isinstance(through,datetime) or through.utcoffset()!=timedelta(0): fail('INVALID_DEVELOPMENT_CUTOFF')
        return self._resolve(relative,through=through)
    def _resolve(self,relative,*,through=None):
        manifest=self.catalog.load(relative); spec=manifest.as_dict(); selected={}; hashes=[]; logical=[]
        cutoff=utc(spec['information_cutoff'])
        for container in spec['candles']:
            end=utc(container['end']) if through is None else through
            if end>utc(container['end']) or end<=utc(container['start']) or not is_timeframe_aligned(end,container['timeframe']): fail('INVALID_DEVELOPMENT_CUTOFF')
            rows=[]; materials=[]
            for record in _parquet_rows(self.catalog.root,container,candle_schema(),through=through,clock='close_time'):
                try:
                    for key in ('schema_version','symbol','timeframe','source'): text(record[key])
                    if record['source_record_id'] is not None: text(record['source_record_id'])
                    for key in ('open','high','low','close','volume'): record[key]=finite_decimal(record[key])
                    if any(record[key]<=0 for key in ('open','high','low','close')): fail('NONPOSITIVE_PRICE')
                    bar=Candle(**record)
                    if spec['availability_model']=='recorded_received_at' and bar.received_at is None: fail('MISSING_AVAILABILITY_EVIDENCE')
                    available=bar.received_at or bar.close_time
                    if available<bar.close_time or available>cutoff or bar.close_time>cutoff: fail('DATA_OUTSIDE_INFORMATION_CUTOFF')
                except DatasetError: raise
                except (ValueError,TypeError,AttributeError,MarketDataError): fail('INVALID_CANONICAL_CANDLE')
                material=dict(record)
                for key in ('open','high','low','close','volume'): material[key]=canonical_decimal(str(material[key]))
                for key in ('open_time','close_time','received_at'):
                    if material[key] is not None: material[key]=z(material[key])
                rows.append(bar); materials.append(material)
            try:
                rows=validate_historical_sequence(rows,symbol=spec['symbol'],timeframe=container['timeframe'],start=utc(container['start']),end=end)
            except MarketDataError: fail('INVALID_E1_SEQUENCE')
            expected_rows=container['rows'] if through is None else (end-utc(container['start']))//timeframe_duration(container['timeframe'])
            if len(rows)!=expected_rows: fail('ROW_COUNT_MISMATCH')
            logical_hash=digest(canonical(materials).encode())
            if through is None and logical_hash!=container['logical_hash']: fail('LOGICAL_HASH_MISMATCH')
            selected[container['timeframe']]=rows
            hashes.append((container['path'],container['byte_hash'])); logical.append((container['timeframe'],logical_hash))
        funding=spec['funding']; model=None; reasons=[]
        if funding['mode']=='MISSING': reasons.append('MISSING_FUNDING')
        else:
            import pyarrow as pa
            schema=pa.schema([pa.field('event_at',pa.timestamp('ms',tz='UTC'),False),pa.field('rate',pa.string(),False),pa.field('source',pa.string(),False)])
            events=[]; material=[]; start,end=utc(funding['start']),utc(funding['end']); expected=start
            if through is not None: end=min(end,through)
            if start>min(rows[0].open_time for rows in selected.values()) or end<max(rows[-1].close_time for rows in selected.values()): fail('MISSING_FUNDING_COVERAGE')
            for item in _parquet_rows(self.catalog.root,funding,schema,through=through,clock='event_at',inclusive=False):
                text(item['source'])
                try: rate=finite_decimal(item['rate'])
                except ValueError: fail('INVALID_FUNDING_RATE')
                if abs(rate)>=1 or item['event_at']!=expected or item['event_at']>=end or item['event_at']>cutoff: fail('INVALID_FUNDING_SEQUENCE')
                events.append((item['event_at'],rate)); material.append(dict(event_at=z(item['event_at']),rate=canonical_decimal(str(rate)),source=item['source']))
                expected+=timedelta(seconds=funding['interval_seconds'])
            if expected<end: fail('MISSING_FUNDING_COVERAGE')
            funding_hash=digest(canonical(material).encode())
            if through is None and funding_hash!=funding['logical_hash']: fail('LOGICAL_HASH_MISMATCH')
            model=RecordedFundingModel(tuple(events),funding_hash)
            hashes.append((funding['path'],funding['byte_hash'])); logical.append(('funding',funding_hash))
        return ResolvedDataset(spec['dataset_id'],spec['dataset_version'],manifest.manifest_hash,
                               digest(canonical(sorted(logical)).encode()),spec['namespace'],spec['symbol'],
                               spec['availability_model'],cutoff,MappingProxyType(selected),tuple(hashes),model,
                               not reasons and through is None,tuple(reasons),manifest.canonical_json,
                               'FULL_LOGICAL_VERIFIED' if through is None else 'DEVELOPMENT_VERIFIED_SEALED_LOGICAL_PENDING')
