"""Real subprocess probes for wheel provenance and cleanup after bootstrap failure."""
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def probe(*paths):
    script=ROOT/'scripts/check_installed.py'
    program='import sys,runpy; sys.path[:0]=sys.argv[1:-1]; script=sys.argv[-1]; sys.argv=[script]; runpy.run_path(script,run_name="__main__")'
    return subprocess.run([sys.executable,'-I','-B','-c',program,*map(str,paths),str(ROOT/'scripts'),str(script)],capture_output=True,text=True)

def test_installed_wheel_has_expected_identity_and_resources():
    result=probe()
    assert result.returncode==0,result.stderr
    data=json.loads(result.stdout)
    assert data['simulator']['version']=='0.1.2' and data['simulator']['owned_files']==10
    assert data['contracts']['name']=='cirnet-contracts'
    assert data['contracts']['version']=='0.1.2' and data['contracts']['owned_files']>0

def test_source_shadowing_is_rejected():
    result=probe(ROOT)
    assert result.returncode!=0
    assert 'shadowed by source' in result.stderr

def test_legacy_contracts_distribution_is_rejected(tmp_path):
    legacy = tmp_path / 'netcircuit_contracts-0.1.1.dist-info'
    legacy.mkdir()
    (legacy / 'METADATA').write_text('Name: netcircuit-contracts\nVersion: 0.1.1\n', encoding='utf-8')
    result = probe(tmp_path)
    assert result.returncode != 0
    assert 'shares the contracts import namespace' in result.stderr


def test_modified_wheel_payload_is_rejected(tmp_path):
    artifact=distribution('cirnet-simulator')
    for item in artifact.files:
        relative=Path(str(item))
        if relative.parts[0] in ('cirnet_sim', 'netcircuit_sim') or (relative.parts[0].endswith('.dist-info') and len(relative.parts)>1):
            if relative.suffix=='.pyc':continue
            destination=tmp_path/relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(artifact.locate_file(item),destination)
    with (tmp_path/'cirnet_sim/engine.py').open('a',encoding='utf-8') as output:output.write('\n# corrupted probe payload\n')
    result=probe(tmp_path)
    assert result.returncode!=0 and 'differs from wheel RECORD' in result.stderr

def test_bootstrap_failure_publishes_cleanup_cli_before_pip(tmp_path):
    pin=json.loads((ROOT/'integration/contracts-version.json').read_text(encoding='utf-8'))['dev']
    filename=f"{pin['name'].replace('-', '_')}-{pin['version']}-py3-none-any.whl"
    wheel=Path(os.environ['CIRNET_ARTIFACTS_SESSION'])/'leaf-dev-bootstrap'/filename
    assert wheel.is_file(),'Bootstrap the pinned DEV artifact before verification.'
    env={**os.environ,'CIRNET_ARTIFACTS_DIR':str(tmp_path),'GITHUB_ENV':str(tmp_path/'github-env'),
         'PIP_REQUIREMENT':str(tmp_path/'intentionally-missing-requirements')}
    env.pop('CIRNET_ARTIFACTS_SESSION',None)
    env.pop('NETCIRCUIT_ARTIFACTS_SESSION',None)
    args=[sys.executable,str(ROOT/'scripts/bootstrap_contract_tools.py'),'--wheel',str(wheel),'--sha256',pin['wheel_sha256']]
    result=subprocess.run(args,env=env,capture_output=True,text=True)
    assert result.returncode!=0 and 'DEV wheel install failed' in result.stderr
    published=dict(line.split('=',1) for line in (tmp_path/'github-env').read_text(encoding='utf-8').splitlines())
    session=Path(published['CIRNET_ARTIFACTS_SESSION'])
    try:
        assert 'CIRNET_ARTIFACTS_CLI' in published,'Bootstrap must expose canonical cleanup even when pip fails.'
        cli=Path(published['CIRNET_ARTIFACTS_CLI'])
        assert cli.is_relative_to(session) and cli.is_file()
        assert (session/'leaf-dev-bootstrap/install.log').read_text(encoding='utf-8')
        cleaned=subprocess.run(['node',str(cli),'--context',published['CIRNET_ARTIFACTS_CONTEXT'],'--cleanup',str(session)],capture_output=True,text=True)
        assert cleaned.returncode==0,cleaned.stderr
    finally:
        # RED also cleans the owned fixture through the already installed canonical module.
        try:
            from cirnet_artifact_paths import cleanup_artifact_session
        except ModuleNotFoundError:
            from netcircuit_artifact_paths import cleanup_artifact_session
        if session.exists():cleanup_artifact_session(session,context=json.loads(published['CIRNET_ARTIFACTS_CONTEXT']))
    assert not session.exists()


