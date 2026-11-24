# Backend execution

[Tiếng Việt](../../vi/architecture/backends.md) · [Documentation](../index.md)

Simulator owns simulated digital and bounded DC results and private CNP1/CNP2 frames. Contracts owns CircuitGraph and NCAP. Hardware validates and projects plans, checks the selected executable hash, supervises the worker, and encodes results. Remote owns release selection and orchestration.

[CIRNET Lab-First](https://github.com/cirnetlab/cirnet-remote-next/blob/master/docs/cirnet-architecture-lab-first-en.md) defines the target execution stages and acceptance gates.

`cirnet-simulator-worker --protocols` lists CNP1 and CNP2. The supervised process runs with `--serve` to handle requests sequentially over stdin/stdout. One-shot mode reads one frame followed by EOF. The frame starts with a little-endian 32-bit length and carries a payload of up to 16 MiB. A request contains the protocol tag, request and generation IDs, duration in nanoseconds, event limit and record counts. The reply echoes the tag and both IDs.

| Protocol | Input | Successful response |
| --- | --- | --- |
| CNP1 | Directed edges, ideal gates, input events and probes | Ordered probe samples |
| CNP2 | Digital records with mapped edges and gate enable flags, plus DC nodes, potentials, resistors, blockers, drivers and LEDs | Ordered probe samples, final pin levels and LED status/current pairs |

Floating digital inputs remain unknown. Event and sample budgets are independent, and a failure produces no partial capture. CNP2 covers supported powered gates and the bounded source/resistor/LED model. Hardware owns validation, cancellation and safe Stop. The reserved [ngspice backend](ngspice-integration.md) remains `UNAVAILABLE`.
