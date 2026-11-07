# ngspice research inputs

[Tiếng Việt](../../vi/architecture/ngspice-integration.md) · [Backend selection](backends.md)

The reserved analog and mixed-signal selector `ngspice` remains
`UNAVAILABLE`. The Stage 1 candidate uses the CIRNET C++ worker for digital
and bounded DC models. The research checked upstream tag
`ngspice-46` and source archive `ngspice-46.tar.gz`. The downloaded upstream
archive matched the SHA-256 from the pinned Homebrew recipe
`a0d1699af1940b06649276dcd6ff5a566c8c0cad01b2f7b5e99dedbb4d64c19b`.
Source and model input digests are **VERIFIED**. Binary build, model pack
hashing and review of the exact distribution are **NOT RUN**.
[Upstream source archive](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/46/ngspice-46.tar.gz/download) ·
[Upstream release inventory](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/46/) ·
[Pinned Homebrew recipe](https://github.com/Homebrew/homebrew-core/blob/539f6abfdfdff8af39757bc100dfbce1db0c5618/Formula/lib/libngspice.rb#L3-L5)

The verified XSPICE model inputs are under `src/xspice/icm/digital/`
in that archive. Each digest covers `cfunc.mod`, a NUL byte and `ifspec.ifs` in
that order. The built code-model library needs its own digest.

| Model input | SHA-256 |
| --- | --- |
| `d_and` | `f77686eed70f915eb3ce10030435b5462285ff7d1659e59f660698e77bea1097` |
| `adc_bridge` | `0b9d31f3de5d4ea3e458a1d7e1d2e1681fbe4a68d1609684458a87fd66115229` |
| `dac_bridge` | `900462caf6e1826eeb25f81c09f0e16a3c7fcc5d3238711561d46c95060d68d8` |

## References

[ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf) ·
[Upstream COPYING](https://sourceforge.net/p/ngspice/ngspice/ci/master/tree/COPYING) ·
[Shared library interface](https://ngspice.sourceforge.io/shared.html) ·
[XSPICE overview](https://ngspice.sourceforge.io/xspiceusage.html) ·
[Original integration proposal](https://github.com/cirnetlab/cirnet-simulator/blob/0831ec64459a4880da9d361dae084f1bf857d853/docs/en/architecture/ngspice-integration.md)
