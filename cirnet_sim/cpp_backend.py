"""Explicit transition adapter for the CNP1/CNP2 worker."""

import atexit
from concurrent.futures import Future, TimeoutError as FutureTimeout
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from functools import lru_cache
from hashlib import file_digest
from math import isfinite
from pathlib import Path
from queue import Empty, LifoQueue, SimpleQueue
import re
from secrets import randbits
from struct import Struct
import subprocess
import sys
from threading import Event, Lock, Thread
from time import monotonic

from jsonschema import ValidationError

from contracts.runtime_config import getenv, simulation_worker_count
from contracts.validation import validate

from .backends import BackendDescriptor, BackendIdentity
from .cpp_dc import PhysicalProjection, project_physical
from .dispatch import SimulationDispatcher
from .engine import SimulationError, VirtualCompiler


_MAGIC_DIGITAL = b'CNP1'
_MAGIC_PHYSICAL = b'CNP2'
_FRAME = Struct('<I')
_REQUEST = Struct('<4sQQQIIIIII')
_DC_COUNTS = Struct('<IIIIII')
_REPLY = Struct('<4sQQBI')
_EDGE = Struct('<II')
_DC_EDGE = Struct('<IIBB')
_DEVICE = Struct('<BIIIQ')
_DC_DEVICE = Struct('<BIIIQB')
_EVENT = Struct('<QIB')
_PROBE = Struct('<I')
_SAMPLE = Struct('<IQB')
_OPERATIONS = {'AND': 0, 'OR': 1, 'XOR': 2, 'NOT': 3}
_ERRORS = {1: 'UNEXECUTABLE', 2: 'EVENT_LIMIT', 3: 'CAPTURE_LIMIT'}
_VALUES = (0, 1, 'X')
_MAX_FRAME = 16 * 1024 * 1024
_MAX_SAMPLES = 100_000
_MAX_PHYSICAL_COUNT = 131_072
_MAX_PHYSICAL_SUFFIX = 2 * _FRAME.size + _MAX_PHYSICAL_COUNT * (1 + Struct('<Bd').size)
_MAX_REPLY = _FRAME.size + _REPLY.size + _MAX_SAMPLES * _SAMPLE.size + _MAX_PHYSICAL_SUFFIX
_REAP_TIMEOUT = 1
_default_lock = Lock()
_default_provider = None


@dataclass(frozen=True)
class _Worker:
    executable: Path
    sha256: str
    run_timeout: float
    preview_timeout: float
    run_slots: int
    preview_slots: int


@dataclass(frozen=True)
class _Projection:
    worker: _Worker
    generation: int
    endpoints: tuple
    edge_count: int
    device_count: int
    wire: bytes
    sources: tuple
    clocks: tuple
    probes: tuple
    physical: PhysicalProjection | None

    @property
    def directions(self):
        return dict(self.endpoints)


def _verify_executable(worker):
    try:
        if not worker.executable.is_file():
            raise OSError()
        with worker.executable.open('rb') as binary:
            observed = file_digest(binary, 'sha256').hexdigest()
    except OSError:
        raise SimulationError('BACKEND_UNAVAILABLE') from None
    if observed != worker.sha256:
        raise SimulationError('BACKEND_UNAVAILABLE')


def _reap(child):
    try:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=_REAP_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        if child.poll() is None:
            raise SimulationError('SAFE_STATE_FAILED') from None


def _read_reply(pipe):
    prefix = pipe.read(_FRAME.size)
    if not prefix:
        raise SimulationError('DRIVER_ERROR')
    if len(prefix) != _FRAME.size:
        raise SimulationError('PROTOCOL_MISMATCH')
    size = _FRAME.unpack(prefix)[0]
    if not _REPLY.size <= size <= _MAX_REPLY - _FRAME.size:
        raise SimulationError('PROTOCOL_MISMATCH')
    body = pipe.read(size)
    if len(body) != size:
        raise SimulationError('PROTOCOL_MISMATCH')
    return prefix + body


