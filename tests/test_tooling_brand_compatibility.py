"""Pre-install tooling accepts canonical settings and immutable legacy DEV wheels."""
import hashlib
import importlib.util
import io
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    spec = importlib.util.spec_from_file_location('tooling_brand_' + name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preinstall_environment_preserves_legacy_and_canonical_precedence(monkeypatch):
    helper = load_script('environment', monkeypatch)
    old = {'NETCIRCUIT_ARTIFACTS_DIR': '/legacy'}
    assert helper.getenv('CIRNET_ARTIFACTS_DIR', environ=old) == '/legacy'
    selected = helper.export_environment({**old, 'CIRNET_ARTIFACTS_DIR': '/canonical'})
    assert selected['NETCIRCUIT_ARTIFACTS_DIR'] == selected['CIRNET_ARTIFACTS_DIR'] == '/canonical'
    assert old == {'NETCIRCUIT_ARTIFACTS_DIR': '/legacy'}


@pytest.mark.parametrize('name', ['cirnet-artifact-paths', 'netcircuit-artifact-paths'])
def test_dev_bootstrap_verifies_resource_for_selected_distribution(name, monkeypatch):
    bootstrap = load_script('bootstrap_contract_tools', monkeypatch)
    payload = io.BytesIO()
    namespace = name.replace('-', '_')
    with ZipFile(payload, 'w') as archive:
        archive.writestr(namespace + '-1.0.0a1.dist-info/METADATA', f'Name: {name}\nVersion: 1.0.0a1\n')
        archive.writestr(namespace + '/artifact-paths.mjs', b'verified canonical allocator')
    contents = payload.getvalue()
    assert bootstrap.verified_dev_payload(contents, hashlib.sha256(contents).hexdigest()) == b'verified canonical allocator'
    with pytest.raises(ValueError, match='SHA256'):
        bootstrap.verified_dev_payload(contents, '0' * 64)
