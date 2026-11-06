"""CNP2 projection of the validated bounded DC model and its result."""

from dataclasses import dataclass
from math import isfinite
from struct import Struct

from contracts.execution_profiles import get_execution_part

from .engine import SimulationError


_COUNT = Struct('<I')
_POTENTIAL = Struct('<IId')
_RESISTOR = Struct('<IId')
_DRIVER = Struct('<IIIdd')
_LED = Struct('<IIdd')
_LED_RESULT = Struct('<Bd')
_LEVELS = (0, 1, 'X')
_IDEAL_ESTIMATE = 'Ideal constant-drop series DC estimate; excludes output impedance, transistor and transient behavior.'
_LED_STATES = (
    ('OFF', 'Open circuit or no forward bias.'),
    ('UNSUPPORTED', 'Only one LED with a series resistor and one ideal DC reference is supported; branching/other analog needs a solver.'),
    ('UNKNOWN', 'The powered digital output driving this DC branch is unknown.'),
    ('UNSUPPORTED', 'Independent floating DC references cannot be compared.'),
    ('UNSUPPORTED', 'DC LED subset is limited to 6 V.'),
    ('UNSUPPORTED', 'The supported LED subset requires a series resistor.'),
    ('ON', _IDEAL_ESTIMATE),
    ('FAULT', _IDEAL_ESTIMATE),
)


@dataclass(frozen=True)
class PhysicalProjection:
    counts: tuple
    wire: bytes
    fixed_sources: frozenset
    base_states: tuple
    leds: tuple

    def result(self, reply, endpoints):
        signals = len(endpoints)
        led_count_offset = _COUNT.size + signals
        led_start = led_count_offset + _COUNT.size
        if (len(reply) != led_start + len(self.leds) * _LED_RESULT.size
                or _COUNT.unpack_from(reply)[0] != signals
                or _COUNT.unpack_from(reply, led_count_offset)[0] != len(self.leds)):
            raise SimulationError('PROTOCOL_MISMATCH')
        levels = reply[_COUNT.size:led_count_offset]
        if any(level >= len(_LEVELS) for level in levels):
            raise SimulationError('PROTOCOL_MISMATCH')
        pin_values = {name: _LEVELS[level] for (name, _), level in zip(endpoints, levels, strict=True)}

        states = {name: dict(state) for name, state in self.base_states}
        for (name, maximum), (status, current) in zip(self.leds, _LED_RESULT.iter_unpack(reply[led_start:]), strict=True):
            if status >= len(_LED_STATES) or not isfinite(current):
                raise SimulationError('PROTOCOL_MISMATCH')
            if ((status < 6 and current != 0) or (status == 6 and not 0 <= current <= maximum)
                    or (status == 7 and current <= maximum)):
                raise SimulationError('PROTOCOL_MISMATCH')
            state, reason = _LED_STATES[status]
            result = {'state': state, 'model': 'bounded-dc-series', 'reason': reason}
            if status >= 6:
                result['currentAmps'] = current
            states[name] = result
        diagnostics = sorted({state['reason'] for state in states.values()
                              if state['state'] in ('UNSUPPORTED', 'FAULT', 'UNKNOWN', 'UNPOWERED')
                              and 'reason' in state})
        return {'device_states': states, 'pin_values': pin_values, 'diagnostics': diagnostics}


def project_physical(circuit, signal_ids):
    """Freeze the structural and nominal electrical data passed to the worker."""
    nodes = {name: index for index, name in enumerate(sorted(set(circuit.endpoint_nodes.values())))}
    endpoints = {name: nodes[node] for name, node in circuit.endpoint_nodes.items()}
    references = {}
    potentials = [(nodes[node], references.setdefault(ref, len(references)), voltage)
                  for node, values in circuit.potentials.items() for ref, voltage in values]
    states = {name: dict(state) for name, state in circuit.device_states.items()}
    resistors, drivers, leds = [], [], []
    blockers, fixed_sources = set(), set()
    for module in circuit.modules:
        name = module['id']
        kind = module['type']
        properties = module.get('properties', {})
        part = get_execution_part(kind)
        model = part['simulation']
        pins = [f"{name}.{pin['id']}" for pin in part['package']['pins']]
        if model['model'] == 'hc08-powered':
            if name in circuit.gate_references:
                ref, low, voltage = circuit.gate_references[name]
                ref_id = references.setdefault(ref, len(references))
                for gate in model['gates']:
                    signal = f"{name}.{gate['output']}"
                    drivers.append((signal_ids[signal], endpoints[signal], ref_id, low, voltage))
        elif model['model'] == 'resistor-dc':
            resistance = properties.get('resistanceOhms', model.get('defaultOhms', 330))
            resistors.append((endpoints[pins[0]], endpoints[pins[1]], resistance))
            states[name] = {'state': 'PASSIVE', 'model': 'bounded-dc-series', 'resistanceOhms': resistance}
        elif model['status'] == 'unsupported':
            states[name] = {'state': 'UNSUPPORTED', 'model': model['model'],
                            'reason': model.get('reason', 'Placement and wiring only; simulation unavailable.')}
            blockers.update(endpoints[pin] for pin in pins)
        elif model['model'] == 'dc-source':
            fixed_sources.update(pins)
        elif model['model'] == 'led-dc':
            settings = get_execution_part(kind, properties)['simulation']
            leds.append((name, endpoints[f'{name}.A'], endpoints[f'{name}.K'],
                         settings.get('forwardVoltage', 2), settings.get('maxCurrentAmps', .02)))
        else:
            states[name] = {'state': 'PASSIVE', 'model': model['model'],
                            'reason': 'Only declared conductive contact pairs are modeled.'}
    sections = (
        (_POTENTIAL, potentials), (_RESISTOR, resistors), (_COUNT, [(node,) for node in sorted(blockers)]),
        (_DRIVER, drivers), (_LED, [led[1:] for led in leds]),
    )
    counts = (len(nodes), *(len(rows) for _, rows in sections))
    wire = b''.join(codec.pack(*record) for codec, rows in sections for record in rows)
    return PhysicalProjection(
        counts, wire, frozenset(fixed_sources), tuple((name, tuple(state.items())) for name, state in states.items()),
        tuple((name, maximum) for name, _, _, _, maximum in leds),
    )
