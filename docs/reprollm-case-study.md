# ReproLLM case study: a recorded local-model privacy experiment

This agent-assisted study recorded genuine GPU inference with ReproLLM 0.6.1. The public evidence includes 3,072 held-out generations, a 768-generation fresh repeat, calibration and development runs, and a separate corrected-declaration validation. See [the report](../REPORT.md) and [the execution ledger](../reports/completion.json). One study is not multiple independent users or long-term deployment evidence.

## Reusable workflow

1. Freeze the scientific code, generated truth, model content identity, software versions and batching policy before formal outcomes. Confirm that locally supplied model files match the published identity. A replacement model needs a new protocol.
2. Create an independent workspace per concurrently running condition. For new model studies, `tools/prepare_extension.py` prepares relative `assets/model` entries and supports source checkouts with existing recording metadata. The frozen original `privacy_study.record.workspace` assumes an uninitialized source checkout. Existing weights can be hard-linked on a supporting shared filesystem. ReproLLM rejects symlinks that resolve outside the project boundary; do not weaken that boundary.
3. Run `tools/complete_recording_metadata.py --workspace <workspace>` to declare the actual boundary/reminder/line-label flags, Python version and exact installed runtime packages. These annotations do not change the frozen prompts.
4. In that workspace, declare the `inference`, `evaluation` and `privacy` profiles and accepted custom-field rules. The extension helper reuses matching rules, adds missing rules and rejects conflicting IDs; an inherited lock is removed because it belongs to the source condition. Create a new offline lock. Use `--hash-large-files` when complete weight hashing is required; otherwise describe the evidence as partial and verify weights independently.
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

No confirmed upstream defect was inferred from these cases. The resulting documentation contribution from [the research owner's Fork](https://github.com/Mosionca2/ReproLLM) was accepted through [Docs Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11) and [merged PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12). The PR contains only the isolated-recording tutorial, navigation and changelog.


## Second-snapshot follow-up

A separately frozen local Qwen3-1.7B snapshot completed another 3,072 formal generations and a 768-response immediate fresh repeat. Its upstream revision and original-versus-modified status remain unverified; evidence binds exact local fingerprints. This is follow-up work within the same agent-assisted study, not an independent adopter or long-term deployment. Full records and controls are in [the second-model report](../reports/extensions/qwen3-1.7b/REPORT.md).

Development calibration showed that changing batch size altered a few decoded greedy outputs and scores, despite the shared seed and decoding mode. The predeclared selection rule retained batch16. ReproLLM captured the actual batch binding and distinct configuration records; it does not certify numerical equivalence. Every extension run used complete committed declarations, full local-weight hashing and an isolated workspace, with zero CRITICAL audit failures. The original primary-run audit findings remain intact. Public diff references and device identifiers are reviewed publication copies; original records stay private.


## Accepted upstream documentation contribution

The [Fork](https://github.com/Mosionca2/ReproLLM) branch `m9/t11-isolated-recording-recipe` supplied the concrete tutorial in [PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12), linked to [Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11). The maintainer approved placement/content and merged the contribution as `ad8b2c7057b6473072b65102eaf8e122b647acec`; Issue #11 is closed. The contribution does not modify product behavior or publish private research documents. Maintainer assistance covered the review, fork-workflow approval and merge; the review did not independently replicate the external study's GPU or scientific results.

Local checks recorded two independent CPU fixture conditions with released 0.6.1 (run schema 1) and two with source 0.7.0 at `8772904` (schema 2). Both check declared/observed condition and batch values, a child configuration-consumption witness, explicit cross-workspace diff, stale-lock exit after a declaration edit and selected historical export without rewriting run bytes. Five tutorial links/anchors and two navigation links pass. These four CPU recordings remain outside the model-response ledger; current totals and later bounded GPU checks are listed in the repository ledger. The existing installed environment was not changed.

Per upstream's documentation-only validation exception, local product full-suite and five-project/resource gates were NOT_APPLICABLE, not passed. [The evidence summary](../reports/reprollm-contribution-validation.json) retains version boundaries and the initial fixture-input correction. After maintainer authorization, [upstream CI attempt 2](https://github.com/EnumaElish123/ReproLLM/actions/runs/41445173597) passed all five platform jobs at head `5ddbf4b`. The original approval-pending CI state is retained separately in the receipt.


## Controlled real-GPU recovery follow-up

The [released-0.6.1 GPU recovery case](../reports/recovery-validation/REPORT.md) completed another 128 responses across an interrupted/resumed pair and an independent reference. The first capture retained 8 rows and recorded the child's signal exit; the unchanged experiment command added the remaining 56. All 64 sample IDs are unique and complete, with 0 output and 0 score differences against the fresh reference. Both actual attempt IDs and the original partial output remain preserved. Resume belongs to the experiment script; ReproLLM supplies the truthful interrupted/completed records and selected-run evidence. This is not current-source 0.7.0 GPU validation or a hard-kill recovery guarantee.

## Later workspace preparation

After committed recording metadata became part of the source checkout, a bounded check reproduced an adapter failure caused by repeated initialization. `tools/prepare_extension.py` now reuses existing matching rules, adds missing rules, rejects conflicts and discards the source condition's inherited lock. A real local-asset setup and full offline-lock check passed, with 25 repository tests and no frozen scientific changes. The [validation report](../reports/workspace-preparation/REPORT.md) distinguishes this study integration repair from upstream product findings; it adds no inference or capture counts.

## Pinned-source GPU follow-up

The later [source-recorder GPU check](../reports/source-recorder-validation/REPORT.md) adds three actual schema-2 source captures and one released reference. It verifies pre-child baselines, post-child auxiliary-input drift and an unchanged historical capture after current-file restoration. Source module version 0.7.0 is kept distinct from the unchanged installed distribution 0.6.1. This adds 256 development responses, without changing the formal scientific results. Source GPU interruption and hard-kill recovery remain untested.
