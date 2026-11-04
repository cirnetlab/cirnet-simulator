"""Replaceable providers preserve legacy behavior and bind execution identity."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import FrozenInstanceError, replace
import importlib
import importlib.util
from multiprocessing import get_context
import pickle
from types import SimpleNamespace

import pytest


def backend_api():
    assert importlib.util.find_spec('cirnet_sim.backends') is not None, 'Replaceable backend facade is missing.'
    return importlib.import_module('cirnet_sim.backends')


def graph():
    return {'schema_version':'1.1','circuit_id':'providers','modules':[
        {'id':'X','type':'DIGITAL_SWITCH','properties':{'state':True}}, {'id':'L','type':'LED'}],
        'connections':[{'source':'X.OUT','destination':'L.IN'}]}


CONFIG={'signals':['L.IN'],'duration_ns':20}


class TrustedProvider:
    def __init__(self,identity=None):
        b=backend_api()
        self.descriptor=b.BackendDescriptor(identity or b.BackendIdentity('trusted','2.0.0',3),True,True,False,2)
        self.calls=[]
    def compile(self,value):
        self.calls.append(('compile',value))
        return SimpleNamespace(directions={'P.OUT':'output'},token='compiled-by-trusted')
    def execute(self,payload,config,vectors=None,clock_config=None,inputs=None):
        self.calls.append(('execute',payload,config,vectors,clock_config,inputs))
        return {'available':True,'state':'COMPLETE','duration_ns':20,'samples':[{'signal':'P.OUT','time_ns':0,'value':1}]}
    def preview(self,value):
        self.calls.append(('preview',value))
        return {'device_states':{},'pin_values':{'P.OUT':1},'diagnostics':['trusted-preview']}


def test_legacy_compile_run_and_old_public_pairing_remain_equal():
    b=backend_api()
    from cirnet_sim.dispatch import SimulationDispatcher
    from cirnet_sim.engine import run_plan
    original=SimulationDispatcher().compile(graph())
    selected=b.compile_graph(graph(),backend_id='legacy')
    assert selected.payload==original
    assert dict(selected.directions)==original.directions
    assert b.run_plan(selected,CONFIG)==run_plan(original,CONFIG)
    assert selected.backend==b.BackendIdentity('legacy','1.0.0',1)


def test_preview_preserves_unsupported_states_and_does_not_use_strict_compile():
    b=backend_api()
    from cirnet_sim.engine import preview_physical_graph
    value={'schema_version':'1.1','circuit_id':'preview','modules':[{'id':'Q','type':'TRANSISTOR_2N3904'}],'connections':[]}
    expected=preview_physical_graph(value)
    assert expected['device_states']['Q']['state']=='UNSUPPORTED'
    assert b.preview_physical_graph(value,backend_id='legacy')==expected
    from cirnet_sim.dispatch import SimulationDispatcher
    with pytest.raises(b.SimulationError) as legacy_error:SimulationDispatcher().compile(value)
    with pytest.raises(b.SimulationError) as provider_error:b.compile_graph(value,backend_id='legacy')
    assert str(provider_error.value)==str(legacy_error.value)=='ANALOG_UNAVAILABLE'


def test_selection_is_explicit_and_environment_changes_do_not_reselect_a_plan(monkeypatch):
    b=backend_api()
    monkeypatch.delenv('CIRNET_SIMULATION_BACKEND',raising=False)
    monkeypatch.delenv('NETCIRCUIT_SIMULATION_BACKEND',raising=False)
    assert b.select_backend_id()=='legacy'
    selected=b.select_backend_id()
    monkeypatch.setenv('CIRNET_SIMULATION_BACKEND','ngspice')
    assert b.select_backend_id()=='ngspice'
    plan=b.compile_graph(graph(),backend_id=selected)
    assert b.run_plan(plan,CONFIG)['samples']==[{'signal':'L.IN','time_ns':0,'value':1}]
    with pytest.raises(b.SimulationError,match='BACKEND_UNAVAILABLE'):
        b.compile_graph(graph())


@pytest.mark.parametrize('value',['',' ', 'missing', 'os:system', '../../module',123,False])
def test_unknown_or_empty_configuration_fails_without_loading_code(value):
    b=backend_api()
    with pytest.raises(ValueError):b.select_backend_id(value)


def test_unknown_environment_selection_fails_clearly(monkeypatch):
    b=backend_api()
    monkeypatch.setenv('CIRNET_SIMULATION_BACKEND','missing')
    with pytest.raises(ValueError):b.get_backend()


@pytest.mark.parametrize('kind,code',[('DIGITAL_SWITCH','BACKEND_UNAVAILABLE'),('CAPACITOR_CERAMIC','ANALOG_UNAVAILABLE')])
def test_ngspice_is_unavailable_without_launch_or_legacy_fallback(monkeypatch,kind,code):
    b=backend_api()
    import subprocess
    import ctypes
    def forbidden(*args,**kwargs):raise AssertionError('No native engine or fallback may run.')
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    monkeypatch.setattr(ctypes,'CDLL',forbidden)
    monkeypatch.setattr(importlib,'import_module',forbidden)
    monkeypatch.setattr(b.LegacyBackend,'compile',forbidden)
    monkeypatch.setattr(b.LegacyBackend,'preview',forbidden)
    value={'schema_version':'1.1','circuit_id':'ngspice','modules':[{'id':'X','type':kind}],'connections':[]}
    descriptor=b.get_backend_descriptor('ngspice')
    assert not descriptor.available and not descriptor.digital and not descriptor.analog
    assert (descriptor.logic_analyzer_channels,descriptor.generator_channels,descriptor.oscilloscope_channels)==(0,0,0)
    for operation in (b.compile_graph,b.preview_physical_graph):
        with pytest.raises(b.SimulationError,match=code):operation(value,backend_id='ngspice')


def test_mixed_ngspice_boundary_retains_truthful_unavailability():
    b=backend_api()
    value=graph();value['modules'].append({'id':'C','type':'CAPACITOR_CERAMIC'})
    with pytest.raises(b.SimulationError,match='MIXED_SIGNAL_UNAVAILABLE'):
        b.compile_graph(value,backend_id='ngspice')


def test_registry_membership_identity_and_plan_directions_are_immutable():
    b=backend_api()
    provider=TrustedProvider()
    registry=b.BackendRegistry([provider])
    with pytest.raises(ValueError,match='Duplicate'):b.BackendRegistry([provider,provider])
    with pytest.raises(FrozenInstanceError):registry.entries=()
    with pytest.raises(FrozenInstanceError):provider.descriptor.identity.id='replacement'
    plan=b.compile_graph(graph(),backend_id='trusted',registry=registry)
    with pytest.raises(TypeError):plan.directions['invented']='input'
    with pytest.raises(FrozenInstanceError):plan.backend=b.BackendIdentity('legacy','1.0.0',1)


def test_trusted_alternative_receives_compile_execute_and_preview_explicitly():
    b=backend_api()
    provider=TrustedProvider();registry=b.BackendRegistry([provider])
    plan=b.compile_graph(graph(),backend_id='trusted',registry=registry)
    vectors=[{'time_ns':1,'inputs':{'X':0}}];clock={'signal':'clock'};inputs={'X':1}
    result=b.run_plan(plan,CONFIG,vectors,clock,inputs,registry=registry)
    assert result['samples']==[{'signal':'P.OUT','time_ns':0,'value':1}]
    assert b.preview_physical_graph(graph(),backend_id='trusted',registry=registry)['diagnostics']==['trusted-preview']
    assert [call[0] for call in provider.calls]==['compile','execute','preview']
    assert provider.calls[1][1].token=='compiled-by-trusted'
    assert provider.calls[1][2:]==(CONFIG,vectors,clock,inputs)
    # A parent-only extension is never reinterpreted as legacy by the worker.
    with pytest.raises(b.SimulationError,match='BACKEND_NOT_REGISTERED'):b.run_plan(plan,CONFIG)


@pytest.mark.parametrize('field,value',[('id','missing'),('adapter_version','9.0.0'),('plan_version',99)])
def test_worker_rejects_identity_tampering_before_provider_execution(monkeypatch,field,value):
    b=backend_api()
    plan=b.compile_graph(graph(),backend_id='legacy')
    modified=replace(plan,backend=replace(plan.backend,**{field:value}))
    def forbidden(*args,**kwargs):raise AssertionError('Mismatched provider must not execute.')
    monkeypatch.setattr(b.LegacyBackend,'execute',forbidden)
    with pytest.raises(b.SimulationError,match='BACKEND_(NOT_REGISTERED|IDENTITY_MISMATCH)'):
        b.run_plan(modified,CONFIG)


def test_raw_legacy_plan_is_not_implicitly_reinterpreted_by_new_worker():
    b=backend_api()
    from cirnet_sim.dispatch import SimulationDispatcher
    with pytest.raises(b.SimulationError,match='BACKEND_PLAN_INVALID'):
        b.run_plan(SimulationDispatcher().compile(graph()),CONFIG)


def test_pickle_and_actual_spawn_keep_pinned_provider_despite_environment(monkeypatch):
    b=backend_api()
    plan=b.compile_graph(graph(),backend_id='legacy')
    restored=pickle.loads(pickle.dumps(plan))
    assert restored==plan and dict(restored.directions)==dict(plan.directions)
    expected=b.run_plan(plan,CONFIG)
    monkeypatch.setenv('CIRNET_SIMULATION_BACKEND','ngspice')
    with ProcessPoolExecutor(max_workers=1,mp_context=get_context('spawn')) as pool:
        assert pool.submit(b.run_plan,restored,CONFIG).result(timeout=20)==expected
        custom=b.compile_graph(graph(),backend_id='trusted',registry=b.BackendRegistry([TrustedProvider()]))
        with pytest.raises(b.SimulationError,match='BACKEND_NOT_REGISTERED'):
            pool.submit(b.run_plan,custom,CONFIG).result(timeout=20)


def test_graph_metadata_cannot_override_explicit_backend_selection(monkeypatch):
    b=backend_api()
    value=graph();value['modules'][0]['properties'].update(backend='legacy',core='legacy')
    monkeypatch.setenv('CIRNET_SIMULATION_BACKEND','legacy')
    with pytest.raises(b.SimulationError,match='BACKEND_UNAVAILABLE'):
        b.compile_graph(value,backend_id='ngspice')


def test_provider_descriptor_mutation_after_registration_cannot_change_a_plan():
    b=backend_api();provider=TrustedProvider();registry=b.BackendRegistry([provider])
    plan=b.compile_graph(graph(),backend_id='trusted',registry=registry)
    provider.descriptor=replace(provider.descriptor,identity=b.BackendIdentity('trusted','3.0.0',3))
    with pytest.raises(b.SimulationError,match='BACKEND_IDENTITY_MISMATCH'):
        b.run_plan(plan,CONFIG,registry=registry)
    assert [call[0] for call in provider.calls]==['compile']


def test_nonserializable_provider_payload_is_rejected_before_worker_submission():
    b=backend_api()
    class InvalidProvider(TrustedProvider):
        def compile(self,value):return SimpleNamespace(directions={},callback=lambda:None)
    with pytest.raises(b.SimulationError,match='BACKEND_PLAN_NOT_SERIALIZABLE'):
        b.compile_graph(graph(),backend_id='trusted',registry=b.BackendRegistry([InvalidProvider()]))


def test_custom_worker_composes_registry_and_uses_compiled_configuration(tmp_path):
    backend_api()
    import json
    import subprocess
    import sys
    (tmp_path/'trusted_worker.py').write_text("""
