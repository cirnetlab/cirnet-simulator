"""Exercise the private CNP1 protocol through the native worker executable."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import os
from pathlib import Path
from struct import Struct
import subprocess

import pytest


LENGTH = Struct('<I')
REQUEST = Struct('<4sQQQIIIIII')
RESPONSE = Struct('<4sQQBI')
EDGE = Struct('<II')
DEVICE = Struct('<BIIIQ')
INPUT = Struct('<QIB')
PROBE = Struct('<I')
SAMPLE = Struct('<IQB')
DC_COUNTS = Struct('<IIIIII')
MAPPED_EDGE = Struct('<IIBB')
POWERED_DEVICE = Struct('<BIIIQB')
POTENTIAL = Struct('<IId')
DRIVER = Struct('<IIIdd')
LED = Struct('<IIdd')
LED_RESULT = Struct('<Bd')


@pytest.fixture(scope='module')
def worker():
    selection = os.environ.get('CIRNET_TEST_CPP_WORKER')
    if selection is None:
        pytest.skip('Set CIRNET_TEST_CPP_WORKER to run the native worker gate.')
    return Path(selection)


def request(*, duration=40, limit=100, signals=0, edges=(), devices=(), inputs=(), probes=(),
            request_id=0x123456789ABCDEF0, generation=17):
    return b''.join((
        REQUEST.pack(b'CNP1', request_id, generation, duration, limit, signals,
                     len(edges), len(devices), len(inputs), len(probes)),
        b''.join(EDGE.pack(*edge) for edge in edges),
        b''.join(DEVICE.pack(*device) for device in devices),
        b''.join(INPUT.pack(*event) for event in inputs),
        b''.join(PROBE.pack(signal) for signal in probes),
    ))


def dc_request(*, duration=40, limit=100, signals=0, edges=(), devices=(), inputs=(), probes=(),
               nodes=0, potentials=(), resistors=(), blockers=(), drivers=(), leds=(),
               request_id=0x123456789ABCDEF0, generation=17):
    return b''.join((
        REQUEST.pack(b'CNP2', request_id, generation, duration, limit, signals,
                     len(edges), len(devices), len(inputs), len(probes)),
        DC_COUNTS.pack(nodes, len(potentials), len(resistors), len(blockers), len(drivers), len(leds)),
        b''.join(MAPPED_EDGE.pack(*edge) for edge in edges),
        b''.join(POWERED_DEVICE.pack(*device) for device in devices),
        b''.join(INPUT.pack(*event) for event in inputs),
        b''.join(PROBE.pack(signal) for signal in probes),
        b''.join(POTENTIAL.pack(*potential) for potential in potentials),
        b''.join(POTENTIAL.pack(*resistor) for resistor in resistors),
        b''.join(PROBE.pack(node) for node in blockers),
        b''.join(DRIVER.pack(*driver) for driver in drivers),
        b''.join(LED.pack(*led) for led in leds),
    ))


def invoke(worker, frame):
    assert worker.is_absolute() and worker.is_file(), f'Native worker is missing: {worker}'
    return subprocess.run([str(worker)], input=frame, capture_output=True, timeout=15)


def reply(worker, body):
    return parse_reply(reply_body(worker, body), 0x123456789ABCDEF0, 17)


def reply_body(worker, body):
    result = invoke(worker, LENGTH.pack(len(body)) + body)
    assert result.returncode == 0, result.stderr
    size, = LENGTH.unpack_from(result.stdout)
    assert size == len(result.stdout) - LENGTH.size
    return result.stdout[LENGTH.size:]


def parse_reply(body, expected_request, expected_generation):
    magic, request_id, generation, status, count = RESPONSE.unpack_from(body)
    assert (magic, request_id, generation) == (b'CNP1', expected_request, expected_generation)
    samples = list(SAMPLE.iter_unpack(body[RESPONSE.size:]))
    assert len(samples) == count
    return status, samples


def parse_dc_reply(body, expected_request=0x123456789ABCDEF0, expected_generation=17):
    magic, request_id, generation, status, count = RESPONSE.unpack_from(body)
    assert (magic, request_id, generation) == (b'CNP2', expected_request, expected_generation)
    if status:
        assert count == 0 and len(body) == RESPONSE.size
        return status, [], [], []
    offset = RESPONSE.size + count * SAMPLE.size
    samples = list(SAMPLE.iter_unpack(body[RESPONSE.size:offset]))
    signal_count, = LENGTH.unpack_from(body, offset)
    offset += LENGTH.size
    pins = list(body[offset:offset + signal_count])
    offset += signal_count
    led_count, = LENGTH.unpack_from(body, offset)
    offset += LENGTH.size
    leds = list(LED_RESULT.iter_unpack(body[offset:]))
    assert len(leds) == led_count
    return status, samples, pins, leds


def test_delayed_74hc08_preserves_unknown_and_transport_delay(worker):
    body = request(signals=6, edges=[(0, 2), (1, 3), (4, 5)],
                   devices=[(0, 2, 3, 4, 8)], inputs=[(0, 0, 0), (0, 1, 1), (20, 0, 1)],
                   probes=[4, 5])
    assert reply(worker, body) == (0, [(4, 0, 2), (5, 0, 2), (4, 8, 0), (5, 8, 0),
                                       (4, 28, 1), (5, 28, 1)])


def test_zero_delay_settles_equal_time_changes_before_ordered_capture(worker):
    body = request(signals=4, devices=[(3, 0, 0, 1, 0), (0, 1, 2, 3, 0)],
                   inputs=[(0, 0, 0), (0, 2, 1), (5, 0, 1), (5, 0, 0), (6, 2, 0)],
                   probes=[3, 1])
    assert reply(worker, body) == (0, [(3, 0, 1), (1, 0, 1), (3, 6, 0)])


def test_or_and_xor_do_not_treat_unknown_as_a_binary_level(worker):
    body = request(signals=4, devices=[(1, 0, 1, 2, 0), (2, 0, 1, 3, 0)],
                   inputs=[(0, 0, 1), (2, 1, 1), (3, 0, 0)], probes=[2, 3])
    assert reply(worker, body) == (0, [(2, 0, 1), (3, 0, 2), (3, 2, 0), (3, 3, 1)])


def test_event_limit_counts_internal_feedback_without_partial_success(worker):
    body = request(limit=12, signals=2, edges=[(1, 0)], devices=[(3, 0, 0, 1, 0)],
                   inputs=[(0, 0, 0)], probes=[1])
    assert reply(worker, body) == (2, [])


@pytest.mark.parametrize('count', [100_000, 100_001])
def test_capture_limit_is_independent_from_event_limit(worker, count):
    body = request(duration=count, limit=200_000, signals=1,
                   inputs=[(i, 0, i % 2) for i in range(count)], probes=[0])
    status, samples = reply(worker, body)
    if count == 100_001:
        assert (status, samples) == (3, [])
    else:
        assert (status, len(samples)) == (0, 100_000)
        assert (samples[0], samples[-1]) == ((0, 0, 0), (0, 99_999, 1))


@pytest.mark.parametrize('body', [
    request(signals=1, edges=[(0, 1)]),
    request(signals=1, devices=[(4, 0, 0, 0, 0)]),
    request(signals=1, inputs=[(0, 0, 2)]),
    request(signals=1, inputs=[(41, 0, 1)]),
    request(signals=1, probes=[0, 0]),
    request(limit=1_000_001),
    request() + b'\x00',
])
def test_malformed_plan_has_no_samples(worker, body):
    assert reply(worker, body) == (1, [])


@pytest.mark.parametrize('frame', [
    LENGTH.pack(16 * 1024 * 1024 + 1),
    LENGTH.pack(REQUEST.size) + b'CNP1',
    LENGTH.pack(REQUEST.size) + request() + b'\x00',
])
def test_malformed_frame_is_rejected_without_response(worker, frame):
    result = invoke(worker, frame)
    assert result.returncode != 0
    assert result.stdout == b''


def test_empty_plan_returns_a_complete_empty_capture(worker):
    assert reply(worker, request()) == (0, [])


@contextmanager
def serve(worker):
    assert worker.is_absolute() and worker.is_file(), f'Native worker is missing: {worker}'
    with subprocess.Popen([str(worker), '--serve'], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        with ThreadPoolExecutor(max_workers=1) as reader:
            try:
                yield process, reader
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)


def read_frame(stream):
    prefix = stream.read(LENGTH.size)
    assert len(prefix) == LENGTH.size, 'Worker closed without a response frame.'
    size, = LENGTH.unpack(prefix)
    max_response = RESPONSE.size + 100_000 * SAMPLE.size + 2 * LENGTH.size + 131_072 * (1 + LED_RESULT.size)
    assert RESPONSE.size <= size <= max_response
    body = stream.read(size)
    assert len(body) == size
    return body


def exchange(process, reader, body, request_id, generation, parser=parse_reply):
    process.stdin.write(LENGTH.pack(len(body)) + body)
    process.stdin.flush()
    return parser(reader.submit(read_frame, process.stdout).result(timeout=5),
                  request_id, generation)


def test_serving_process_flushes_each_reply_and_isolates_request_state(worker):
    with serve(worker) as (process, reader):
        first = request(signals=1, inputs=[(0, 0, 1)], probes=[0], request_id=1, generation=2)
        invalid = request(signals=1, probes=[1], request_id=2, generation=3)
        last = request(signals=1, probes=[0], request_id=3, generation=4)
        assert exchange(process, reader, first, 1, 2) == (0, [(0, 0, 1)])
        assert exchange(process, reader, invalid, 2, 3) == (1, [])
        assert exchange(process, reader, last, 3, 4) == (0, [(0, 0, 2)])
        assert process.poll() is None
        process.stdin.close()
        assert process.wait(timeout=5) == 0
        assert process.stdout.read() == b''


@pytest.mark.parametrize('tail', [b'\x34\x00', LENGTH.pack(REQUEST.size) + b'CNP1'])
def test_serving_process_rejects_truncated_next_frame(worker, tail):
    with serve(worker) as (process, reader):
        assert exchange(process, reader, request(), 0x123456789ABCDEF0, 17) == (0, [])
        process.stdin.write(tail)
        process.stdin.close()
        assert process.wait(timeout=5) != 0
        assert process.stdout.read() == b''


def test_dc_edges_map_binary_levels_and_disabled_device_remains_unknown(worker):
    body = dc_request(signals=4, edges=[(0, 1, 1, 0)], devices=[(3, 1, 0, 2, 0, 0)],
                      inputs=[(0, 0, 0), (0, 3, 1), (10, 0, 1)], probes=[1, 2])
    assert parse_dc_reply(reply_body(worker, body)) == (
        0, [(1, 0, 1), (2, 0, 2), (1, 10, 0)], [1, 0, 2, 1], [],
    )


def test_disabled_dc_device_still_counts_toward_event_limit(worker):
    body = dc_request(limit=1, signals=2, devices=[(3, 0, 0, 1, 0, 0)],
                      inputs=[(0, 0, 0)], probes=[1])
    assert parse_dc_reply(reply_body(worker, body)) == (2, [], [], [])


def test_dc_unknown_level_is_never_remapped_as_a_binary_input(worker):
    body = dc_request(signals=4, edges=[(0, 1, 0, 2), (2, 3, 1, 1)],
                      devices=[(3, 1, 0, 2, 0, 1)], inputs=[(0, 0, 0), (10, 0, 1)],
                      probes=[1, 3])
    assert parse_dc_reply(reply_body(worker, body)) == (
        0, [(1, 0, 0), (3, 0, 1), (1, 10, 2), (3, 10, 2)], [1, 2, 2, 2], [],
    )


@pytest.mark.parametrize('input_events, expected_pins, status, current', [
    ([(0, 0, 1)], [1], 6, 3.0 / 330.0),
    ([], [2], 2, 0.0),
])
def test_dc_resistor_led_branch_uses_final_driven_level(worker, input_events, expected_pins, status, current):
    body = dc_request(signals=1, inputs=input_events, nodes=3, potentials=[(2, 20, 0.0)],
                      resistors=[(0, 1, 330.0)], drivers=[(0, 0, 20, 0.0, 5.0)],
                      leds=[(1, 2, 2.0, 0.02)])
    reply_status, samples, pins, leds = parse_dc_reply(reply_body(worker, body))
    assert (reply_status, samples, pins) == (0, [], expected_pins)
    assert len(leds) == 1 and leds[0][0] == status and leds[0][1] == pytest.approx(current)


@pytest.mark.parametrize('extra_source, status, current', [
    ((0, 20, 5.0), 6, 3.0 / 330.0),
    ((0, 21, 5.0), 1, 0.0),
    ((0, 20, 4.0), 1, 0.0),
])
def test_dc_equal_sources_coalesce_and_conflicts_remain_unsupported(worker, extra_source, status, current):
    body = dc_request(signals=1, nodes=3, potentials=[(0, 20, 5.0), extra_source, (2, 20, 0.0)],
                      resistors=[(0, 1, 330.0)], drivers=[(0, 0, 20, 0.0, 5.0)],
                      leds=[(1, 2, 2.0, 0.02)])
    reply_status, samples, pins, leds = parse_dc_reply(reply_body(worker, body))
    assert (reply_status, samples, pins) == (0, [], [2])
    assert len(leds) == 1 and leds[0][0] == status and leds[0][1] == pytest.approx(current)


def test_dc_shared_potentials_and_leds_stay_within_the_worker_deadline(worker):
    # Near the wire bounds, a scan of all sources for each trace is quadratic.
    count = 131_072
    body = dc_request(
        signals=1, inputs=[(0, 0, 1)], nodes=1,
        potentials=[(0, 1, 5.0)] * count, drivers=[(0, 0, 1, 0.0, 5.0)] * count,
        leds=[(0, 0, 2.0, 0.02)] * count,
    )
    assert parse_dc_reply(reply_body(worker, body)) == (0, [], [1], [(1, 0.0)] * count)


@pytest.mark.parametrize('body', [
    dc_request(signals=2, edges=[(0, 1, 3, 0)]),
    dc_request(signals=2, devices=[(3, 0, 0, 1, 0, 2)]),
    dc_request(nodes=1, potentials=[(1, 0, 0.0)]),
    dc_request(nodes=1, potentials=[(0, 0, float('nan'))]),
    dc_request(nodes=2, resistors=[(0, 1, 0.0)]),
    dc_request(nodes=1, blockers=[1]),
    dc_request(nodes=1, drivers=[(0, 0, 0, 0.0, 0.0)]),
    dc_request(nodes=1, leds=[(0, 0, -1.0, 0.02)]),
    dc_request(nodes=131_073),
    dc_request()[:-1],
    dc_request() + b'\x00',
])
def test_malformed_dc_plan_is_rejected_with_v2_status_and_no_suffix(worker, body):
    assert parse_dc_reply(reply_body(worker, body)) == (1, [], [], [])


def test_serving_process_accepts_both_protocol_versions_without_state_leak(worker):
    with serve(worker) as (process, reader):
        first = dc_request(signals=1, inputs=[(0, 0, 1)], request_id=1, generation=2)
        second = request(signals=1, probes=[0], request_id=2, generation=3)
        third = dc_request(signals=1, request_id=3, generation=4)
        assert exchange(process, reader, first, 1, 2, parse_dc_reply) == (0, [], [1], [])
        assert exchange(process, reader, second, 2, 3) == (0, [(0, 0, 2)])
        assert exchange(process, reader, third, 3, 4, parse_dc_reply) == (0, [], [2], [])
        process.stdin.close()
        assert process.wait(timeout=5) == 0
