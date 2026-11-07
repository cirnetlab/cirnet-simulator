# Write and maintain CIRNET Simulator documentation

[Tiếng Việt](../../vi/contributing/writing-documentation.md) · [Documentation](../index.md)

Follow the [repository instructions](../../../AGENTS.md) and the
[shared CIRNET conventions](https://github.com/cirnetlab/cirnet-remote/blob/40849a3478b20f31f3882f36852b47a688952516/docs/en/contributing/writing-documentation.md).
Keep the root README in English with links to both language indexes. Give
current English and Vietnamese pages the same relative path and update
them together. Preserve commands, identifiers, versions, limits and
capability status in both languages.

Keep Simulator models, backend selection and the private worker protocol here. Contracts owns the schemas and catalogs. Hardware owns station lifecycles and Remote owns REST orchestration. Keep the released Python profile separate from the opt-in native worker and preserve unavailable-model behavior.

Keep each task plan under `.superpowers/plans/`. Keep its matching spec,
acceptance criteria and progress checklist under `.superpowers/specs/`.
Both paths are ignored here. Use `- [ ]` for open items and `- [x]` only
after verification. After verifying the change, update the paired pages
and the [release changelog](../../changelogs/README.md).

Preserve dated records at their existing paths and list them in both
[history indexes](../history/index.md). Cite the exact Git revision for
superseded plans or specs. Keep raw logs and build output in an owned
external session. Before handoff, compare the language pair, verify
links and anchors, and review Git diff and ignored output.
[Verification guide](verification.md)
