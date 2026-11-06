"""Explicit simulation providers around the unchanged legacy implementation.

Only trusted application code composes registries. Plans are internal process
messages, never unpickled from documents or network requests. A provider must
compile all execution-relevant configuration into its serializable payload;
execute must not re-read ambient configuration or choose a different core.
"""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import pickle
import re
from typing import Protocol

from jsonschema import ValidationError
from contracts.signal_domains import classify_graph
from contracts.runtime_config import getenv
from .dispatch import SimulationDispatcher
from .engine import SimulationError
from . import engine as legacy_engine


def _valid_id(value):
    return isinstance(value,str) and re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',value) is not None


@dataclass(frozen=True)
class BackendIdentity:
    id: str
    adapter_version: str
    plan_version: int

    def __post_init__(self):
        if not _valid_id(self.id) or not isinstance(self.adapter_version,str) or not self.adapter_version.strip():
            raise ValueError('Backend identity requires a valid ID and adapter version.')
        if type(self.plan_version) is not int or self.plan_version<1:
            raise ValueError('Backend plan_version must be a positive integer.')


@dataclass(frozen=True)
class BackendDescriptor:
    identity: BackendIdentity
    available: bool
    digital: bool
    analog: bool
    logic_analyzer_channels: int
    generator_channels: int = 0
    oscilloscope_channels: int = 0

    def __post_init__(self):
        if not isinstance(self.identity,BackendIdentity):raise ValueError('Backend identity is required.')
        if any(type(value) is not bool for value in (self.available,self.digital,self.analog)):
            raise ValueError('Backend capability flags must be booleans.')
        counts=(self.logic_analyzer_channels,self.generator_channels,self.oscilloscope_channels)
        if any(type(value) is not int or value<0 for value in counts):
            raise ValueError('Backend channel counts must be nonnegative integers.')
        if not self.available and (self.digital or self.analog or any(counts)):
            raise ValueError('An unavailable backend cannot advertise execution capabilities.')


@dataclass(frozen=True)
class _Directions(Mapping):
    entries: tuple

    def __getitem__(self,key):
        for name,value in self.entries:
            if name==key:return value
        raise KeyError(key)
    def __iter__(self):return (name for name,_ in self.entries)
    def __len__(self):return len(self.entries)


@dataclass(frozen=True)
class CompiledPlan:
    backend: BackendIdentity
    payload: object
    directions: Mapping

    def __post_init__(self):
        if not isinstance(self.backend,BackendIdentity) or not isinstance(self.directions,Mapping):
            raise SimulationError('BACKEND_PLAN_INVALID')
        entries=tuple(self.directions.items())
        if any(not isinstance(key,str) or not isinstance(value,str) for key,value in entries):
            raise SimulationError('BACKEND_PLAN_INVALID')
        object.__setattr__(self,'directions',_Directions(entries))


class SimulationBackend(Protocol):
    descriptor: BackendDescriptor

    def compile(self,graph):
        """Return a serializable payload with a directions mapping and frozen configuration."""
        ...
    def execute(self,payload,configuration,vectors=None,clock_config=None,inputs=None):
        """Use payload configuration; do not reselect from environment or graph metadata."""
        ...
    def preview(self,graph):...


@dataclass(frozen=True,init=False)
class BackendRegistry:
    entries: tuple

    def __init__(self,providers:Iterable[SimulationBackend]):
        entries=[];identifiers=set()
        for provider in providers:
            descriptor=getattr(provider,'descriptor',None)
            if not isinstance(descriptor,BackendDescriptor):raise ValueError('Provider requires a BackendDescriptor.')
            if descriptor.identity.id in identifiers:raise ValueError('Duplicate backend ID: '+descriptor.identity.id)
            if any(not callable(getattr(provider,name,None)) for name in ('compile','execute','preview')):
                raise ValueError('Provider must implement compile, execute and preview.')
            identifiers.add(descriptor.identity.id);entries.append((descriptor,provider))
        object.__setattr__(self,'entries',tuple(entries))

    def _entry(self,backend_id):
        if not _valid_id(backend_id):raise ValueError('Invalid simulation backend ID.')
        for descriptor,provider in self.entries:
            if descriptor.identity.id==backend_id:return descriptor,provider
        raise ValueError('Unknown simulation backend: '+backend_id)

    def get(self,backend_id):
        descriptor,provider=self._entry(backend_id)
        if provider.descriptor!=descriptor:raise ValueError('Backend descriptor changed after registration.')
        return provider

    def descriptor(self,backend_id):
        self.get(backend_id)
        return self._entry(backend_id)[0]

    def resolve(self,identity):
        if not isinstance(identity,BackendIdentity):raise SimulationError('BACKEND_PLAN_INVALID')
        try:descriptor,provider=self._entry(identity.id)
        except ValueError:raise SimulationError('BACKEND_NOT_REGISTERED') from None
        if identity!=descriptor.identity or provider.descriptor!=descriptor:
            raise SimulationError('BACKEND_IDENTITY_MISMATCH')
        return provider


