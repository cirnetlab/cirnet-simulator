# Backend selection and execution

English · [Tiếng Việt](../vi/backends.md)

[Documentation index](index.md)

`CIRNET_SIMULATION_BACKEND` selects the built-in adapter at application or station creation. The default is `legacy`, which handles existing digital and bounded DC models. `ngspice` is reserved and reports `UNAVAILABLE`. It produces no samples and launches no native executable. The canonical setting takes precedence over `NETCIRCUIT_SIMULATION_BACKEND`. Graph properties cannot choose an adapter.

Application code resolves the ID once with `cirnet_sim.backends.select_backend_id()`. Pass it to `compile_graph(graph, backend_id=...)` and `preview_physical_graph(graph, backend_id=...)`. Check availability before execution. A compiled plan carries the backend ID, adapter version and plan format. The worker’s `run_plan(plan, configuration, vectors, clock_config, inputs)` resolves this frozen identity. Missing or mismatched providers fail rather than falling back. Hardware admission uses the read-only `.directions` mapping.

Trusted application code can supply an explicit `BackendRegistry` of providers. Each provider publishes a frozen `BackendDescriptor` and implements compile, execute and preview. Compile must return a serializable payload with execution settings and directions. Spawned workers need their own equivalent registry. The current Hardware composition uses built-in providers. Simulator does not discover providers from module paths or graph content. See the [backend source](../../cirnet_sim/backends.py).

For rollback within this release, select `legacy`. To restore an earlier artifact set, restore matching Simulator, Contracts and consumer pins. Resolve historic artifacts by SHA256, even when their version numbers match. The change does not require rewriting stored graphs or captures.

## Experimental C++ worker

To select this adapter in Remote and Hardware, set `CIRNET_SIMULATION_BACKEND=cpp`, `CIRNET_SIM_CPP_WORKER` to the absolute executable path, and `CIRNET_SIM_CPP_WORKER_SHA256` to the digest from the selected artifact. The host verifies the executable before launching it. Invalid or missing pins make `cpp` unavailable. An explicit `BackendRegistry` can also take a `CppBackend` from `cirnet_sim.cpp_backend`.

Run and preview maintain separate pools. The configured Run pool follows `CIRNET_SIMULATION_WORKERS`, defaults to four jobs and uses a 10-second IPC deadline. Preview admits one job with a two-second IPC deadline. Admission is immediate and rejects work when all slots are busy. Each lane reuses its own process. Timeout, cancellation, worker exit or an invalid reply discards that process. Hardware waits for a cancelled Run to finish cleanup before acknowledging safe Stop or reset. Switch the services back to `legacy` after stopping active work and restarting the processes.

### Private worker protocol

The worker runs as `cirnet-simulator-worker --serve` and handles one request at a time over stdin/stdout. The one-shot CLI accepts one frame followed by EOF. A frame consists of a little-endian 32-bit byte count and a payload of at most 16 MiB. Each request starts with a four-byte protocol tag, 64-bit request and generation IDs, the duration in nanoseconds and six 32-bit fields for the event limit and record counts. The reply echoes the tag and both IDs. The adapter verifies these fields before accepting any results.

| Tag | Request body following the common header | Successful reply following the common header |
| --- | --- | --- |
| `CNP1` | Directed edges, ideal gates, input events and probes | Ordered probe samples |
| `CNP2` | Six DC record counts, directed edges with mapped input levels, gates with enable flags, events, probes, source potentials, resistors, blocked nodes, output drivers and LEDs | Ordered probe samples, final pin levels and one status/current pair per LED |

The digital event loop uses 0, 1 and unknown. Preview sets gate delays to zero and holds clocks at their initial level. CNP2 covers the bounded DC series model and powered gates. The Python transition adapter validates and projects graphs and formats results. Contracts encodes the public NCAP payload at the Hardware boundary.

The worker checks event and sample limits and uses an operating-system memory limit of 256 MiB per process. The default release profile selects `legacy`.

Build and install the C++20 executable in an allocator-owned external directory. These commands use Visual Studio 2022 Build Tools on Windows.

```powershell
cmake -S . -B "$env:CIRNET_ARTIFACTS_SESSION/cpp" -G "Visual Studio 17 2022" -A x64
cmake --build "$env:CIRNET_ARTIFACTS_SESSION/cpp" --config Release
cmake --install "$env:CIRNET_ARTIFACTS_SESSION/cpp" --config Release --prefix "$env:CIRNET_ARTIFACTS_SESSION/cpp-install"
$env:CIRNET_TEST_CPP_WORKER = "$env:CIRNET_ARTIFACTS_SESSION/cpp-install/bin/cirnet-simulator-worker.exe"
python -B -m pytest -q tests/test_cpp_worker.py --basetemp "$env:CIRNET_ARTIFACTS_SESSION/pytest-cpp-worker"
```

