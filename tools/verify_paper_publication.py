"""Native owner publications over an actual, strictly local FIXTURE copy peer.

The product owns every report, outbox transition and verified copy ACK. This
driver only exercises public commands and reads exact existing local evidence.
Real cloud, provider requests and financial authority are never commissioned.
"""
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from verify_paper_product import PublicFixture, ROOT, sha
from application.cloud.manifest import canonical_bytes, load_json, safe_relative
from application.cloud.public_feedback import validate_public_feedback_publication
from application.cloud.rclone_bridge import _private_key, _private_text
from application.cloud.safe_files import read_bounded
from application.datasets.catalog import decode,hash_value
from application.fixtures.recipe import ROOT_ID
from application.platform.private_files import create_private_directory, require_private, write_private_new
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.supervision import _local_path
from application.platform.distribution import _inventory
from application.qualification import _sanitize

MAX_PUBLICATIONS = 32
MAX_REPORT = 256 * 1024
MAX_PAYLOADS = 1024 * 1024
ACK_SCOPE = 'LOCAL_FIXTURE_VERIFIED_COPY_ACK'


def helper_inventory(root):
    """Bind the entire emitted onedir runtime, never just its launcher."""
    root=Path(root)
    if (root/'distribution.json').exists():raise ValueError('Unexpected helper manifest')
    result=_inventory(root)
    if not result or any((root/ref).stat().st_nlink!=1 for ref in result):
        raise ValueError('Single-link complete native helper inventory required')
    return result


@contextmanager
def readonly_store(path):
    """No migration, namespace binder, replacement database or writable handle."""
    path = Path(path).absolute()
    _local_path(path)
    require_private(path)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        try:
            yield db
        finally:
            db.rollback()


def _public_content(value):
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if any(_private_key(key) for key in item):
                raise ValueError('Native publication contains private fields')
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, str) and _private_text(item):
            raise ValueError('Native publication contains private text')


def validate_report_row(row, kind, *, forbidden=()):
    """Pure verification of the same immutable bundle the actual owner retained."""
    if kind not in ('paper', 'research'):
        raise ValueError('Named owner feedback required')
    raw, encoded = row['feedback_json'].encode('utf-8'), row['payloads_json'].encode('utf-8')
    if len(raw) > MAX_REPORT or len(encoded) > MAX_PAYLOADS or sha(raw) != row['feedback_hash']:
        raise ValueError('Native stored feedback hash differs')
    text_payloads = decode(encoded)
    if not isinstance(text_payloads, dict) or any(not isinstance(value, str) for value in text_payloads.values()):
        raise ValueError('Native bounded feedback payloads required')
    payloads = {name:value.encode('utf-8') for name,value in text_payloads.items()}
    validate_public_feedback_publication(row['logical_path'], payloads)
    artifact = sha(canonical_bytes({name:sha(value) for name,value in payloads.items()}))
    prefix = 'r7-paper-feedback-' if kind == 'paper' else 'r7-feedback-'
    if (payloads['feedback.json'] != raw or artifact != row['artifact_hash']
            or row['operation_id'] != prefix + row['feedback_hash'][7:]):
        raise ValueError('Native stored feedback artifact differs')
    document = load_json(raw, MAX_REPORT)
    _public_content(document)
    if any(text and text.encode('utf-8') in value for text in forbidden for value in payloads.values()):
        raise ValueError('Native report disclosed private fixture input')
    if (document['namespace'] != 'FIXTURE' or document['run_id'] != row['run_id']
            or document['performance_policy'] != 'OPT_OUT' or document['live'] != {'status':'NOT_RUN','performance':None}):
        raise ValueError('Native owner disclosure policy differs')
    if kind == 'paper':
        observation = document['observation']
        if (observation['mode'] != 'ACCELERATED_FIXTURE' or observation['execution'] != 'SIMULATED_MECHANICS'
                or observation['actual_elapsed_seconds'] != 0 or observation['actual_healthy_seconds'] != 0
                or document['performance'] is not None or document['assessment']['status'] != 'BLOCKED'
                or document['financial_authority'] != 'NONE'):
            raise ValueError('Accelerated owner evidence cannot establish real forward qualification')
    elif any(document[stage]['performance'] is not None for stage in ('training','development','robustness','sealed_oos')):
        raise ValueError('Research performance disclosure was not selected')
    return document, payloads


