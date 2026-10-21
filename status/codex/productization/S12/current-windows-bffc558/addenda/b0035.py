"""Copy already verified public delivery bytes; never copy an operating profile."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[1]
ROOT = PROJECT / 'workspaces/project-r7-productization-master-20261002'
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from application.platform.private_files import create_private_directory, write_private_atomic, write_private_new
from application.paper.producer import _guard
from application.paper.inventory import current_target, fixed_profile
from application.platform.distribution import verify_distribution

REV = 'bffc558b9652dc41c0804896436ac7ad8744f7f8'
ZIP_SHA = 'b05a81eef327bf5ce2c32fa246a805f79f7b0f73aa32a13b37f5403dce4e1642'
DOCTOR_SHA = '7c543e32ae5314f82a648ed71a23e6e0f59f725150890ad55e128d3dca246f1c'

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()

def local(path):
    from application.platform.supervision import _local_path
    _local_path(path)
    if not path.resolve().is_relative_to(PROJECT.resolve()):
        raise ValueError('Public delivery must remain inside the project')

def run():
    installed = PROJECT / 'installations/windows-bffc558-clean'
    facts = verify_distribution(installed)
    guard = lambda: _guard(ROOT, REV, installed, facts, fixed_profile(current_target()))
    guard()
    delivery = PROJECT / 'deliveries/current-windows-bffc558'
    local(delivery)
    version_path = delivery / 'version.json'
    version = json.loads(version_path.read_bytes())
    if version['revision'] != REV or version['identity'] != facts or version['archive_sha256'] != ZIP_SHA:
        raise ValueError('Existing verified launch guide subject differs')
    if 'delivery_files' in version:
        raise ValueError('Delivery already materialized; inspect retained results')
    archive = PROJECT / version['archive_ref']
    local(archive)
    if digest(archive) != ZIP_SHA:
        raise ValueError('Actual portable ZIP changed')
    portable = BASE / 'portable-bffc558-first'
    smoke = json.loads((portable / 'first-run-smoke/native-smoke.json').read_bytes())
    doctor = portable / 'first-run-smoke/01-doctor.log'
    # The existing actual command record binds the original observation.
    doctor_records = [row for row in smoke['commands'] if row['name'] == '01-doctor'
                      and row['log'] == '01-doctor.log' and row['log_sha256'] == DOCTOR_SHA
                      and row['passed'] is True and row['tree_reaped'] is True and row['exit_code'] == 0]
    if smoke['identity'] != facts or smoke['passed'] is not True or digest(doctor) != DOCTOR_SHA or len(doctor_records) != 1:
        raise ValueError('Original actual hardware command commitment differs')
    kit = portable / 'chat-authoring-kit'
    expected = {'README.md', 'authoring-reference.md', 'engineering-example-not-gpt.json',
                'capabilities.json', 'version.json', 'engineering-package/manifest.json',
                'engineering-package/strategy.json'}
    if {p.relative_to(kit).as_posix() for p in kit.rglob('*') if p.is_file()} != expected:
        raise ValueError('Exact already verified authoring kit required')
    pairs = [(archive, delivery / archive.name),
             (BASE / 'build-bffc558/build-result.json', delivery / 'build-result.json'),
             (installed / 'FIRST_RUN.md', delivery / 'FIRST_RUN.md'),
             (doctor, delivery / 'hardware-current-host.json')]
    pairs += [(kit / name, delivery / 'chat-authoring-kit' / name) for name in sorted(expected)]
    observations = []
    for source, destination in pairs:
        local(source)
        local(destination)
        if source.is_symlink() or not source.is_file() or source.stat().st_nlink != 1:
            raise ValueError('Regular single-link public source required')
        if destination.exists():
            raise ValueError('Fresh public copy required')
        if not destination.parent.exists():
            create_private_directory(destination.parent)
        before = digest(source)
        with source.open('rb') as incoming, destination.open('xb') as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
        if digest(source) != before or digest(destination) != before or destination.stat().st_nlink != 1:
            raise ValueError('Actual copied public bytes differ')
        observations.append(dict(source_ref=source.relative_to(PROJECT).as_posix(),
            delivery_ref=destination.relative_to(delivery).as_posix(), sha256=before,
            size_bytes=destination.stat().st_size))
    guard()
    hardware = dict(executable_revision=REV, source_ref=doctor.relative_to(PROJECT).as_posix(),
        source_sha256=DOCTOR_SHA, original_command_record=doctor_records[0],
        scope='CURRENT_DEVELOPMENT_HOST_ONLY', target_machine_acceptance='NOT_RUN',
        credentials='NONE', financial_authority='NONE')
    write_private_new(delivery / 'hardware-provenance.json', (json.dumps(hardware, indent=2) + '\n').encode())
    version.update(delivery_archive_ref=(delivery / archive.name).relative_to(PROJECT).as_posix(),
        delivery_archive_sha256=ZIP_SHA, delivery_files=observations,
        hardware_provenance_ref='hardware-provenance.json', operating_profile_copied=False,
        authoring_kit_strategy='ENGINEERING_BASELINE_NOT_GPT')
    write_private_atomic(version_path, (json.dumps(version, indent=2) + '\n').encode())
    readme = delivery / 'README.md'
    addition = '''\n## 集中交付內容\n\n本資料夾已實際複製完整安裝 ZIP、`build-result.json`、`FIRST_RUN.md`、`hardware-current-host.json`／`hardware-provenance.json` 與 `chat-authoring-kit/`。複製檔案的來源、大小與 SHA-256 保留於 `version.json`；ZIP 的校驗碼見 `SHA256SUMS.txt`。可整個搬移此資料夾，再依目標機全新設定與驗收。硬體紀錄只代表目前開發電腦，沒有替代舊電腦或 Ubuntu 驗收。\n'''
    write_private_atomic(readme, readme.read_bytes() + addition.encode())
    guard()
    print(json.dumps(dict(passed=True, revision=REV, copied_files=len(observations),
        zip_sha256=ZIP_SHA, delivery_ref=delivery.relative_to(PROJECT).as_posix(),
        operating_profile_copied=False)), flush=True)

if __name__ == '__main__':
    run()