import os
from types import SimpleNamespace
from cirnet_sim.backends import BackendIdentity,BackendDescriptor,BackendRegistry,run_plan
class ConfiguredProvider:
    descriptor=BackendDescriptor(BackendIdentity('configured','1.0.0',1),True,True,False,1)
    def compile(self,graph):
        return SimpleNamespace(directions={'P.OUT':'output'},level=int(os.environ['TEST_PROVIDER_LEVEL']))
    def execute(self,payload,config,vectors=None,clock_config=None,inputs=None):
        return {'pid':os.getpid(),'level':payload.level,'worker_environment':os.environ['TEST_PROVIDER_LEVEL']}
    def preview(self,graph):return {'device_states':{},'pin_values':{},'diagnostics':[]}
def execute(plan):
    return run_plan(plan,{},registry=BackendRegistry([ConfiguredProvider()]))
""",encoding='utf-8')
    (tmp_path/'run_worker.py').write_text("""
from pathlib import Path
import json,os,sys
sys.path.insert(0,str(Path(__file__).parent))
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from trusted_worker import ConfiguredProvider,execute
from cirnet_sim.backends import BackendRegistry,compile_graph
if __name__=='__main__':
    registry=BackendRegistry([ConfiguredProvider()])
    os.environ['TEST_PROVIDER_LEVEL']='1'
    first=compile_graph({},backend_id='configured',registry=registry)
    os.environ['TEST_PROVIDER_LEVEL']='0'
    with ProcessPoolExecutor(max_workers=1,mp_context=get_context('spawn')) as pool:
        a=pool.submit(execute,first).result(timeout=20)
        second=compile_graph({},backend_id='configured',registry=registry)
        os.environ['TEST_PROVIDER_LEVEL']='1'
        b=pool.submit(execute,second).result(timeout=20)
    print(json.dumps([a,b]))
