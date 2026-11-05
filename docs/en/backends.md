# Backend selection and execution

English · [Tiếng Việt](../vi/backends.md)

[Documentation index](index.md)

`CIRNET_SIMULATION_BACKEND` selects the built-in adapter at application or station creation. The default is `legacy`, which handles existing digital and bounded DC models. `ngspice` is reserved and reports `UNAVAILABLE`. It produces no samples and launches no native executable. The canonical setting takes precedence over `NETCIRCUIT_SIMULATION_BACKEND`. Graph properties cannot choose an adapter.

Application code resolves the ID once with `cirnet_sim.backends.select_backend_id()`. Pass it to `compile_graph(graph, backend_id=...)` and `preview_physical_graph(graph, backend_id=...)`. Check availability before execution. A compiled plan carries the backend ID, adapter version and plan format. The worker’s `run_plan(plan, configuration, vectors, clock_config, inputs)` resolves this frozen identity. Missing or mismatched providers fail rather than falling back. Hardware admission uses the read-only `.directions` mapping.

Trusted application code can supply an explicit `BackendRegistry` of providers. Each provider publishes a frozen `BackendDescriptor` and implements compile, execute and preview. Compile must return a serializable payload with execution settings and directions. Spawned workers need their own equivalent registry. The current Hardware composition uses built-in providers. Simulator does not discover providers from module paths or graph content. See the [backend source](../../cirnet_sim/backends.py).

For rollback within this release, select `legacy`. To restore an earlier artifact set, restore matching Simulator, Contracts and consumer pins. Resolve historic artifacts by SHA256, even when their version numbers match. The change does not require rewriting stored graphs or captures.