def validate_intake_row(row, *, forbidden=()):
    raw = bytes(row['payload'])
    if len(raw) > MAX_REPORT or sha(raw) != row['payload_hash']:
        raise ValueError('Actual intake receipt hash differs')
    _public_content(load_json(raw,MAX_REPORT))
    if any(value and value.encode('utf-8') in raw for value in forbidden):
        raise ValueError('Actual intake receipt disclosed private fixture input')
    expected = sha(canonical_bytes({'receipt.json':sha(raw)}))
    # The real pending owner row has no transport artifact receipt yet. Derive
    # its immutable expected content hash, while retaining the observed state.
    if (row['artifact_hash'] is not None and row['artifact_hash'] != expected
            or row['artifact_hash'] is None and row['state'] not in ('PENDING','UNAVAILABLE')):
        raise ValueError('Actual intake transport artifact receipt differs')
    return dict(row,payload=raw.decode('utf-8'),artifact_hash=expected,kind='intake')


def _immutable(rows):
    return [{key:value for key,value in row.items() if key not in ('state','attempts')}
            for row in rows]


def observed_research_input(row):
    """Read a bounded, hash-bound internal owner record for lineage only.

    Internal provenance explicitly declares credentials=NONE. The external
    author/publication parser correctly rejects that field name, so it cannot
    decode this private record. Public payloads keep their original validators.
    """
    raw=row['input_json'].encode('utf-8')
    if len(raw)>MAX_PAYLOADS or sha(raw)!=row['input_hash']:
        raise ValueError('Native research report input lineage missing')
    value=decode(raw)
    if not isinstance(value,dict) or not isinstance(value.get('strategy'),dict):
        raise ValueError('Native research owner input structure differs')
    provenance=value.get('provenance')
    if (not isinstance(provenance,dict) or any(provenance.get(key)!=expected for key,expected in
            dict(credentials='NONE',provider_requests=0,capital='NONE',github_compute='NOT_USED').items())):
        raise ValueError('Expected credential-free local research owner input required')
    hash_value(value.get('dataset_manifest_hash'));hash_value(value.get('split_policy_hash'))
    return value


def _summary(result, *, status, maximum=MAX_PUBLICATIONS):
    names = ('attempted','local_staged','cloud_acknowledged','unavailable','conflicts')
    if (not isinstance(result, dict) or result.get('status') != status
            or any(type(result.get(name)) is not int or not 0 <= result[name] <= maximum for name in names)
            or sum(result[name] for name in names[1:]) != result['attempted']):
        raise ValueError('Actual bounded native publication counters required')


