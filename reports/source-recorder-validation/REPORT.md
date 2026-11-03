# Pinned-source recorder GPU validation

## Observed result

The [predeclared protocol](protocol.json) completed four genuine local Qwen3-1.7B development conditions, **64 new responses each**, for **256 new responses**. Three used ReproLLM source 0.7.0 at `ad8b2c7057b6473072b65102eaf8e122b647acec`; the fourth used the unchanged installed 0.6.1 recorder. All children exited 0 with complete eight-case/eight-variant coverage and distinct actual run IDs.

| Condition | Recorder module / run schema | New responses | Captured Git dirty | Actual run ID |
|---|---|---:|---|---|
| source-D0 | 0.7.0 / 2 | 64 | False | `20261103T015543Z-14ba74` |
| source-D1 | 0.7.0 / 2 | 64 | False | `20261103T015543Z-59cc35` |
| source-input-change | 0.7.0 / 2 | 64 | True | `20261103T015543Z-4272d6` |
| released-D0 | 0.6.1 / 1 | 64 | False | `20261103T015540Z-3d33c7` |

Each condition had its own checkout, manifest, offline full-weight lock and committed inputs. Four available A100 80GB devices hosted the four independent jobs; free memory was checked before launch. Existing local weights were linked after full identity verification. The scientific prompts, data, scoring source and formal freezes were not edited. This is recorder/workflow validation rather than a new formal defense estimate.

## Source and installed-distribution identity

The existing OSNIP environment still has the **0.6.1 installed distribution**. For source conditions, 148 tracked upstream package files were copied into ignored `assets/recorder-source`, hashed against the pinned checkout and selected through a process-local relative `PYTHONPATH`. No package upgrade, environment creation or model download occurred. Payload hashes were checked before and after capture; source code was not modified.

The source run records correctly identify their executing recorder module as **0.7.0**. The runner's `versions.reprollm` and environment distribution inventory correctly remain **0.6.1** because they query installed distribution metadata. They describe different scopes. Each condition retains its `recorder-source.json`, observed `runtime-witness.json` and original manifest; the [offline verifier](../../tools/verify_evidence.py) checks this explicit distinction rather than falsely requiring those versions to be equal.

## Pre-child baseline and post-child changes

All three source captures use schema 2 with `baseline_phase=pre_child`, `check_phase=post_child` and `consumption=unverified`. Source D0 and D1 have no changed declared inputs. The released reference remains schema 1 with unknown input phase.

Only the diagnostic condition changed the predeclared auxiliary `probe/declared-input.json`, after the executed controller enforced at least eight completed responses and incomplete coverage while the child was still running. The exact poll count was not persisted before the post-capture assessment failed, so it is retained as unknown rather than reconstructed as eight. The scientific runner does not read that file. The schema-2 file snapshot and before hash retain its original bytes, while the post-child fingerprint records the changed bytes. The captured Git dirty state and patch remain published, along with the [after-change diagnostic bytes](../../evidence/source-recorder-validation/source-input-change/diagnostic-input-after.json).

After preserving the capture, the diagnostic file was restored to its committed content. A second [explicit historical export](../../evidence/source-recorder-validation/source-input-change/historical-after-restore.md) retained the original selected-run evidence; `run.json` bytes remained unchanged. Its current-tree audit context is separate from the historical captured input check. No file-consumption guarantee is inferred from unchanged fingerprints.

## Comparisons and functional evidence

At identical D0 scientific identities, source versus released output strings changed in **0** rows and scores in **0** rows. Diagnostic D0 versus released output strings changed in **0** rows and scores in **0** rows. These are bounded observed comparisons, not batching or universal determinism guarantees.

Actual cross-workspace diffs cover [D1 versus D0](diff-source-D1.json), [released versus source D0](diff-released-D0.json) and [the diagnostic versus ordinary source D0](diff-source-input-change.json). The D1 diff includes the observed defense change. Every condition has a selected-run export and an audit retaining its findings. The intentional diagnostic dirty state is not represented as a clean execution.

The [comparison receipt](comparison.json) retains actual outcomes, provenance tags and source identity. The original model/recorder processes completed, but the three source controller processes then exited 1: their guard incorrectly required every candidate to be present. Schema 2 also retained two inline prose values as missing optional candidates. The guard was corrected to validate typed missing-to-missing candidates without replacing real input baselines. Assessment was rebuilt from the existing complete captures; no model execution was repeated and no run ID was replaced. Original failure logs remain private. The missing prose candidates remain visible in the public records and [minimal CPU reproduction](inline-candidate-mre.json), as an upstream clarification finding in [Issue #13](https://github.com/EnumaElish123/ReproLLM/issues/13). The specification permits text or paths; the intended candidate semantics require a maintainer decision before an upstream behavior change. The contributor could not assign the requested `spec` label because GitHub denied label permissions; that administrative action is requested from the maintainer.

[37 repository tests](unit-checks.json) pass, including source-payload mutation, baseline preservation, optional-candidate handling, input-change consistency and owned-child progress guards. No upstream product code was changed and no upstream full product gate, five-project qualification or release-readiness claim is made.

## Updated accounting and limits

The repository now contains **10,880 completed responses across 37 GPU captures**: 36 completed and one intentionally interrupted. Formal results remain **6,144 responses**. The [complete offline verification](evidence-verification.json) checks 10,888 row appearances and 201 saved input-snapshot hashes; the eight retained recovery rows are counted once. Full local model content was independently checked after the campaign.

The current-source GPU execution and declared-input phase gap is now covered by this bounded case. Source GPU interruption, hard-kill/power failure, damaged-output repair, verified upstream model revisions, paid APIs and neutral-tail ablation remain outside its scope. This is one agent-assisted research project with documented maintainer help, not an independent laboratory replication or a new adopter count. No product defect is inferred from successful contract checks.
