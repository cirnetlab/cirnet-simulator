# Planned ngspice integration

[Tiếng Việt](../../vi/architecture/ngspice-integration.md) · [Backend selection](backends.md)

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