class LegacyBackend:
    descriptor=BackendDescriptor(BackendIdentity('legacy','1.0.0',1),True,True,False,4)

    def compile(self,graph):return SimulationDispatcher().compile(graph)
    def execute(self,payload,configuration,vectors=None,clock_config=None,inputs=None):
        return legacy_engine.run_plan(payload,configuration,vectors,clock_config,inputs)
    def preview(self,graph):
        # Preview intentionally preserves bounded UNSUPPORTED states; strict
        # execution admission must never be substituted here.
        return legacy_engine.preview_physical_graph(graph)


def _unavailable(graph=None):
    try:
        kind=classify_graph(graph)['kind'] if graph is not None else None
    except ValidationError as error:
        issues=getattr(error,'issues',None) or [{'code':'UNEXECUTABLE'}]
        raise SimulationError(issues[0].get('code','UNEXECUTABLE')) from None
    code={'ANALOG':'ANALOG_UNAVAILABLE','MIXED':'MIXED_SIGNAL_UNAVAILABLE'}.get(kind,'BACKEND_UNAVAILABLE')
    raise SimulationError(code)


class NgspiceBackend:
    """Reserved boundary only: no native library, executable or model adapter."""
    descriptor=BackendDescriptor(BackendIdentity('ngspice','1.0.0',1),False,False,False,0)

    def compile(self,graph):return _unavailable(graph)
    def execute(self,payload,configuration,vectors=None,clock_config=None,inputs=None):return _unavailable()
    def preview(self,graph):return _unavailable(graph)


def _builtins(include_cpp):
    providers = (LegacyBackend(), NgspiceBackend())
    if not include_cpp:
        return BackendRegistry(providers)
    from .cpp_backend import configured_cpp_backend
    cpp = configured_cpp_backend()
    return BackendRegistry(providers if cpp is None else (*providers, cpp))


def default_registry():
    """Code-owned built-ins and an explicitly pinned optional C++ worker."""
    return _builtins(include_cpp=True)


def close_native_workers():
    """Reap optional native workers owned by the default service registry."""
    from .cpp_backend import close_configured_cpp_backend
    close_configured_cpp_backend()


def _registry(registry, backend_id):
    if registry is None:return _builtins(include_cpp=backend_id=='cpp')
    if not isinstance(registry,BackendRegistry):raise ValueError('Expected an explicitly composed BackendRegistry.')
    return registry


def _selection(backend_id, registry):
    value=getenv('CIRNET_SIMULATION_BACKEND','legacy') if backend_id is None else backend_id
    return value,_registry(registry,value)


def select_backend_id(value=None,*,registry=None):
    """Resolve configuration once at application/station creation, never in run_plan."""
    value,selected=_selection(value,registry)
    selected.get(value)
    return value


def get_backend(backend_id=None,*,registry=None):
    value,selected=_selection(backend_id,registry)
    return selected.get(value)


def get_backend_descriptor(backend_id=None,*,registry=None):
    value,selected=_selection(backend_id,registry)
    return selected.descriptor(value)


def compile_graph(graph,*,backend_id=None,registry=None):
    value,selected=_selection(backend_id,registry)
    provider=selected.get(value)
    identity=provider.descriptor.identity
    if not provider.descriptor.available:return _unavailable(graph)
    payload=provider.compile(graph)
    # A descriptor cannot change during compilation and silently change identity.
    selected.resolve(identity)
    directions=getattr(payload,'directions',None)
    plan=CompiledPlan(identity,payload,directions)
    try:pickle.dumps(plan)
    except Exception as error:raise SimulationError('BACKEND_PLAN_NOT_SERIALIZABLE') from error
    return plan


def run_plan(plan,configuration,vectors=None,clock_config=None,inputs=None,*,registry=None,cancel=None):
    """Execute only the identity carried by the plan; ambient selection is irrelevant."""
    if not isinstance(plan,CompiledPlan):raise SimulationError('BACKEND_PLAN_INVALID')
    provider=_registry(registry,plan.backend.id).resolve(plan.backend)
    if not provider.descriptor.available:return _unavailable()
    if cancel is not None:
        from .cpp_backend import CppBackend
        if not isinstance(provider, CppBackend):
            raise SimulationError('NOT_IMPLEMENTED')
        return provider.execute(plan.payload,configuration,vectors,clock_config,inputs,cancel=cancel)
    return provider.execute(plan.payload,configuration,vectors,clock_config,inputs)


def preview_physical_graph(graph,*,backend_id=None,registry=None):
    provider=get_backend(backend_id,registry=registry)
    if not provider.descriptor.available:return _unavailable(graph)
    return provider.preview(graph)
