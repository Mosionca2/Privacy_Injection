# ReproLLM case study: a recorded local-model privacy experiment

This agent-assisted study recorded genuine GPU inference with ReproLLM 0.6.1. The public evidence includes 3,072 held-out generations, a 768-generation fresh repeat, calibration and development runs, and a separate corrected-declaration validation. See [the report](../REPORT.md) and [the execution ledger](../reports/completion.json). One study is not multiple independent users or long-term deployment evidence.

## Reusable workflow

1. Freeze the scientific code, generated truth, model content identity, software versions and batching policy before formal outcomes. Confirm that locally supplied model files match the published identity. A replacement model needs a new protocol.
2. Create an independent workspace per concurrently running condition. `privacy_study.record.workspace` prepares relative `assets/model` entries. Existing weights can be hard-linked on a supporting shared filesystem. ReproLLM rejects symlinks that resolve outside the project boundary; do not weaken that boundary.
3. Run `tools/complete_recording_metadata.py --workspace <workspace>` to declare the actual boundary/reminder/line-label flags, Python version and exact installed runtime packages. These annotations do not change the frozen prompts.
4. In that workspace, add the `inference`, `evaluation` and `privacy` profiles and accepted custom-field rules. Create an offline lock. Use `--hash-large-files` when complete weight hashing is required; otherwise describe the evidence as partial and verify weights independently.
5. Commit the condition manifest, lock, runtime declarations and project rules before inference. Preserve that commit. Model assets, raw working output and credentials stay outside version control.
6. Execute a real command through ReproLLM, for example `reprollm run --capture-output -- python -m privacy_study.run --model assets/model --defense D0 --split test --batch-size 64`. A formal run requires the matching frozen protocol and all held-out cases.
7. Inspect the actual child exit code, warnings and case coverage. Run audit, compare two real condition records, and export the explicitly selected run. Do not equate `status=completed` with exit code zero, an audit result with scientific success, or an empty resumed job with a new experiment.
8. Publish reviewed evidence and independent paired statistics. Document capture limitations and preserve unsuccessful findings rather than editing old records into a green state.

## What was useful

Actual run IDs link rows to captures; accepted CLI bindings detected intentional conflicts; failure exits and failed launches remained visible; explicit historical exports and semantic diff helped inspect which state was recorded. Audit also exposed our incomplete mechanism declaration. The corrected workflow was verified with four new 64-response GPU runs and clean committed input states.

## Boundaries observed

- `lock --check` does not rehash local model files; it checks manifest and project-rule freshness.
- Large local weights are not fully hashed by default.
- A present project field may pass its presence rule while a contradictory runtime observation correctly fails `consistency.custom_fields`.
- `NONE` is a real drift severity; omitting `--fail-on` makes diff informational.
- Capture evidence is collected mainly after the child exits. Keep scientific inputs immutable and isolate concurrent manifests.
- The selected synthetic secret patterns were redacted in tool-owned persistence. This is not a general guarantee for arbitrary secrets or user-created output files.

No confirmed upstream defect was inferred from these cases. The resulting documentation proposal is now submitted as [Docs Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11) and [Draft PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12) from [the research owner's Fork](https://github.com/Mosionca2/ReproLLM). The PR contains only the isolated-recording tutorial, navigation and changelog. Maintainer placement/content review is pending.


## Second-snapshot follow-up

A separately frozen local Qwen3-1.7B snapshot completed another 3,072 formal generations and a 768-response immediate fresh repeat. Its upstream revision and original-versus-modified status remain unverified; evidence binds exact local fingerprints. This is follow-up work within the same agent-assisted study, not an independent adopter or long-term deployment. Full records and controls are in [the second-model report](../reports/extensions/qwen3-1.7b/REPORT.md).

Development calibration showed that changing batch size altered a few decoded greedy outputs and scores, despite the shared seed and decoding mode. The predeclared selection rule retained batch16. ReproLLM captured the actual batch binding and distinct configuration records; it does not certify numerical equivalence. Every extension run used complete committed declarations, full local-weight hashing and an isolated workspace, with zero CRITICAL audit failures. The original primary-run audit findings remain intact. Public diff references and device identifiers are reviewed publication copies; original records stay private.


## Submitted upstream documentation contribution

The [Fork](https://github.com/Mosionca2/ReproLLM) branch `m9/t11-isolated-recording-recipe` supplies the concrete tutorial in [Draft PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12), linked to [Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11). Proposed placement and content remain under maintainer review; no acceptance or merge is asserted. The contribution does not modify product behavior or publish private research documents.

Local checks recorded two independent CPU fixture conditions with released 0.6.1 (run schema 1) and two with source 0.7.0 at `8772904` (schema 2). Both check declared/observed condition and batch values, a child configuration-consumption witness, explicit cross-workspace diff, stale-lock exit after a declaration edit and selected historical export without rewriting run bytes. Five tutorial links/anchors and two navigation links pass. These four CPU recordings are separate from the 10,496 scientific model generations. The existing installed environment was not changed.

Per upstream's documentation-only validation exception, product full-suite and five-project/resource gates are NOT_APPLICABLE, not passed. [The evidence summary](../reports/reprollm-contribution-validation.json) retains version boundaries and the initial fixture-input correction. [Upstream CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/41445173597) currently reports `action_required`; local document checks do not replace that CI result.
