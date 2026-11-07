# Getting started with CIRNET Simulator

English · [Tiếng Việt](../vi/getting-started.md)

[Documentation index](index.md)

The current source builds `cirnet-simulator==0.1.2` for Python 3.11 or later.
For the published CIRNET 0.1.4 system profile, install the Simulator and
`cirnet-contracts==0.1.2` wheels by exact digest from the [release manifest](https://github.com/cirnetlab/cirnet-remote/blob/38aea6120920f48cea817827ac2277cce4bef25e/integration/release-set.json)
in a fresh environment. This profile uses `legacy`. The canonical import is
`cirnet_sim`. The `netcircuit_sim` shim resolves to the same modules and classes
for older callers.

After installing the wheels, run this check from outside the checkout. It prints `1` for the two-input AND primitive.

~~~sh
python -I -B -c "from cirnet_sim import and2; print(and2(1, 1))"
~~~

The event simulator accepts supported CircuitGraph 1.0, 1.1 and 1.2 graphs. The built-in models cover digital switches, logic gates, LEDs and probes, clocks, and the bounded powered HC08/source/resistor/LED DC subset. Board and instrument visuals do not create electrical nets. Unknown models report `UNEXECUTABLE`. Analog, SPICE and mixed-signal execution remain `UNAVAILABLE`.

Time is counted in integer nanoseconds. The 8 ns default digital delay is an educational model value. Floating inputs stay `X`. Captures record settled 0/1/X transitions on at most four requested probes. Default bounds are 1 ms, 100,000 scheduled events and 100,000 captured samples. The configurable scheduling limit reaches 1,000,000 events. The capture limit is independent. Exceeding either budget fails the run without truncating results.

Remote owns REST previews and persistence. Hardware owns worker pools, station sessions and Stop/reset invalidation. See [backend selection](backends.md) and the [pinned signal-domain reference](https://github.com/cirnetlab/cirnet-remote/blob/13a35145b6d15644c7be10d95a5410bf69e11867/docs/en/architecture/signal-domains-and-simulation.md).