""",encoding='utf-8')
    result=subprocess.run([sys.executable,'-I','-B',str(tmp_path/'run_worker.py')],capture_output=True,text=True,timeout=50)
    assert result.returncode==0,result.stderr
    first,second=json.loads(result.stdout)
    assert first['pid']==second['pid']
    assert [first['level'],second['level']]==[1,0]
    assert [first['worker_environment'],second['worker_environment']]==['0','0']


def test_unexpected_provider_bug_is_not_hidden_as_unavailable_or_legacy_success():
    b=backend_api()
    class BrokenProvider(TrustedProvider):
        def execute(self,*args,**kwargs):raise RuntimeError('provider implementation bug')
    provider=BrokenProvider();registry=b.BackendRegistry([provider])
    plan=b.compile_graph(graph(),backend_id='trusted',registry=registry)
    with pytest.raises(RuntimeError,match='provider implementation bug'):
        b.run_plan(plan,CONFIG,registry=registry)


def test_unavailable_descriptor_cannot_advertise_execution_or_instruments():
    b=backend_api()
    with pytest.raises(ValueError,match='unavailable'):
        b.BackendDescriptor(b.BackendIdentity('false-capability','1.0.0',1),False,True,False,4)


@pytest.mark.parametrize('operation',['compile_graph','preview_physical_graph'])
def test_unavailable_provider_maps_domain_rejection_to_existing_simulation_error(operation):
    b=backend_api()
    value=graph();value['modules'][0]['signal_domains']={'version':'2.0','future-field':True}
    with pytest.raises(b.SimulationError,match='UNSUPPORTED_SIGNAL_DOMAIN_VERSION'):
        getattr(b,operation)(value,backend_id='ngspice')
