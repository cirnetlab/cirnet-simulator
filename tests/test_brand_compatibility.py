"""Canonical and legacy consumers share types across import and worker boundaries."""
import subprocess
import sys

import pytest


@pytest.mark.parametrize('first', ['cirnet_sim', 'netcircuit_sim'])
def test_import_order_preserves_package_submodule_and_class_identity(first):
    program = """
import importlib, pickle, sys
importlib.import_module(sys.argv[1])
assert importlib.import_module('cirnet_sim') is importlib.import_module('netcircuit_sim')
for name in ('analog','backends','circuit','dispatch','engine','logic','nets','waveform'):
    assert importlib.import_module('cirnet_sim.'+name) is importlib.import_module('netcircuit_sim.'+name)
from cirnet_sim.backends import BackendIdentity
assert BackendIdentity.__module__ == 'cirnet_sim.backends'
assert pickle.loads(b'cnetcircuit_sim.backends\\nBackendIdentity\\n.') is BackendIdentity
"""
    result = subprocess.run([sys.executable, '-I', '-B', '-c', program, first], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_old_pickle_module_path_resolves_in_spawned_worker(tmp_path):
    (tmp_path / 'worker.py').write_text("""
import pickle
def legacy_identity(payload):
    from cirnet_sim.backends import BackendIdentity
    from netcircuit_sim.backends import BackendIdentity as LegacyIdentity
    return pickle.loads(payload) is BackendIdentity is LegacyIdentity
def run_legacy_plan(payload):
    from cirnet_sim.backends import run_plan
    return run_plan(pickle.loads(payload),{'signals':['L.IN'],'duration_ns':20})
""")
    (tmp_path / 'run.py').write_text("""
import sys,pickle
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from worker import legacy_identity,run_legacy_plan
from cirnet_sim.backends import compile_graph
if __name__ == '__main__':
    graph={'schema_version':'1.1','circuit_id':'legacy-worker','modules':[
        {'id':'X','type':'DIGITAL_SWITCH','properties':{'state':True}}, {'id':'L','type':'LED'}],
        'connections':[{'source':'X.OUT','destination':'L.IN'}]}
    payload=pickle.dumps(compile_graph(graph,backend_id='legacy'),protocol=0).replace(b'cirnet_sim.',b'netcircuit_sim.')
    with ProcessPoolExecutor(max_workers=1,mp_context=get_context('spawn')) as pool:
        assert pool.submit(legacy_identity,b'cnetcircuit_sim.backends\\nBackendIdentity\\n.').result(timeout=20)
        result=pool.submit(run_legacy_plan,payload).result(timeout=20)
        assert result['samples']==[{'signal':'L.IN','time_ns':0,'value':1}]
""")
    result = subprocess.run([sys.executable, '-I', '-B', str(tmp_path / 'run.py')], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_backend_setting_legacy_fallback_and_canonical_precedence(monkeypatch):
    from cirnet_sim.backends import select_backend_id
    monkeypatch.delenv('CIRNET_SIMULATION_BACKEND', raising=False)
    monkeypatch.setenv('NETCIRCUIT_SIMULATION_BACKEND', 'ngspice')
    assert select_backend_id() == 'ngspice'
    monkeypatch.setenv('CIRNET_SIMULATION_BACKEND', 'legacy')
    assert select_backend_id() == 'legacy'
    monkeypatch.setenv('CIRNET_SIMULATION_BACKEND', '')
    with pytest.raises(ValueError):
        select_backend_id()