def test_same_version_wheel_requires_selected_archive_and_force_install(tmp_path):
    import base64
    import csv
    import hashlib
    import io
    from urllib.parse import urlparse
    from urllib.request import url2pathname
    import venv
    from zipfile import ZipFile, ZIP_DEFLATED

    artifact=distribution('cirnet-simulator')
    selected=Path(url2pathname(urlparse(json.loads(artifact.read_text('direct_url.json'))['url']).path))
    old=tmp_path/'a'/selected.name
    candidate=tmp_path/'b'/selected.name
    old.parent.mkdir();candidate.parent.mkdir()
    shutil.copyfile(selected,old)
    with ZipFile(selected) as archive:
        payloads={name:archive.read(name) for name in archive.namelist()}
    metadata=next(name for name in payloads if name.endswith('.dist-info/METADATA'))
    record=next(name for name in payloads if name.endswith('.dist-info/RECORD'))
    payloads[metadata]+=b'\nSame-version regression candidate metadata.\n'
    lines=io.StringIO(newline='');writer=csv.writer(lines,lineterminator='\n')
    for name,data in payloads.items():
        if name!=record:
            digest=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
            writer.writerow([name,'sha256='+digest,len(data)])
    writer.writerow([record,'',''])
    payloads[record]=lines.getvalue().encode('utf-8')
    with ZipFile(candidate,'w',ZIP_DEFLATED) as archive:
        for name,data in payloads.items():archive.writestr(name,data)
    assert hashlib.sha256(old.read_bytes()).digest()!=hashlib.sha256(candidate.read_bytes()).digest()

    isolated=tmp_path/'v'
    venv.EnvBuilder(with_pip=False).create(isolated)
    python=isolated/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    result=subprocess.run([str(python),'-I','-B','-c','import json,site; print(json.dumps(site.getsitepackages()))'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    site_packages=next(Path(path) for path in json.loads(result.stdout) if Path(path).name=='site-packages')
    site_packages.mkdir(parents=True,exist_ok=True)
    # Only already installed third-party/Contracts dependencies are shared. The
    # child venv owns its distinct Simulator wheel and direct_url/RECORD metadata.
    (site_packages/'test-dependencies.pth').write_text(str(artifact.locate_file(''))+'\n',encoding='utf-8')
    pip=[sys.executable,'-m','pip','--python',str(python),'install','--no-index','--no-deps','--disable-pip-version-check']
    def install(path,*flags):
        value=subprocess.run([*pip,*flags,str(path)],capture_output=True,text=True)
        assert value.returncode==0,value.stdout+value.stderr
        return value
    install(old,'--ignore-installed')
    skipped=install(candidate)
    assert 'already installed' in skipped.stdout.lower()
    check=[str(python),str(ROOT/'scripts/check_installed.py'),'--wheel',str(candidate)]
    stale=subprocess.run(check,capture_output=True,text=True)
    assert stale.returncode!=0,'A stale same-version installation must not pass the newly selected wheel gate.'
    assert 'selected wheel' in stale.stderr
    install(candidate,'--force-reinstall')
    verified=subprocess.run(check,capture_output=True,text=True)
    assert verified.returncode==0,verified.stderr
    data=json.loads(verified.stdout)
    assert data['simulator']['selected_sha256']==hashlib.sha256(candidate.read_bytes()).hexdigest()
    assert data['simulator']['selected_files']==15