class _Connection:
    """Own a worker process and its sole pipe reader/writer."""

    def __init__(self, worker):
        self._requests = SimpleQueue()
        self._lock = Lock()
        self._closed = False
        self._io = Thread(target=self._serve_io, name='cirnet-cpp-worker-io', daemon=True)
        _verify_executable(worker)
        try:
            self.child = subprocess.Popen(
                [str(worker.executable), '--serve'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
        except OSError:
            raise SimulationError('BACKEND_UNAVAILABLE') from None

    def _serve_io(self):
        stdin, stdout = self.child.stdin, self.child.stdout
        try:
            while (job := self._requests.get()) is not None:
                request, response = job
                try:
                    stdin.write(request)
                    stdin.flush()
                    reply = _read_reply(stdout)
                except OSError:
                    response.set_exception(SimulationError('DRIVER_ERROR'))
                except SimulationError as error:
                    response.set_exception(error)
                else:
                    response.set_result(reply)
        finally:
            with suppress(OSError):
                stdin.close()
            stdout.close()

    def running(self):
        return not self._closed and self.child.poll() is None

    def exchange(self, request, deadline, cancel):
        response = Future()
        with self._lock:
            if self._closed:
                raise SimulationError('BACKEND_UNAVAILABLE')
            if self._io.ident is None:
                self._io.start()
            self._requests.put((request, response))
        while True:
            if cancel is not None and cancel.is_set():
                raise SimulationError('CANCELLED')
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise SimulationError('TIMEOUT')
            try:
                reply = response.result(timeout=min(remaining, .01) if cancel is not None else remaining)
            except FutureTimeout:
                continue
            if cancel is not None and cancel.is_set():
                raise SimulationError('CANCELLED')
            return reply

    def close(self):
        with self._lock:
            self._closed = True
            _reap(self.child)
            if self._io.ident is None:
                with suppress(OSError):
                    self.child.stdin.close()
                self.child.stdout.close()
            else:
                self._requests.put(None)
                self._io.join(_REAP_TIMEOUT)
                if self._io.is_alive():
                    raise SimulationError('SAFE_STATE_FAILED')


class _Lane:
    def __init__(self, worker):
        self._worker = worker
        self._connection = None
        self._closed = False
        self._lock = Lock()

    def exchange(self, request, timeout, cancel):
        if cancel is not None and cancel.is_set():
            raise SimulationError('CANCELLED')
        deadline = monotonic() + timeout
        with self._lock:
            if self._closed:
                raise SimulationError('BACKEND_UNAVAILABLE')
            if self._connection is not None and not self._connection.running():
                self._connection.close()
                self._connection = None
            if self._connection is None:
                self._connection = _Connection(self._worker)
            connection = self._connection
        try:
            return connection.exchange(request, deadline, cancel)
        except BaseException:
            self.discard()
            raise

    def discard(self):
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def close(self):
        with self._lock:
            self._closed = True
        self.discard()


def _close_all(resources):
    failed = False
    for resource in resources:
        try:
            resource.close()
        except SimulationError:
            failed = True
    if failed:
        raise SimulationError('SAFE_STATE_FAILED')


class _Pool:
    def __init__(self, worker, slots):
        self._lanes = tuple(_Lane(worker) for _ in range(slots))
        self._available = LifoQueue()
        for lane in self._lanes:
            self._available.put(lane)
        self._lock = Lock()
        self._closed = False

    @contextmanager
    def lease(self):
        with self._lock:
            if self._closed:
                raise SimulationError('BACKEND_UNAVAILABLE')
            try:
                lane = self._available.get_nowait()
            except Empty:
                raise SimulationError('RESOURCE_CONFLICT') from None
        try:
            yield lane
        finally:
            self._available.put(lane)

    def close(self):
        with self._lock:
            self._closed = True
        _close_all(self._lanes)


def _configuration(contract, value):
    try:
        return validate(contract, value)
    except ValidationError:
        raise SimulationError('UNEXECUTABLE') from None


def _validate_capture_configuration(value):
    config = _configuration('CaptureConfiguration', value)
    if 'trigger' in config:
        raise SimulationError('NOT_IMPLEMENTED')
    return tuple(config['signals']), int(config['duration_ns']), int(config.get('max_events', 100_000))


@lru_cache(maxsize=128, typed=True)
def _cached_capture_configuration(signals, duration, limit):
    value = {'signals': list(signals), 'duration_ns': duration}
    if limit is not None:
        value['max_events'] = limit
    return _validate_capture_configuration(value)


def _capture_configuration(value):
    # Only short, exact JSON shapes can share a validation result. Graph membership
    # and probe order are still checked against the active plan for every request.
    if type(value) is dict and len(value) in (2, 3):
        value = value.copy()
        if value.keys() <= {'signals', 'duration_ns', 'max_events'} and all(type(key) is str for key in value):
            signals, duration, limit = value.get('signals'), value.get('duration_ns'), value.get('max_events')
            if (type(signals) is list and len(signals) <= 4 and type(duration) in (int, float)
                    and (type(limit) in (int, float) or 'max_events' not in value)):
                signals = tuple(signals)
                if len(signals) <= 4 and all(type(signal) is str and len(signal) <= 128 for signal in signals):
                    return _cached_capture_configuration(signals, duration, limit)
    return _validate_capture_configuration(value)


def _input_events(plan, signal_ids, duration, limit, vectors, clock_config, inputs, preview):
    initial = dict(plan.sources)
    fixed = plan.physical.fixed_sources if plan.physical is not None else ()
    if inputs and (not isinstance(inputs, dict) or any(
        name not in initial or name in fixed or type(value) is not int or value not in (0, 1)
        for name, value in inputs.items()
    )):
        raise SimulationError('UNEXECUTABLE')
    initial.update(inputs or {})
    events = bytearray()
    limit_bytes = limit * _EVENT.size
    append = events.extend
    pack = _EVENT.pack

    def schedule(timestamp, name, value):
        if len(events) >= limit_bytes:
            raise SimulationError('EVENT_LIMIT')
        append(pack(timestamp, signal_ids[name], value))

    for name, value in sorted(initial.items()):
        schedule(0, name, value)
    if clock_config:
        clock_config = _configuration('ClockConfiguration', clock_config)
        if not any(name == clock_config['signal'] for name, _, _ in plan.clocks):
            raise SimulationError('UNEXECUTABLE')
    else:
        clock_config = {}
    for name, period, signal in (() if preview else plan.clocks):
        override = clock_config.get('signal') == name
        if override:
            period = int(clock_config['period_ns'])
        cycles = duration // period + 1
        if override:
            cycles = min(cycles, int(clock_config['cycles']))
        if cycles > 100_000:
            raise SimulationError('EVENT_LIMIT')
        paired_cycles = min(cycles, duration // period)
        half_period = period // 2
        last_rise = paired_cycles * period + half_period
        partial_cycle = paired_cycles < cycles and last_rise <= duration
        if len(events) + (2 * paired_cycles + partial_cycle) * _EVENT.size > limit_bytes:
            raise SimulationError('EVENT_LIMIT')
        for start in range(0, paired_cycles * period, period):
            append(pack(start + half_period, signal, 1))
            append(pack(start + period, signal, 0))
        if partial_cycle:
            append(pack(last_rise, signal, 1))
    for vector in vectors or ():
        if (not isinstance(vector, dict) or set(vector) != {'time_ns', 'inputs'}
                or type(vector['time_ns']) is not int or vector['time_ns'] < 0
                or not isinstance(vector['inputs'], dict)):
            raise SimulationError('UNEXECUTABLE')
        levels = vector['inputs']
        if any(name not in initial or name in fixed or type(value) is not int or value not in (0, 1)
               for name, value in levels.items()):
            raise SimulationError('UNEXECUTABLE')
        if vector['time_ns'] <= duration:
            for name, value in sorted(levels.items()):
                schedule(vector['time_ns'], name, value)
    return events


def _request(plan, request_id, duration, limit, events, probes):
    physical = plan.physical
    body = bytearray(_REQUEST.pack(
        _MAGIC_PHYSICAL if physical is not None else _MAGIC_DIGITAL,
        request_id, plan.generation, duration, limit, len(plan.endpoints), plan.edge_count,
        plan.device_count, len(events) // _EVENT.size, len(probes),
    ))
    body.extend(plan.wire)
    body.extend(events)
    for probe in probes:
        body.extend(_PROBE.pack(probe))
    if physical is not None:
        body.extend(physical.wire)
    if len(body) > _MAX_FRAME:
        raise SimulationError('UNEXECUTABLE')
    return _FRAME.pack(len(body)) + body


def _single_probe_samples(entries, plan, duration, probe):
    name = plan.endpoints[probe][0]
    samples = []
    previous_time, previous_value = -1, -1
    for signal, timestamp, value in entries:
        if (signal != probe or timestamp > duration or value >= len(_VALUES) or timestamp <= previous_time
                or value == previous_value or (previous_time < 0 and timestamp != 0)):
            raise SimulationError('PROTOCOL_MISMATCH')
        previous_time, previous_value = timestamp, value
        samples.append({'signal': name, 'time_ns': timestamp, 'value': _VALUES[value]})
    if not samples:
        raise SimulationError('PROTOCOL_MISMATCH')
    return samples


def _multi_probe_samples(entries, plan, duration, probes):
    positions = {index: position for position, index in enumerate(probes)}
    last = {}
    previous = (-1, -1)
    samples = []
    for signal, timestamp, value in entries:
        if signal not in positions or timestamp > duration or value >= len(_VALUES):
            raise SimulationError('PROTOCOL_MISMATCH')
        order = (timestamp, positions[signal])
        if order <= previous or last.get(signal) == value or (signal not in last and timestamp != 0):
            raise SimulationError('PROTOCOL_MISMATCH')
        last[signal] = value
        previous = order
        samples.append({'signal': plan.endpoints[signal][0], 'time_ns': timestamp, 'value': _VALUES[value]})
    if last.keys() != positions.keys():
        raise SimulationError('PROTOCOL_MISMATCH')
    return samples


def _capture(reply, plan, request_id, duration, probes):
    header_size = _FRAME.size + _REPLY.size
    if len(reply) < header_size or _FRAME.unpack_from(reply)[0] != len(reply) - _FRAME.size:
        raise SimulationError('PROTOCOL_MISMATCH')
    magic, request, generation, status, count = _REPLY.unpack_from(reply, _FRAME.size)
    expected_magic = _MAGIC_PHYSICAL if plan.physical is not None else _MAGIC_DIGITAL
    if (magic, request, generation) != (expected_magic, request_id, plan.generation):
        raise SimulationError('PROTOCOL_MISMATCH')
    samples_end = header_size + count * _SAMPLE.size
    if count > _MAX_SAMPLES or len(reply) < samples_end:
        raise SimulationError('PROTOCOL_MISMATCH')
    if status:
        if status not in _ERRORS or count or len(reply) != header_size:
            raise SimulationError('PROTOCOL_MISMATCH')
        raise SimulationError(_ERRORS[status])
    if plan.physical is None and len(reply) != samples_end:
        raise SimulationError('PROTOCOL_MISMATCH')

    entries = _SAMPLE.iter_unpack(memoryview(reply)[header_size:samples_end])
    if len(probes) == 1:
        samples = _single_probe_samples(entries, plan, duration, probes[0])
    else:
        samples = _multi_probe_samples(entries, plan, duration, probes)
    capture = {'available': bool(samples), 'state': 'COMPLETE', 'duration_ns': duration, 'samples': samples}
    if plan.physical is not None:
        capture.update(plan.physical.result(memoryview(reply)[samples_end:], plan.endpoints))
    return capture


class CppBackend:
    """Compose explicitly with a trusted executable and its release SHA-256."""

    descriptor = BackendDescriptor(BackendIdentity('cpp', '1.2.0', 3), True, True, False, 4)

    def __init__(self, executable, sha256, *, run_timeout=10, preview_timeout=2, run_slots=4, preview_slots=1):
        executable = Path(executable)
        if not executable.is_absolute() or not isinstance(sha256, str) or re.fullmatch(r'[0-9a-fA-F]{64}', sha256) is None:
            raise ValueError('Select an absolute C++ worker path and its SHA-256.')
        if any(type(value) not in (int, float) or not isfinite(value) or value <= 0
               for value in (run_timeout, preview_timeout)):
            raise ValueError('Worker deadlines must be finite and positive.')
        if any(type(value) is not int or value < 1 for value in (run_slots, preview_slots)):
            raise ValueError('Worker slot limits must be positive integers.')
        self._worker = _Worker(executable.resolve(), sha256.lower(), run_timeout, preview_timeout, run_slots, preview_slots)
        _verify_executable(self._worker)
        self._closed = Event()
        self._run_pool = _Pool(self._worker, run_slots)
        self._preview_pool = _Pool(self._worker, preview_slots)
        atexit.register(self.close)

    def compile(self, graph):
        return self._project(SimulationDispatcher().compile(graph))

    def _project(self, plan, *, preview=False):
        endpoints = tuple(plan.directions.items())
        signal_ids = {name: index for index, (name, _) in enumerate(endpoints)}
        edges = []
        for net in plan.nets:
            levels = dict(net.levels)
            for target in net.destinations:
                zero, one = levels.get(target, (0, 1))
                edges.append((signal_ids[net.source], signal_ids[target], _VALUES.index(zero), _VALUES.index(one)))
        devices = tuple(
            (_OPERATIONS[gate.operation], signal_ids[gate.inputs[0]],
             signal_ids[gate.inputs[1]] if len(gate.inputs) == 2 else 0,
             signal_ids[gate.output], gate.delay_ns, int(gate.enabled))
            for gate in sorted(plan.devices, key=lambda gate: gate.device_id)
        )
        physical = project_physical(plan.physical, signal_ids) if plan.physical is not None else None
        wire = bytearray()
        if physical is None:
            for source, target, _, _ in edges:
                wire.extend(_EDGE.pack(source, target))
            for operation, left, right, output, delay, _ in devices:
                wire.extend(_DEVICE.pack(operation, left, right, output, 0 if preview else delay))
        else:
            wire.extend(_DC_COUNTS.pack(*physical.counts))
            for edge in edges:
                wire.extend(_DC_EDGE.pack(*edge))
            for operation, left, right, output, delay, enabled in devices:
                wire.extend(_DC_DEVICE.pack(operation, left, right, output, 0 if preview else delay, enabled))
        return _Projection(
            self._worker, randbits(64), endpoints, len(edges), len(devices), bytes(wire),
            tuple(sorted(plan.initial_sources.items())),
            tuple((clock.signal, clock.period_ns, signal_ids[clock.signal]) for clock in plan.clocks),
            plan.probes, physical,
        )

    def _execute(self, plan, configuration, vectors, clock_config, inputs, *, preview=False, cancel=None):
        if not isinstance(plan, _Projection):
            raise SimulationError('BACKEND_PLAN_INVALID')
        if plan.worker != self._worker:
            raise SimulationError('BACKEND_IDENTITY_MISMATCH')
        if self._closed.is_set():
            raise SimulationError('BACKEND_UNAVAILABLE')
        if cancel is not None and cancel.is_set():
            raise SimulationError('CANCELLED')
        pool = self._preview_pool if preview else self._run_pool
        with pool.lease() as lane:
            signals, duration, limit = _capture_configuration(configuration)
            signal_ids = {name: index for index, (name, _) in enumerate(plan.endpoints)}
            selected = signals or plan.probes[:4] or [name for name, _ in plan.sources[:4]]
            if len(selected) > 4 or len(set(selected)) != len(selected) or any(name not in signal_ids for name in selected):
                raise SimulationError('UNEXECUTABLE')
            probes = tuple(signal_ids[name] for name in selected)
            events = _input_events(plan, signal_ids, duration, limit, vectors, clock_config, inputs, preview)
            request_id = randbits(64)
            request = _request(plan, request_id, duration, limit, events, probes)
            timeout = plan.worker.preview_timeout if preview else plan.worker.run_timeout
            reply = lane.exchange(request, timeout, cancel)
            try:
                capture = _capture(reply, plan, request_id, duration, probes)
            except SimulationError as error:
                if str(error) == 'PROTOCOL_MISMATCH':
                    lane.discard()
                raise
            if cancel is not None and cancel.is_set():
                lane.discard()
                raise SimulationError('CANCELLED')
            if self._closed.is_set():
                raise SimulationError('BACKEND_UNAVAILABLE')
            return capture

    def execute(self, payload, configuration, vectors=None, clock_config=None, inputs=None, *, cancel=None):
        """A transition caller can set its own cancellation event while a job runs."""
        return self._execute(payload, configuration, vectors, clock_config, inputs, cancel=cancel)

    def preview(self, graph):
        plan = self._project(VirtualCompiler().compile(graph), preview=True)
        capture = self._execute(plan, {'signals': [], 'duration_ns': 0, 'max_events': 10_000},
                                None, None, None, preview=True)
        diagnostics = capture.get('diagnostics', [])
        if plan.clocks:
            diagnostics.append('Static DC preview holds clocks at their initial level; use virtual capture for waveforms.')
        return {'device_states': capture.get('device_states', {}),
                'pin_values': capture.get('pin_values', {}), 'diagnostics': diagnostics}

    def close(self):
        """Reap both pools, including a worker with an in-flight job."""
        self._closed.set()
        _close_all((self._run_pool, self._preview_pool))
        atexit.unregister(self.close)


def configured_cpp_backend():
    """Use a single provider with configuration admitted once per process."""
    global _default_provider
    with _default_lock:
        if _default_provider is None:
            executable = getenv('CIRNET_SIM_CPP_WORKER')
            sha256 = getenv('CIRNET_SIM_CPP_WORKER_SHA256')
            if executable and sha256:
                _default_provider = CppBackend(executable, sha256, run_slots=simulation_worker_count())
        return _default_provider


def close_configured_cpp_backend():
    global _default_provider
    with _default_lock:
        if _default_provider is not None:
            _default_provider.close()
            _default_provider = None