## Planned ngspice integration

Use upstream ngspice source for a separate, opt-in analog and mixed-signal
backend. The Stage 1 candidate uses the CIRNET C++ worker for the existing digital and bounded
DC models. The proposed first reproducible experiment uses upstream tag
`ngspice-46` and source archive `ngspice-46.tar.gz`. The downloaded upstream
archive matched the SHA-256 from the pinned Homebrew recipe
`a0d1699af1940b06649276dcd6ff5a566c8c0cad01b2f7b5e99dedbb4d64c19b`.
Source and model input digests are **VERIFIED**. Binary build, model pack
hashing and review of the exact distribution are **NOT RUN**.
[Upstream source archive](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/46/ngspice-46.tar.gz/download) ·
[Upstream release inventory](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/46/) ·
[Pinned Homebrew recipe](https://github.com/Homebrew/homebrew-core/blob/539f6abfdfdff8af39757bc100dfbce1db0c5618/Formula/lib/libngspice.rb#L3-L5)

For the first RC test, use ngspice's built-in R, C and voltage source.
Pin the first XSPICE model inputs from `src/xspice/icm/digital/` in that
archive. Each digest covers `cfunc.mod`, a NUL byte and `ifspec.ifs` in
that order. The built code-model library needs its own digest.

| Model input | SHA-256 |
| --- | --- |
| `d_and` | `f77686eed70f915eb3ce10030435b5462285ff7d1659e59f660698e77bea1097` |
| `adc_bridge` | `0b9d31f3de5d4ea3e458a1d7e1d2e1681fbe4a68d1609684458a87fd66115229` |
| `dac_bridge` | `900462caf6e1826eeb25f81c09f0e16a3c7fcc5d3238711561d46c95060d68d8` |

1. **Build and verify the inputs.** Record the source revision and archive
   digest, patches, target, compiler and build options. Use
   `--with-ngshared --enable-xspice --disable-debug` for the first
   configure-based shared build. Pin the SHA-256 of each executable or shared library and
   each code-model library or model pack. Record SPDX identifiers or license
   references per component, with the license texts and notices for the exact
   files distributed. The release's `COPYING` uses modified BSD for much
   of the source and lists exceptions including the XSPICE table model.
   Audit every component actually included in the selected build.
   [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf) ·
   [Upstream COPYING](https://sourceforge.net/p/ngspice/ngspice/ci/master/tree/COPYING)
2. **Choose the isolation boundary.** Start with a pinned headless ngspice
   child with controlled inputs and outputs, resource limits, and a host
   deadline. Evaluate the shared C library inside a dedicated worker when
   callbacks are needed for in-memory netlists, solver output or XSPICE
   events. The shared API exposes `ngSpice_Circ`, data and event callbacks,
   and `ngSpice_Init_Sync` for external sources and transient-step
   synchronization. Direct embedding would share a process with the caller.
   Keep the process boundary around either integration and verify cooperative
   Stop, forced termination and reaping on deadline, reset, and rejection of
   late results. `bg_halt` may take time to take effect.
   [Shared library interface](https://ngspice.sourceforge.io/shared.html) ·
   [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf)
3. **Generate netlists from validated graphs.** Allow only reviewed component
   and model mappings from the versioned catalog, bounded parameters with
   explicit units, generated node names and explicit electrical references.
   The adapter owns simulator directives and model paths. Reject user-supplied
   netlist text, control commands, includes and model-library paths. Bound
   solver time, result size and channel count before launching a job.
4. **Compare simulation and capture semantics.** Test a DC operating point,
   an RC transient, ideal digital gates and clocks, and mixed analog/digital
   circuits with explicit A/D and D/A bridges. Compare digital event order,
   simultaneous changes, integer nanosecond timestamps, delays and 0/1/X
   against the C++ reference where the models overlap. Document the mapping
   from XSPICE's logic states and drive strengths, including unknown and
   high-impedance cases. Keep digital NCAP v1 compatible. For analog capture,
   retain the solver time axis and explicitly define sampling before using a
   fixed-rate format. Record units, simulation provenance, model identity and
   incomplete or invalid results.
   [XSPICE overview](https://ngspice.sourceforge.io/xspiceusage.html) ·
   [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf)
5. **Advertise only tested capabilities.** Verify reproducible artifact
   selection, supported models, capture compatibility, convergence failure,
   timeout, worker crash, and rollback to the existing backend. Enable
   capabilities only for the exact verified platform, worker and model pack.
   Until that gate passes, `ngspice` reports `UNAVAILABLE`.
