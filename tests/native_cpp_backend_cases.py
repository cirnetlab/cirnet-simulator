"""Opt-in transition checks against an explicitly selected C++ worker."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import os
from pathlib import Path
import pickle
from queue import Empty, Queue
from struct import Struct
import subprocess
import sys
from threading import Event, Timer

import pytest

from contracts.capture_codec import encode_digital
from cirnet_sim import cpp_backend
from cirnet_sim.backends import (
    BackendRegistry, LegacyBackend, SimulationError, compile_graph, preview_physical_graph, run_plan,
)


GRAPH = {
    'schema_version': '1.0',
    'circuit_id': 'native-and',
    'modules': [
        {'id': 'X', 'type': 'DIGITAL_SWITCH', 'properties': {'state': False}},
        {'id': 'Y', 'type': 'DIGITAL_SWITCH', 'properties': {'state': True}},
        {'id': 'G', 'type': '74HC08'},
        {'id': 'L', 'type': 'LED'},
    ],
    'connections': [
        {'source': 'X.OUT', 'destination': 'G.A1'},
        {'source': 'Y.OUT', 'destination': 'G.B1'},
        {'source': 'G.Y1', 'destination': 'L.IN'},
    ],
}
CONFIG = {'signals': ['G.Y1'], 'duration_ns': 40, 'max_events': 100}
VECTORS = [{'time_ns': 20, 'inputs': {'X.OUT': 1}}]
CLOCK_GRAPH = {'schema_version': '1.0', 'circuit_id': 'clock',
               'modules': [{'id': 'C', 'type': 'CLOCK', 'properties': {'frequency_hz': 100_000_000}}],
               'connections': []}


@pytest.fixture
def selection():
    return Path(os.environ['CIRNET_CPP_WORKER']), os.environ['CIRNET_CPP_WORKER_SHA256']


@pytest.fixture
def backend(selection):
    provider = cpp_backend.CppBackend(*selection, run_slots=1, preview_slots=1)
    yield provider
    provider.close()


def registry(provider):
    return BackendRegistry((LegacyBackend(), provider))


def test_and_capture_matches_python_after_the_plan_crosses_a_pickle_boundary(backend, monkeypatch):
    from cirnet_sim.backends import close_native_workers

    close_native_workers()
    for prefix in ('CIRNET', 'NETCIRCUIT'):
        monkeypatch.delenv(f'{prefix}_SIM_CPP_WORKER', raising=False)
        monkeypatch.delenv(f'{prefix}_SIM_CPP_WORKER_SHA256', raising=False)
    providers = registry(backend)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    plan = pickle.loads(pickle.dumps(plan))
    capture = run_plan(plan, CONFIG, VECTORS, registry=providers)
    legacy = run_plan(compile_graph(GRAPH, backend_id='legacy'), CONFIG, VECTORS)
    assert capture == legacy
    assert capture['samples'] == [
        {'signal': 'G.Y1', 'time_ns': 0, 'value': 'X'},
        {'signal': 'G.Y1', 'time_ns': 8, 'value': 0},
        {'signal': 'G.Y1', 'time_ns': 28, 'value': 1},
    ]
    encoded = encode_digital(capture['samples'], capture['duration_ns'])
    assert sha256(encoded).hexdigest() == 'a7d9fbe031939f9cdbf60f0f626b325beac173d9e720eb968fc62d9b83314010'
    with pytest.raises(SimulationError, match='^BACKEND_NOT_REGISTERED$'):
        run_plan(plan, CONFIG, VECTORS)


def test_same_timestamp_samples_follow_probe_order_and_inputs_are_overridden(backend):
    providers = registry(backend)
    config = {'signals': ['L.IN', 'G.Y1'], 'duration_ns': 40}
    vectors = [
        {'time_ns': 20, 'inputs': {'Y.OUT': 0}},
        {'time_ns': 20, 'inputs': {'X.OUT': 0, 'Y.OUT': 1}},
    ]
    native = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    legacy = compile_graph(GRAPH, backend_id='legacy')
    assert run_plan(native, config, vectors, inputs={'X.OUT': 1}, registry=providers) == run_plan(
        legacy, config, vectors, inputs={'X.OUT': 1},
    )


def test_integral_json_numbers_are_accepted_by_the_binary_boundary(backend):
    providers = registry(backend)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    config = {**CONFIG, 'duration_ns': 40.0, 'max_events': 100.0}
    capture = run_plan(plan, config, VECTORS, registry=providers)
    assert type(capture['duration_ns']) is int
    assert capture == run_plan(compile_graph(GRAPH, backend_id='legacy'), CONFIG, VECTORS)
    with pytest.raises(SimulationError, match='^UNEXECUTABLE$'):
        run_plan(plan, {**config, 'max_events': 100.5}, VECTORS, registry=providers)


def test_capture_configuration_reuses_only_exact_validation_results(backend, monkeypatch):
    cache = getattr(cpp_backend, '_cached_capture_configuration', None)
    if cache is not None:
        cache.cache_clear()
    providers = registry(backend)
    plan = compile_graph(CLOCK_GRAPH, backend_id='cpp', registry=providers)
    validator = cpp_backend._configuration
    checked = []

    def record(contract, value):
        if contract == 'CaptureConfiguration':
            checked.append(value)
        return validator(contract, value)

    monkeypatch.setattr(cpp_backend, '_configuration', record)
    config = {'signals': ['C.OUT'], 'duration_ns': 0, 'max_events': 1}
    capture = run_plan(plan, config, registry=providers)
    assert run_plan(plan, {**config, 'signals': ['C.OUT']}, registry=providers) == capture
    assert len(checked) == 1
    assert run_plan(plan, {**config, 'duration_ns': 0.0}, registry=providers) == capture
    assert run_plan(plan, {'signals': ['C.OUT'], 'duration_ns': 0}, registry=providers) == capture
    assert len(checked) == 3

    for invalid in ({**config, 'duration_ns': False}, {**config, 'max_events': True},
                    {**config, 'max_events': None}, {**config, 'signals': ('C.OUT',)},
                    {**config, 'extra': 0}):
        with pytest.raises(SimulationError, match='^UNEXECUTABLE$'):
            run_plan(plan, invalid, registry=providers)

    class AliasedSignal(str):
        pass

    assert run_plan(plan, {**config, 'signals': [AliasedSignal('C.OUT')]}, registry=providers) == capture
    assert len(checked) == 9

    frozen = cpp_backend._capture_configuration(config)
    config['signals'][0] = 'different'
    assert frozen == (('C.OUT',), 0, 1)
    assert run_plan(plan, {'signals': ['C.OUT'], 'duration_ns': 0, 'max_events': 1}, registry=providers) == capture
    assert len(checked) == 9


def test_clock_and_held_clock_preview_match_python(backend):
    config = {'signals': ['C.OUT'], 'duration_ns': 50}
    clock = {'signal': 'C.OUT', 'period_ns': 8, 'cycles': 3}
    providers = registry(backend)
    native = compile_graph(CLOCK_GRAPH, backend_id='cpp', registry=providers)
    legacy = compile_graph(CLOCK_GRAPH, backend_id='legacy')
    assert run_plan(native, config, clock_config=clock, registry=providers) == run_plan(
        legacy, config, clock_config=clock,
    )
    floating_clock = {**clock, 'period_ns': 8.0, 'cycles': 3.0}
    assert run_plan(native, config, clock_config=floating_clock, registry=providers) == run_plan(
        legacy, config, clock_config=clock,
    )
    assert preview_physical_graph(CLOCK_GRAPH, backend_id='cpp', registry=providers) == preview_physical_graph(
        CLOCK_GRAPH, backend_id='legacy',
    )


@pytest.mark.parametrize(('duration', 'cycles', 'times'), [
    (0, 3, [0]), (2, 3, [0, 2]), (5, 3, [0, 2, 5]), (12, 2, [0, 2, 5, 7, 10]),
    (12, 3, [0, 2, 5, 7, 10, 12]),
])
def test_clock_clips_odd_period_and_honors_exact_event_budget(backend, duration, cycles, times):
    providers = registry(backend)
    native = compile_graph(CLOCK_GRAPH, backend_id='cpp', registry=providers)
    legacy = compile_graph(CLOCK_GRAPH, backend_id='legacy')
    clock = {'signal': 'C.OUT', 'period_ns': 5, 'cycles': cycles}
    config = {'signals': ['C.OUT'], 'duration_ns': duration, 'max_events': len(times)}
    capture = run_plan(native, config, clock_config=clock, registry=providers)
    assert capture == run_plan(legacy, config, clock_config=clock)
    assert [sample['time_ns'] for sample in capture['samples']] == times
    if len(times) > 1:
        with pytest.raises(SimulationError, match='^EVENT_LIMIT$'):
            run_plan(native, {**config, 'max_events': len(times) - 1}, clock_config=clock, registry=providers)


def test_clock_precedes_vectors_at_equal_timestamps(backend):
    providers = registry(backend)
    native = compile_graph(CLOCK_GRAPH, backend_id='cpp', registry=providers)
    legacy = compile_graph(CLOCK_GRAPH, backend_id='legacy')
    clock = {'signal': 'C.OUT', 'period_ns': 5, 'cycles': 1}
    config = {'signals': ['C.OUT'], 'duration_ns': 5}
    vectors = [{'time_ns': 2, 'inputs': {'C.OUT': 0}}, {'time_ns': 5, 'inputs': {'C.OUT': 1}}]
    assert run_plan(native, config, vectors, clock_config=clock, registry=providers) == run_plan(
        legacy, config, vectors, clock_config=clock,
    )


def test_preview_uses_the_pinned_worker_and_its_own_budget(backend, monkeypatch):
    providers = registry(backend)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    exchange = cpp_backend._Lane.exchange
    requests = []

    def record(lane, request, timeout, cancel):
        requests.append((request, timeout))
        return exchange(lane, request, timeout, cancel)

    monkeypatch.setattr(cpp_backend._Lane, 'exchange', record)
    with backend._run_pool.lease():
        with pytest.raises(SimulationError, match='^RESOURCE_CONFLICT$'):
            run_plan(plan, CONFIG, VECTORS, registry=providers)
        assert preview_physical_graph(GRAPH, backend_id='cpp', registry=providers) == preview_physical_graph(
            GRAPH, backend_id='legacy',
        )
    [(frame, timeout)] = requests
    header = Struct('<4sQQQIIIIII')
    _, _, _, duration, limit, _, edge_count, device_count, _, _ = header.unpack_from(frame, 4)
    assert (duration, limit, timeout) == (0, 10_000, 2)
    for offset in range(4 + header.size + edge_count * 8, 4 + header.size + edge_count * 8 + device_count * 21, 21):
        assert Struct('<BIIIQ').unpack_from(frame, offset)[-1] == 0


@pytest.mark.parametrize(
    ('configuration', 'code'),
    [({**CONFIG, 'max_events': 2}, 'EVENT_LIMIT'), ({**CONFIG, 'max_events': 3}, 'EVENT_LIMIT'),
     ({**CONFIG, 'signals': ['unknown']}, 'UNEXECUTABLE')],
)
def test_stable_execution_errors(backend, configuration, code):
    providers = registry(backend)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    with pytest.raises(SimulationError, match=f'^{code}$'):
        run_plan(plan, configuration, VECTORS, registry=providers)


@pytest.mark.parametrize('mixed,code', [(False, 'ANALOG_UNAVAILABLE'), (True, 'MIXED_SIGNAL_UNAVAILABLE')])
def test_unsupported_analog_run_never_launches_or_falls_back(backend, monkeypatch, mixed, code):
    def forbidden(*args):
        pytest.fail('Unsupported circuits must not launch the C++ worker.')

    monkeypatch.setattr(cpp_backend.subprocess, 'Popen', forbidden)
    providers = registry(backend)
    graph = {'schema_version': '1.1', 'circuit_id': 'unsupported',
             'modules': [{'id': 'U', 'type': 'CAPACITOR_CERAMIC'}],
             'connections': []}
    if mixed:
        graph['modules'].append({'id': 'D', 'type': 'DIGITAL_SWITCH'})
    with pytest.raises(SimulationError, match=f'^{code}$'):
        compile_graph(graph, backend_id='cpp', registry=providers)


def test_artifact_pin_and_generation_are_required(selection, backend, monkeypatch):
    with pytest.raises(ValueError):
        cpp_backend.CppBackend(Path('worker'), selection[1])
    providers = registry(backend)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    with pytest.raises(SimulationError, match='^BACKEND_IDENTITY_MISMATCH$'):
        run_plan(plan, CONFIG, VECTORS, registry=registry(cpp_backend.CppBackend(*selection, run_timeout=3)))

    exchange = cpp_backend._Lane.exchange

    def stale(lane, request, timeout, cancel):
        response = bytearray(exchange(lane, request, timeout, cancel))
        response[16] ^= 1
        return response

    monkeypatch.setattr(cpp_backend._Lane, 'exchange', stale)
    with pytest.raises(SimulationError, match='^PROTOCOL_MISMATCH$'):
        run_plan(plan, CONFIG, VECTORS, registry=providers)


def test_prepacked_plan_rejects_the_old_projection_version(backend):
    providers = registry(backend)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    old_plan = replace(plan, backend=replace(plan.backend, plan_version=2))
    with pytest.raises(SimulationError, match='^BACKEND_IDENTITY_MISMATCH$'):
        run_plan(old_plan, CONFIG, VECTORS, registry=providers)


@pytest.mark.parametrize('mutation', ['first_timestamp', 'unprobed_signal', 'repeated_level', 'repeated_time',
                                      'unknown_level', 'late_sample'])
def test_single_probe_capture_rejects_invalid_samples(backend, monkeypatch, mutation):
    providers = registry(backend)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    exchange = cpp_backend._Lane.exchange
    sample = Struct('<IQB')

    def corrupt(lane, request, timeout, cancel):
        reply = bytearray(exchange(lane, request, timeout, cancel))
        first = 4 + Struct('<4sQQBI').size
        second = first + sample.size
        signal, timestamp, value = sample.unpack_from(reply, second)
        if mutation == 'first_timestamp':
            sample.pack_into(reply, first, signal, 1, 2)
        elif mutation == 'unprobed_signal':
            sample.pack_into(reply, second, 0, timestamp, value)
        elif mutation == 'repeated_level':
            sample.pack_into(reply, second, signal, timestamp, 2)
        elif mutation == 'repeated_time':
            sample.pack_into(reply, second, signal, 0, value)
        elif mutation == 'unknown_level':
            sample.pack_into(reply, second, signal, timestamp, 3)
        elif mutation == 'late_sample':
            sample.pack_into(reply, second, signal, CONFIG['duration_ns'] + 1, value)
        return reply

    monkeypatch.setattr(cpp_backend._Lane, 'exchange', corrupt)
    with pytest.raises(SimulationError, match='^PROTOCOL_MISMATCH$'):
        run_plan(plan, CONFIG, VECTORS, registry=providers)


@pytest.mark.parametrize('action', ['timeout', 'cancel', 'crash'])
def test_owned_subprocess_is_reaped_after_an_execution_failure(selection, monkeypatch, action):
    provider = cpp_backend.CppBackend(*selection, run_timeout=.5 if action == 'timeout' else 5)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=registry(provider))
    original = subprocess.Popen
    seen = []
    cancel = Event()
    timer = Timer(.1, cancel.set)

    def start(_worker, **options):
        # Replace only the child program. The adapter's pipe handling and cleanup are real.
        script = 'raise SystemExit(2)' if action == 'crash' else 'import time; time.sleep(60)'
        child = original([sys.executable, '-B', '-c', script], **options)
        seen.append(child)
        if action == 'cancel':
            timer.start()
        return child

    monkeypatch.setattr(cpp_backend.subprocess, 'Popen', start)
    try:
        code = {'timeout': 'TIMEOUT', 'cancel': 'CANCELLED', 'crash': 'DRIVER_ERROR'}[action]
        with pytest.raises(SimulationError, match=f'^{code}$'):
            provider.execute(plan.payload, CONFIG, VECTORS, cancel=cancel)
        assert len(seen) == 1 and seen[0].poll() is not None
    finally:
        timer.cancel()
        provider.close()


def test_persistent_run_and_preview_have_independent_children(backend, monkeypatch):
    original = subprocess.Popen
    children = []

    def observe(command, **options):
        assert command[-1] == '--serve'
        child = original(command, **options)
        children.append(child)
        return child

    monkeypatch.setattr(cpp_backend.subprocess, 'Popen', observe)
    providers = registry(backend)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    for _ in range(3):
        assert run_plan(plan, CONFIG, VECTORS, registry=providers)['available']
        assert preview_physical_graph(GRAPH, backend_id='cpp', registry=providers) == {
            'device_states': {}, 'pin_values': {}, 'diagnostics': [],
        }
    assert len(children) == 2 and all(child.poll() is None for child in children)
    backend.close()
    assert all(child.poll() is not None for child in children)
    with pytest.raises(SimulationError, match='^BACKEND_UNAVAILABLE$'):
        run_plan(plan, CONFIG, registry=providers)


def test_cancellation_discards_only_its_lane_and_replacement_works(backend, monkeypatch):
    original = subprocess.Popen
    children = []
    cancel = Event()
    timer = Timer(.1, cancel.set)

    def start(command, **options):
        hung = len(children) == 1
        if hung:
            command = [sys.executable, '-B', '-c', 'import time; time.sleep(60)']
        child = original(command, **options)
        children.append(child)
        if hung:
            timer.start()
        return child

    monkeypatch.setattr(cpp_backend.subprocess, 'Popen', start)
    providers = registry(backend)
    plan = compile_graph(GRAPH, backend_id='cpp', registry=providers)
    try:
        preview_physical_graph(GRAPH, backend_id='cpp', registry=providers)
        with pytest.raises(SimulationError, match='^CANCELLED$'):
            run_plan(plan, CONFIG, VECTORS, registry=providers, cancel=cancel)
        assert len(children) == 2 and children[0].poll() is None and children[1].poll() is not None
        assert run_plan(plan, CONFIG, VECTORS, registry=providers)['available']
        assert len(children) == 3 and children[0].poll() is None and children[2].poll() is None
    finally:
        timer.cancel()


def test_configured_default_worker_does_not_change_the_default_backend_or_reselect_plan(selection, monkeypatch):
    from cirnet_sim.backends import close_native_workers, select_backend_id

    close_native_workers()
    monkeypatch.delenv('CIRNET_SIMULATION_BACKEND', raising=False)
    monkeypatch.delenv('NETCIRCUIT_SIMULATION_BACKEND', raising=False)
    monkeypatch.setenv('CIRNET_SIM_CPP_WORKER', str(selection[0]))
    monkeypatch.setenv('CIRNET_SIM_CPP_WORKER_SHA256', selection[1])
    try:
        assert select_backend_id() == 'legacy'
        plan = compile_graph(GRAPH, backend_id='cpp')
        monkeypatch.delenv('CIRNET_SIM_CPP_WORKER')
        monkeypatch.delenv('CIRNET_SIM_CPP_WORKER_SHA256')
        assert run_plan(plan, CONFIG, VECTORS)['available']
        cancel = Event()
        cancel.set()
        with pytest.raises(SimulationError, match='^CANCELLED$'):
            run_plan(plan, CONFIG, VECTORS, cancel=cancel)
    finally:
        close_native_workers()


@pytest.mark.parametrize('workers', [4, 5])
def test_configured_run_slots_match_station_worker_count(selection, monkeypatch, workers):
    from cirnet_sim.backends import close_native_workers

    close_native_workers()
    monkeypatch.setenv('CIRNET_SIM_CPP_WORKER', str(selection[0]))
    monkeypatch.setenv('CIRNET_SIM_CPP_WORKER_SHA256', selection[1])
    monkeypatch.setenv('CIRNET_SIMULATION_WORKERS', str(workers))
    admitted = Queue()
    release = Event()
    request_header = Struct('<4sQQQIIIIII')
    reply_header = Struct('<4sQQBI')
    index = Struct('<I')
    sample = Struct('<IQB')

    def controlled_exchange(lane, request, timeout, cancel):
        magic, request_id, generation, duration, *_ = request_header.unpack_from(request, index.size)
        if duration:
            admitted.put(None)
            assert release.wait(10), 'Configured Run slots were not released.'
        signal, = index.unpack_from(request, len(request) - index.size)
        body = reply_header.pack(magic, request_id, generation, 0, 1) + sample.pack(signal, 0, 2)
        return index.pack(len(body)) + body

    monkeypatch.setattr(cpp_backend._Lane, 'exchange', controlled_exchange)
    try:
        plan = compile_graph(GRAPH, backend_id='cpp')
        with ThreadPoolExecutor(max_workers=workers) as callers:
            jobs = [callers.submit(run_plan, plan, CONFIG, VECTORS) for _ in range(workers)]
            try:
                for _ in jobs:
                    try:
                        admitted.get(timeout=5)
                    except Empty:
                        for job in jobs:
                            if job.done():
                                job.result()
                        pytest.fail('A configured Run slot was never admitted.')
                with pytest.raises(SimulationError, match='^RESOURCE_CONFLICT$'):
                    run_plan(plan, CONFIG, VECTORS)
                assert preview_physical_graph(GRAPH, backend_id='cpp') == {
                    'device_states': {}, 'pin_values': {}, 'diagnostics': [],
                }
            finally:
                release.set()
            assert all(job.result(timeout=5)['available'] for job in jobs)
    finally:
        close_native_workers()


def test_legacy_rollback_does_not_admit_a_stale_optional_worker(selection, monkeypatch):
    from cirnet_sim.backends import close_native_workers, select_backend_id

    close_native_workers()
    monkeypatch.setenv('CIRNET_SIM_CPP_WORKER', str(selection[0].with_name('missing-worker')))
    monkeypatch.setenv('CIRNET_SIM_CPP_WORKER_SHA256', selection[1])
    monkeypatch.setenv('CIRNET_SIMULATION_BACKEND', 'legacy')
    assert select_backend_id() == 'legacy'
    assert run_plan(compile_graph(GRAPH), CONFIG, VECTORS)['available']
    with pytest.raises(SimulationError, match='^BACKEND_UNAVAILABLE$'):
        select_backend_id('cpp')


def _powered_graph(mode):
    graph = {
        'schema_version': '1.1',
        'circuit_id': 'native-powered',
        'modules': [
            {'id': 'PS', 'type': 'DC_SUPPLY', 'properties': {'voltage': 5}},
            {'id': 'U', 'type': 'SN74HC08N'},
            {'id': 'A', 'type': 'DIGITAL_SWITCH', 'properties': {'state': True}},
            {'id': 'R', 'type': 'RESISTOR_AXIAL', 'properties': {'resistanceOhms': 330}},
            {'id': 'L', 'type': 'LED_LTL307EE'},
        ],
        'connections': [
            {'source': 'PS.PLUS', 'destination': 'U.14'},
            {'source': 'PS.MINUS', 'destination': 'U.7'},
            {'source': 'PS.PLUS', 'destination': 'U.1'},
            {'source': 'A.OUT', 'destination': 'U.2'},
            {'source': 'U.3', 'destination': 'R.A'},
            {'source': 'R.B', 'destination': 'L.A'},
            {'source': 'L.K', 'destination': 'PS.MINUS'},
        ],
    }
    if mode == 'unpowered':
        graph['connections'].pop(1)
    elif mode == 'unreferenced':
        graph['modules'].append({'id': 'PS2', 'type': 'DC_SUPPLY', 'properties': {'voltage': 5}})
        graph['connections'][2]['source'] = 'PS2.PLUS'
    elif mode == 'overcurrent':
        graph['modules'][3]['properties']['resistanceOhms'] = 1
    elif mode == 'open':
        graph['connections'].pop()
    return graph


@pytest.mark.parametrize(
    'mode, gate_state, led_state, final',
    [('powered', 'POWERED', 'ON', 1), ('unpowered', 'UNPOWERED', 'OFF', 'X'),
     ('unreferenced', 'POWERED', 'UNKNOWN', 'X'), ('overcurrent', 'POWERED', 'FAULT', 1),
     ('open', 'POWERED', 'OFF', 1)],
)
def test_powered_gate_and_led_match_full_legacy_result(backend, mode, gate_state, led_state, final):
    graph = _powered_graph(mode)
    config = {'signals': ['U.3', 'U.1'], 'duration_ns': 30}
    providers = registry(backend)
    legacy = run_plan(compile_graph(graph, backend_id='legacy'), config)
    plan = compile_graph(graph, backend_id='cpp', registry=providers)
    result = run_plan(pickle.loads(pickle.dumps(plan)), config, registry=providers)
    assert result == legacy
    assert result['pin_values']['U.3'] == final
    assert result['device_states']['U']['state'] == gate_state
    assert result['device_states']['L']['state'] == led_state
    assert preview_physical_graph(graph, backend_id='cpp', registry=providers) == preview_physical_graph(
        graph, backend_id='legacy',
    )


def test_fixed_physical_supply_levels_cannot_be_overridden(backend):
    providers = registry(backend)
    plan = compile_graph(_powered_graph('powered'), backend_id='cpp', registry=providers)
    config = {'signals': ['U.3'], 'duration_ns': 20}
    with pytest.raises(SimulationError, match='^UNEXECUTABLE$'):
        run_plan(plan, config, inputs={'PS.PLUS': 0}, registry=providers)
    with pytest.raises(SimulationError, match='^UNEXECUTABLE$'):
        run_plan(plan, config, [{'time_ns': 1, 'inputs': {'PS.MINUS': 1}}], registry=providers)


def test_native_preview_preserves_permissive_unsupported_states(backend):
    graph = {'schema_version': '1.1', 'circuit_id': 'unsupported-preview',
             'modules': [{'id': 'Q', 'type': 'TRANSISTOR_2N3904'}], 'connections': []}
    result = preview_physical_graph(graph, backend_id='cpp', registry=registry(backend))
    assert result == preview_physical_graph(graph, backend_id='legacy')
    assert result['device_states']['Q']['state'] == 'UNSUPPORTED'


@pytest.mark.parametrize('gate', ['AND', 'OR', 'XOR', 'NOT'])
def test_digital_gate_vectors_match_legacy_facade(backend, gate):
    graph = {
        'schema_version': '1.0',
        'circuit_id': f'native-{gate.lower()}',
        'modules': [
            {'id': 'A', 'type': 'DIGITAL_INPUT', 'properties': {'state': False}},
            {'id': 'B', 'type': 'DIGITAL_SWITCH', 'properties': {'state': True}},
            {'id': 'G', 'type': gate},
            {'id': 'L', 'type': 'LED'},
        ],
        'connections': [{'source': 'A.OUT', 'destination': 'G.A'}, {'source': 'G.Y', 'destination': 'L.IN'}],
    }
    if gate != 'NOT':
        graph['connections'].append({'source': 'B.OUT', 'destination': 'G.B'})
    config = {'signals': ['L.IN', 'G.Y'], 'duration_ns': 40}
    vectors = [
        {'time_ns': 10, 'inputs': {'A.OUT': 1}},
        {'time_ns': 20, 'inputs': {'B.OUT': 0}},
        {'time_ns': 25, 'inputs': {'A.OUT': 0}},
    ]
    providers = registry(backend)
    legacy = run_plan(compile_graph(graph, backend_id='legacy'), config, vectors)
    native = run_plan(compile_graph(graph, backend_id='cpp', registry=providers), config, vectors, registry=providers)
    assert native == legacy
    assert native['samples'][0]['value'] == 'X'


def test_all_four_powered_gates_keep_pin_mapping_and_same_time_order(backend):
    graph = _powered_graph('powered')
    graph['modules'].append({'id': 'B', 'type': 'DIGITAL_SWITCH', 'properties': {'state': False}})
    for first, second, switch in ((4, 5, 'B'), (9, 10, 'A'), (12, 13, 'B')):
        graph['connections'].extend((
            {'source': 'PS.PLUS', 'destination': f'U.{first}'},
            {'source': f'{switch}.OUT', 'destination': f'U.{second}'},
        ))
    signals = ['U.11', 'U.3', 'U.8', 'U.6']
    config = {'signals': signals, 'duration_ns': 30}
    vectors = [{'time_ns': 10, 'inputs': {'A.OUT': 0, 'B.OUT': 1}}]
    providers = registry(backend)
    native = run_plan(compile_graph(graph, backend_id='cpp', registry=providers), config, vectors, registry=providers)
    assert native == run_plan(compile_graph(graph, backend_id='legacy'), config, vectors)
    for time_ns, values in ((0, ['X'] * 4), (8, [0, 1, 1, 0]), (18, [1, 0, 0, 1])):
        assert [sample for sample in native['samples'] if sample['time_ns'] == time_ns] == [
            {'signal': signal, 'time_ns': time_ns, 'value': value}
            for signal, value in zip(signals, values, strict=True)
        ]
