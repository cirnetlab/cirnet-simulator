# Backend selection and execution

English · [Tiếng Việt](../../vi/architecture/backends.md)

[Documentation index](../index.md)

`CIRNET_SIMULATION_BACKEND` selects the built-in adapter at application or
station creation. It takes precedence over `NETCIRCUIT_SIMULATION_BACKEND`.
Graph properties cannot choose an adapter.

| Selector | Availability |
| --- | --- |
| `legacy` | Default. Supports deterministic digital and bounded DC models. |
| `cpp` | Opt-in in current source. Requires a separately selected C++ worker and its SHA-256. |
| `ngspice` | Reserved and `UNAVAILABLE`. Reports zero channels and produces no samples. |

The [published CIRNET 0.1.4 profile](https://github.com/cirnetlab/cirnet-remote/blob/38aea6120920f48cea817827ac2277cce4bef25e/integration/release-set.json) selects `legacy`. The separate
Stage 1 r7 combination passed Gate 1 on Windows x64 with `cpp`. SPICE and
physical HIL remain `NOT RUN` for that candidate.
[Gate 1 decision](https://github.com/cirnetlab/cirnet-remote/blob/13a35145b6d15644c7be10d95a5410bf69e11867/docs/en/architecture/native-migration.md#gate-1-decision-for-windows-x64)

Application code resolves the ID once with `cirnet_sim.backends.select_backend_id()`. Pass it to `compile_graph(graph, backend_id=...)` and `preview_physical_graph(graph, backend_id=...)`. Check availability before execution. A compiled plan carries the backend ID, adapter version and plan format. The worker’s `run_plan(plan, configuration, vectors, clock_config, inputs)` resolves this frozen identity. Missing or mismatched providers fail rather than falling back. Hardware admission uses the read-only `.directions` mapping.

Trusted application code can supply an explicit `BackendRegistry` of providers. Each provider publishes a frozen `BackendDescriptor` and implements compile, execute and preview. Compile must return a serializable payload with execution settings and directions. Spawned workers need their own equivalent registry. The current Hardware composition uses built-in providers. Simulator does not discover providers from module paths or graph content. See the [backend source](../../../cirnet_sim/backends.py).

For rollback within this release, select `legacy`. To restore an earlier artifact set, restore matching Simulator, Contracts and consumer pins. Resolve historic artifacts by SHA256, even when their version numbers match. The change does not require rewriting stored graphs or captures.

## Experimental C++ worker

To select this adapter in Remote and Hardware, set
`CIRNET_SIMULATION_BACKEND=cpp`, `CIRNET_SIM_CPP_WORKER` to the absolute
executable path, and `CIRNET_SIM_CPP_WORKER_SHA256` to the digest from the
selected artifact. Both pins are required for registration. Malformed pins
fail configuration. Unreadable files and digest mismatches fail worker
startup. Trusted application code can also add `CppBackend` from
`cirnet_sim.cpp_backend` to an explicit `BackendRegistry`.

Run and preview maintain separate pools. The configured Run pool follows `CIRNET_SIMULATION_WORKERS`, defaults to four jobs and uses a 10-second IPC deadline. Preview admits one job with a two-second IPC deadline. Admission is immediate and rejects work when all slots are busy. Each lane reuses its own process. Timeout, cancellation, worker exit or an invalid reply discards that process. Hardware waits for a cancelled Run to finish cleanup before acknowledging safe Stop or reset. Switch the services back to `legacy` after stopping active work and restarting the processes.

### Private worker protocol

The worker runs as `cirnet-simulator-worker --serve` and handles one request at a time over stdin/stdout. The one-shot CLI accepts one frame followed by EOF. A frame consists of a little-endian 32-bit byte count and a payload of at most 16 MiB. Each request starts with a four-byte protocol tag, 64-bit request and generation IDs, the duration in nanoseconds and six 32-bit fields for the event limit and record counts. The reply echoes the tag and both IDs. The adapter verifies these fields before accepting any results.

| Tag | Request body following the common header | Successful reply following the common header |
| --- | --- | --- |
| `CNP1` | Directed edges, ideal gates, input events and probes | Ordered probe samples |
| `CNP2` | Six DC record counts, directed edges with mapped input levels, gates with enable flags, events, probes, source potentials, resistors, blocked nodes, output drivers and LEDs | Ordered probe samples, final pin levels and one status/current pair per LED |

The digital event loop uses 0, 1 and unknown. Preview sets gate delays to zero and holds clocks at their initial level. CNP2 covers the bounded DC series model and powered gates. The Python transition adapter validates and projects graphs and formats results. Contracts encodes the public NCAP payload at the Hardware boundary.

The worker checks event and sample limits and uses an operating-system memory limit of 256 MiB per process.

See the [C++ worker build and verification steps](../contributing/verification.md#verify-the-c-worker).

## Model scope and limits

The event simulator accepts supported CircuitGraph 1.0, 1.1 and 1.2 graphs. The built-in models cover digital switches, logic gates, LEDs and probes, clocks, and the bounded powered HC08/source/resistor/LED DC subset. Board and instrument visuals do not create electrical nets. Unknown models report `UNEXECUTABLE`. Analog, SPICE and mixed-signal execution remain `UNAVAILABLE`.

Time is counted in integer nanoseconds. The 8 ns default digital delay is an educational model value. Floating inputs stay `X`. Captures record settled 0/1/X transitions on at most four requested probes. Default bounds are 1 ms, 100,000 scheduled events and 100,000 captured samples. The configurable scheduling limit reaches 1,000,000 events. The capture limit is independent. Exceeding either budget fails the run without truncating results.

## Reserved ngspice selector

The analog and mixed-signal backend remains `UNAVAILABLE`. The
[ngspice research record](ngspice-integration.md) identifies the verified
source and model inputs and the scope of the checks.
