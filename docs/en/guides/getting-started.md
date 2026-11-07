# Getting started with CIRNET Simulator

English · [Tiếng Việt](../../vi/guides/getting-started.md)

[Documentation index](../index.md)

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

See [model scope and limits](../architecture/backends.md#model-scope-and-limits).

Remote owns REST previews and persistence. Hardware owns worker pools, station sessions and Stop/reset invalidation. See [backend selection](../architecture/backends.md) and the [pinned signal-domain reference](https://github.com/cirnetlab/cirnet-remote/blob/13a35145b6d15644c7be10d95a5410bf69e11867/docs/en/architecture/signal-domains-and-simulation.md).