class NativePublicationFlow(PublicFixture):
    def __init__(self, package, output, *, expected_identity=None):
        super().__init__(Path(package), Path(output), 'positive', expected_identity=expected_identity)
        self.observation.update(publication_scope=ACK_SCOPE, real_cloud='NOT_RUN')
        # Research's normal mkdir preserves existing directories. Provision only
        # empty private filesystem ancestry before any product owner starts;
        # the actual public product still creates every database and result.
        self._private_directory(self.data/'worker-logs')

    def _owner_run(self):
        with readonly_store(self.data / 'queue.sqlite') as db:
            row = db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (self.research_job_id,)).fetchone()
        if row is None or row['state'] != 'COMPLETE' or not row['owner_run_id']:
            raise ValueError('Actual completed native research job required')
        raw = row['input_json'].encode('utf-8')
        if len(raw) > 512*1024 or sha(raw) != row['input_hash']:
            raise ValueError('Actual native research input differs')
        outcome = load_json(row['outcome_json'].encode('utf-8'), 65536)
        if outcome['run_id'] != row['owner_run_id']:
            raise ValueError('Actual research owner identity differs')
        return row['owner_run_id']

    def _run_facts(self):
        with readonly_store(self.data / 'canonical.sqlite3') as db:
            run = db.execute('SELECT binding_json,binding_hash FROM paper_process_runs WHERE run_id=?', (self.paper_run_id,)).fetchone()
            checkpoint = db.execute('SELECT revision,state_json,state_hash FROM paper_process_checkpoints WHERE run_id=? ORDER BY revision DESC LIMIT 1',
                (self.paper_run_id,)).fetchone()
            generation = db.execute('SELECT max(generation) FROM paper_process_generations WHERE run_id=?', (self.paper_run_id,)).fetchone()[0]
        if (run is None or checkpoint is None or not generation
                or sha(run['binding_json'].encode()) != run['binding_hash'] or sha(checkpoint['state_json'].encode()) != checkpoint['state_hash']):
            raise ValueError('Native Paper binding/checkpoint facts differ')
        return dict(run_id=self.paper_run_id, binding_hash=run['binding_hash'], revision=checkpoint['revision'],
            state_hash=checkpoint['state_hash'], process_generation=generation)

    def _paper_lineage(self, db, row, document):
        run = db.execute('SELECT * FROM paper_process_runs WHERE run_id=?', (row['run_id'],)).fetchone()
        checkpoint = db.execute('SELECT state_json,state_hash FROM paper_process_checkpoints WHERE run_id=? AND revision=?',
            (row['run_id'],row['run_revision'])).fetchone()
        generation = db.execute('SELECT instance_id FROM paper_process_generations WHERE run_id=? AND generation=?',
            (row['run_id'],row['process_generation'])).fetchone()
        if run is None or checkpoint is None or generation is None:
            raise ValueError('Native Paper report lineage missing')
        binding = load_json(run['binding_json'].encode(), 65536)
        if (sha(run['binding_json'].encode()) != run['binding_hash'] or run['binding_hash'] != row['binding_hash']
                or sha(checkpoint['state_json'].encode()) != checkpoint['state_hash'] or checkpoint['state_hash'] != row['checkpoint_state_hash']
                or document['assessment']['run_revision'] != row['run_revision']
                or document['producer']['process_generation'] != row['process_generation']
                or document['producer']['process_instance_hash'] != sha(generation['instance_id'].encode())
                or document['namespace'] != binding['namespace'] or document['observation']['mode'] != binding['mode']
                or document['strategy'] != dict(strategy_id=binding['strategy_id'],strategy_version=binding['strategy_version'],content_hash=binding['strategy_content_hash'])
                or document['binding'] != {key:binding[key] for key in ('config_hash','risk_policy_hash','paper_policy_hash')}
                or document['source']['implementation_hash'] != binding['implementation_hash']
                or document['source']['implementation_hash'] != self.identity['implementation_hash']
                or document['source']['executable_revision'] != self.identity['executable_revision']):
            raise ValueError('Native Paper report producer/checkpoint/source differs')

    def _publications(self):
        rows, final_paper = [], False
        forbidden = (self.password, str(self.output), str(ROOT))
        with readonly_store(self.data / 'canonical.sqlite3') as db:
            found = db.execute('SELECT * FROM paper_feedback_publications WHERE run_id=? ORDER BY operation_id LIMIT ?',
                (self.paper_run_id,MAX_PUBLICATIONS+1)).fetchall()
            for original in found:
                row = dict(original)
                document, _ = validate_report_row(row, 'paper', forbidden=forbidden)
                self._paper_lineage(db, row, document)
                observation = document['observation']
                final_paper |= observation['closed_trades'] == 1 and observation['simulated_elapsed_seconds'] > 0
                rows.append(dict(row,kind='paper'))
        with readonly_store(self.data / 'research.sqlite') as db:
            found = db.execute('SELECT * FROM research_feedback_publications WHERE run_id=? ORDER BY operation_id LIMIT ?',
                (self.research_owner_run_id,MAX_PUBLICATIONS+1)).fetchall()
            if len(found) != 1:
                raise ValueError('One actual research feedback publication required')
            owner = db.execute('SELECT input_json,input_hash FROM research_runs WHERE run_id=?', (self.research_owner_run_id,)).fetchone()
            if owner is None:
                raise ValueError('Native research report input lineage missing')
            inputs = observed_research_input(owner)
            for original in found:
                row = dict(original)
                document, _ = validate_report_row(row, 'research', forbidden=forbidden)
                strategy = inputs['strategy']
                if (document['strategy'] != {**{key:strategy[key] for key in ('strategy_id','strategy_version','content_hash')},**strategy['runtime_compatibility']}
                        or document['dataset']['manifest_hash'] != inputs['dataset_manifest_hash']
                        or document['split']['policy_hash'] != inputs['split_policy_hash']
                        or document['source']['implementation_hash'] != self.identity['implementation_hash']
                        or document['source']['executable_revision'] != self.identity['executable_revision']):
                    raise ValueError('Native research report strategy/dataset/split differs')
                rows.append(dict(row,kind='research'))
        with readonly_store(self.data / 'intake.sqlite') as db:
            found = db.execute('SELECT * FROM app_outbox ORDER BY operation_id LIMIT ?', (MAX_PUBLICATIONS+1,)).fetchall()
            for original in found:
                rows.append(validate_intake_row(dict(original),forbidden=forbidden))
        if not final_paper or not any(row['kind']=='intake' for row in rows) or len(rows) > MAX_PUBLICATIONS:
            raise ValueError('Bounded actual research/Paper/intake publications required')
        # bytes never enter observations; only private retained closures/hashes do.
        for row in rows:
            if type(row['attempts']) is not int or row['attempts'] < 0:
                raise ValueError('Actual outbox attempt count required')
        return sorted(rows, key=lambda row:row['operation_id'])

    def _artifact_closures(self, root, rows):
        closures = []
        for row in rows:
            logical = safe_relative(row['logical_path'])
            if row['kind']=='intake':
                payloads = {'receipt.json':row['payload'].encode('utf-8')}
            else:
                _, payloads = validate_report_row(row,row['kind'],forbidden=(self.password,str(self.output),str(ROOT)))
            hashes = {name:sha(value) for name,value in payloads.items()}
            artifact = sha(canonical_bytes(hashes))
            manifest = read_bounded(root, logical+'/manifest.json', 65536)
            expected = dict(schema_version='r7-result-bundle-v0.2',operation_id=row['operation_id'],artifact_hash=artifact,payload_hashes=hashes)
            if load_json(manifest) != expected or row['artifact_hash'] != artifact:
                raise ValueError('Native staged/remote artifact manifest differs')
            files = []
            for name, raw in (*sorted(payloads.items()),('manifest.json',manifest)):
                relative = logical+'/'+safe_relative(name)
                actual = read_bounded(root, relative, MAX_REPORT)
                if actual != raw:
                    raise ValueError('Native staged/remote actual bytes differ')
                files.append(dict(relative_path=(root/self._safe_relative(relative)).relative_to(self.output).as_posix(),bytes=len(raw),sha256=sha(raw)))
            closures.append(dict(operation_id=row['operation_id'],kind=row['kind'],artifact_hash=artifact,files=files))
        return closures

    @staticmethod
    def _safe_relative(value):
        return Path(safe_relative(value))

    def _stage_outboxes(self):
        total = 0
        for index in range(MAX_PUBLICATIONS+1):
            result = self.command('stage-'+str(index), ['publish-fixture-outbox','--config',self.config,'--limit','1'])
            _summary(result,status='LOCAL_STAGED',maximum=1)
            if result['cloud_acknowledged'] or result['unavailable'] or result['conflicts'] or result.get('remote_verification') != 'NOT_RUN':
                raise ValueError('Local stage cannot establish verified copy ACK')
            total += result['local_staged']
            if not result['attempted']:
                rows = self._publications()
                if total < 3 or any(row['state']!='LOCAL_STAGED' for row in rows):
                    raise ValueError('Native staging did not reach all actual owner outboxes')
                return rows
        raise ValueError('Native staging did not reach bounded quiescence')

    def _private_directory(self, path):
        if not path.is_relative_to(self.output) or path == self.output:
            raise ValueError('Exact private native fixture descendant required')
        current = self.output
        require_private(current,directory=True)
        for part in path.relative_to(self.output).parts:
            current /= part
            _local_path(current)
            if not current.exists():
                create_private_directory(current)
            require_private(current,directory=True)

    def _build_python(self):
        if os.name != 'nt':
            raise ValueError('Native local-copy helper build not prepared on this target')
        return ROOT.parents[1]/'toolchains/py312-native-build/Scripts/python.exe'

    def _build_helper(self):
        # PyInstaller's COLLECT uses ordinary Windows file copies. Keep its
        # private tree shallow enough for dependency filenames at owning depth.
        base = self.output/'h'
        if base.exists():
            raise ValueError('Fresh native helper build output required')
        self._private_directory(base)
        # The product runs without a user profile. Only this development
        # compiler needs a home/cache; keep both in its private work tree.
        build_home=base/'home'
        self._private_directory(build_home)
        self._private_directory(build_home/'pyinstaller-cache')
        build_env={**self.env,'USERPROFILE':str(build_home),
            'PYINSTALLER_CONFIG_DIR':str(build_home/'pyinstaller-cache')}
        source = TOOLS/'local_fixture_copy.py'
        source_before = sha(source.read_bytes())
        python = self._build_python()
        _local_path(python)
        if not python.is_file():
            raise ValueError('Existing local native helper toolchain unavailable')
        argv = [str(python),'-m','PyInstaller','--onedir','--console','--noupx','--noconfirm',
            '--name','R7FixtureCopy','--distpath',str(base/'dist'),'--workpath',str(base/'work'),
            '--specpath',str(base/'spec'),'--paths',str(ROOT/'src'),str(source)]
        raw_path = self.output/'helper-build.raw'
        log = self.output/'helper-build.log'
        owned, code, cleanup = None, None, None
        try:
            with raw_path.open('xb') as stream:
                owned = spawn_owned(argv,cwd=self.output,limits=ResourceLimits(900),stdout=stream,
                    stderr=subprocess.STDOUT,env=build_env)
                try:
                    code = owned.wait()
                finally:
                    cleanup = terminate_owned(owned,deadline_seconds=5)
        finally:
            if raw_path.exists():
                if raw_path.stat().st_size > 16*1024*1024:
                    raise ValueError('Bounded helper build log required')
                text = _sanitize(raw_path.read_text(encoding='utf-8',errors='replace'),ROOT)
                text = text.replace(self.password,'<SYNTHETIC_TEST_INPUT>').replace(str(self.output),'<PRIVATE_FIXTURE_ROOT>')
                write_private_new(log,text.encode('utf-8'))
                raw_path.unlink()
                self.commands.append(dict(command='build-local-fixture-copy',exit_code=code,
                    tree_reaped=bool(cleanup and cleanup.reaped),log=log.name,log_hash=sha(log.read_bytes())))
                self.persist()
        helper = base/'dist/R7FixtureCopy'/('R7FixtureCopy.exe' if os.name=='nt' else 'R7FixtureCopy')
        _local_path(helper)
        if code != 0 or not cleanup or not cleanup.reaped or not helper.is_file() or sha(source.read_bytes()) != source_before:
            raise ValueError('Actual owned local helper build failed')
        self.helper = helper
        self.helper_hash = sha(helper.read_bytes())
        self.helper_inventory = helper_inventory(helper.parent)
        self.helper_source_hash = source_before
        self.observation['copy_execution_tool'] = dict(source='tools/local_fixture_copy.py',source_hash=source_before,
            executable=helper.relative_to(self.output).as_posix(),executable_hash=self.helper_hash,
            complete_onedir_inventory=self.helper_inventory,inventory_hash=sha(canonical_bytes(self.helper_inventory)),
            scope='LOCAL_SYNTHETIC_COPY_ONLY')
        return helper

    def _require_helper(self):
        if (sha(self.helper.read_bytes())!=self.helper_hash
                or helper_inventory(self.helper.parent)!=self.helper_inventory):
            raise ValueError('Complete native copy helper runtime changed')

    def _prepare_bridge(self):
        helper = self._build_helper()
        work = self.data/'worker-logs/fixture-bridge'
        self.remote = self.output/'local-remote'
        if self.remote.exists() or work.exists():
            raise ValueError('Fresh exact local-copy peer required')
        self._private_directory(work)
        self._private_directory(self.remote)
        write_private_new(self.remote/'.r7-root.json',canonical_bytes({'root_id':ROOT_ID}))
        reference = self.output/'local-fixture-copy.json'
        alias, drive = 'fixturecopy','r7-local-fixture-0001'
        config = dict(schema_version='r7-local-fixture-copy-v1',data_class='SYNTHETIC_FIXTURE_ONLY',
            scope_root=str(self.output),stage_root=str(self.cloud),work_root=str(work),remote_root=str(self.remote),
            remote_alias=alias,drive_root_folder_id=drive)
        write_private_new(reference,canonical_bytes(config))
        profile = self.output/'fixture-bridge-profile.json'
        document = dict(schema_version='r7-rclone-bridge-config-v0.2',executable=str(helper),executable_sha256=sha(helper.read_bytes()),
            rclone_config_ref=str(reference),remote_alias=alias,drive_root_folder_id=drive,root_id=ROOT_ID,
            private_work_root=str(work),timeout_seconds=60,max_listing_bytes=1024*1024,max_transfer_bytes=16*1024*1024)
        write_private_new(profile,canonical_bytes(document))
        self.bridge_input_hashes = {profile:sha(profile.read_bytes()),reference:sha(reference.read_bytes())}
        return profile

    def _remote_cycle(self, profile, staged, facts):
        marker = self.remote/'.r7-root.json'
        retained = self.remote/'retained-root-marker.json'
        if (self.remote != self.output/'local-remote' or retained.exists()
                or load_json(read_bounded(self.remote,'.r7-root.json',4096)) != {'root_id':ROOT_ID}):
            raise ValueError('Exact fresh synthetic remote marker required')
        _local_path(marker)
        require_private(self.remote,directory=True)
        require_private(marker)
        marker.rename(retained)
        try:
            self._require_helper()
            failure = self.command('copy-peer-unavailable',['cloud-publish-outbox','--config',self.config,
                '--bridge-profile',profile,'--limit',str(MAX_PUBLICATIONS)],expected=2,json_result=True)
            self._require_helper()
        finally:
            if marker.exists():
                raise ValueError('Synthetic remote marker unexpectedly replaced; original retained')
            retained.rename(marker)
        _summary(failure,status='INCOMPLETE')
        failed = self._publications()
        if (failure['unavailable'] != len(staged) or failure['cloud_acknowledged'] or failure['conflicts'] or failure['local_staged']
                or _immutable(failed) != _immutable(staged) or any(row['state']!='UNAVAILABLE' for row in failed)
                or any(new['attempts']<=old['attempts'] for old,new in zip(staged,failed)) or self._run_facts()!=facts):
            raise ValueError('Actual failed native copy falsely ACKed or changed logical evidence')
        self._require_helper()
        result = self.command('copy-peer-retry',['cloud-publish-outbox','--config',self.config,
            '--bridge-profile',profile,'--limit',str(MAX_PUBLICATIONS)])
        self._require_helper()
        _summary(result,status='COMPLETE')
        acknowledged = self._publications()
        if (result['cloud_acknowledged'] != len(staged) or result['unavailable'] or result['conflicts'] or result['local_staged']
                or _immutable(acknowledged)!=_immutable(staged) or any(row['state']!='CLOUD_ACKNOWLEDGED' for row in acknowledged)
                or self._run_facts()!=facts):
            raise ValueError('Actual native local-copy byte ACK missing')
        remote = self._artifact_closures(self.remote,acknowledged)
        self._require_helper()
        again = self.command('copy-peer-idempotent',['cloud-publish-outbox','--config',self.config,
            '--bridge-profile',profile,'--limit',str(MAX_PUBLICATIONS)])
        self._require_helper()
        _summary(again,status='COMPLETE')
        if (again['attempted'] or self._publications()!=acknowledged or self._run_facts()!=facts
                or self._artifact_closures(self.remote,acknowledged)!=remote):
            raise ValueError('Native ACK replay changed logical effects or actual remote bytes')
        self.observation.update(remote_scope=ACK_SCOPE,real_cloud='NOT_RUN',failed_publication=failure,
            verified_copy=result,idempotent_copy=again,remote_artifact_closures=remote)

    def _publication(self):
        self.research_owner_run_id = self._owner_run()
        queued = self.command('queue-actual-research-feedback',['queue-research-feedback','--config',self.config,
            '--namespace','FIXTURE','--run-id',self.research_owner_run_id])
        if queued.get('status')!='FEEDBACK_QUEUED' or queued.get('cloud')!='NOT_CONTACTED':
            raise ValueError('Actual owner research feedback was not queued')
        facts = self._run_facts()
        initial = self._publications()
        if queued['operation_id'] not in {row['operation_id'] for row in initial if row['kind']=='research'}:
            raise ValueError('Actual queued research feedback reference differs')
        staged = self._stage_outboxes()
        if _immutable(initial)!=_immutable(staged) or self._run_facts()!=facts:
            raise ValueError('Native staging changed owner evidence')
        self.observation.update(research_job_id=self.research_job_id,research_owner_run_id=self.research_owner_run_id,
            paper_run_id=self.paper_run_id,original_paper_facts=facts,staged_artifact_closures=self._artifact_closures(self.cloud,staged),
            disclosure='ACTUAL_OWNER_REPORTS_OPT_OUT;SIMULATED_TIME_DISTINCT;REAL_FORWARD_NOT_ISSUED',
            owner_publications=[dict(operation_id=row['operation_id'],kind=row['kind'],artifact_hash=row['artifact_hash'],
                producer_generation=row.get('process_generation'),run_revision=row.get('run_revision')) for row in staged])
        profile = self._prepare_bridge()
        self._remote_cycle(profile,staged,facts)
        self.guard()
        self._require_helper()
        if (sha(self.helper.read_bytes())!=self.helper_hash or sha((TOOLS/'local_fixture_copy.py').read_bytes())!=self.helper_source_hash
                or any(sha(path.read_bytes())!=expected for path,expected in self.bridge_input_hashes.items())):
            raise ValueError('Native local-copy execution tool/configuration changed')
        self.observation['copy_execution_tool']['identity_rechecked_after_final_flush'] = True

    def run(self):
        passed = False
        try:
            super().run()
            self.observation['passed'] = False
            self._publication()
            passed = True
            return self.observation
        finally:
            self.observation.update(passed=passed,publication_scope=ACK_SCOPE,real_cloud='NOT_RUN')
            try:
                self.persist()
            except BaseException:
                self.observation['passed'] = False
                raise


def verify_slice(package, output, identity):
    flow=NativePublicationFlow(package,output/'publication',expected_identity=identity)
    try:return [flow.run()]
    except Exception as error:
        flow.observation.update(passed=False,error_type=type(error).__name__)
        flow.persist()
        return [flow.observation]
