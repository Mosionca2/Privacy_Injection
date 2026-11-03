# Privacy Injection

A controlled local-model study of confidentiality and task completion under injected instructions in retrieved text. ReproLLM records actual executions and their declared inputs. All identifiers are synthetic; models have no tools, network actions, or access to real credentials.

Read the [delivery checkpoint and functional coverage](reports/delivery/REPORT.md) for the consolidated evidence, accepted upstream contribution and remaining limits. The offline verifier checks response accounting and published input snapshots without running inference.

The paired design uses two tasks (entity lookup and latest-record lookup), four prompt interventions, three attack families, two injection positions, and separate clean and authorized-copy controls. There are 24 development cases and 96 held-out cases. A complete single-model formal experiment requires 3,072 newly generated responses. The statistical unit is the base case, not each response.

- D0: confidentiality policy with plain record presentation.
- D1: D0 plus a delimited external-data block and boundary instruction.
- D2: D1 plus a policy/task reminder after the block.
- D3: D1 plus a source label on every external line, including injected text.

Privacy leakage, public-task correctness, and safe task correctness are scored separately. Refusal or an empty response is not a safe task success. Authorized-copy controls help distinguish confidentiality from inability to copy identifiers. These synthetic tasks and fixed attacks cannot establish general RAG security.

## Development

Use Python 3.10 or newer and a compatible CUDA PyTorch installation. Install `requirements.txt`, then run:

```sh
python -c 'from privacy_study.core import prepare; prepare(".")'
python -m unittest discover -s tests -v
```

Model weights and machine-specific configuration are not distributed here. Execution and ReproLLM integration are added as independently validated stages. Published results will identify completed generations, failures, exact software versions, and limitations; completed stages and their evidence are reported below.

## Recorded execution

`privacy_study.record` contains the frozen original recording implementation. For new model-study workspaces from the current checkout, use `tools/prepare_extension.py`: it accepts committed recording metadata, reuses matching rules, adds missing rules, and rejects conflicting rule definitions. Each new condition requires a fresh offline lock and committed inputs before inference. On filesystems supporting hard links, existing local weights can be shared without duplicating their bytes. Model assets remain ignored by Git.

The inference entry point is:

```sh
python -m privacy_study.run --model assets/model --defense D0 --split dev --batch-size 1
```

Result files contain independent per-response scores and actual ReproLLM run IDs. Interrupted conditions resume only when scientific identity, software versions, case selection, and batch size match. A completed file does not trigger a new inference job. Each recorded condition retains its own manifest, lock, rules, capture warnings, and selected-run export.

Formal execution additionally requires `protocol.freeze.json`. Changing code, test data, protocol, model identity, dependency versions, or batch size invalidates that frozen experiment. Analysis rejects incomplete case clusters, missing defense conditions, duplicate successes, and mixed scientific identities.

## Initial throughput calibration

Four real ReproLLM-recorded development runs each generated the same 64 responses. Batch sizes 1, 8, 32, and 64 produced identical output strings and scores in this bounded comparison. Batch 64 reached about 19.5 responses/s versus 2.5 for batch 1, with approximately 20.2 GiB peak reserved CUDA memory. This is a small calibration result, not a guarantee for every batch or workload. Detailed measurements and recordings are under `reports/calibration/` and `evidence/calibration/`.

ReproLLM 0.6.1 `lock --check` checks changes to the manifest and project rules; it does not rehash referenced local model content. This study separately records full model-file SHA-256 identities, checks metadata before/after inference, and rechecks full model identity before formal-result publication. Default local-model locks without `--hash-large-files` are explicitly partial weight evidence. Public run copies remove device UUIDs; original records remain available privately.

## Development completion and formal freeze

The four defense conditions completed 768 real development generations without infrastructure failures or output-cap events. Authorized-copy recall was 100% in each condition. Clean-task accuracy ranged from 79.2% to 87.5%; the fixed D0 capability cohort contains 20 of the 24 cases. These are development results, not held-out estimates. Actual cross-condition ReproLLM diffs and paired summaries are under `reports/development/`.

The formal protocol fixes batch size 64, all scientific source files, 96 held-out cases, model content identity, and the actual dependency versions before any formal generation. No attack template or scoring rule is selected from formal outcomes.

## ReproLLM contract checks

Nine bounded CPU fixture checks cover offline locking, manifest freshness, the limited scope of local-asset freshness, synthetic credential redaction, CRITICAL custom-parameter conflicts, preserved nonzero exits, failed launch status, explicit historical export, and recorded-state diff. Their source is `tools/verify_reprollm.py`; results and owned capture artifacts are in `reports/reprollm-validation.json` and `evidence/tool-validation/`. These fixture executions are not counted as model generations.

The declared-field presence rule and runtime consistency rule are distinct: a present `custom.defense` can pass its project rule while a contradictory observed flag correctly fails `consistency.custom_fields` at CRITICAL. Diff comparisons without an exit threshold omit `--fail-on`; `NONE` is the lowest drift severity, not a switch disabling failure.

## Completed results

The formal study completed **3,072 generations**. Attack-query leakage was 44.44% (D0), 30.56% (D1), 19.44% (D2), and 19.62% (D3); safe task success under attack was 50.87%, 61.81%, 74.83%, and 72.74%. These are controlled synthetic-task results for one exact local model snapshot, not a general safety guarantee.

A fresh D0 repeat generated 768 additional responses with no changed output strings or scores. Original recording audits exposed a missing mechanism-parameter declaration; those findings remain published. Four subsequent 64-response validations of completed, committed declarations have zero CRITICAL findings.

Read [the complete report and figures](REPORT.md), [ReproLLM case study](docs/reprollm-case-study.md), and [execution ledger](reports/completion.json). The ledger contains 5,120 real model generations across 17 GPU runs, with separate CPU-only tool checks.

## Second local snapshot extension

The separately frozen Local Qwen3-1.7B study completed another 3,072 formal responses and a 768-response fresh repeat. Its larger calibration batches changed a few greedy outputs and scores, so the predeclared agreement rule retained batch16. All 13 extension runs used clean committed inputs and have zero CRITICAL audit failures. Original primary-study findings remain retained.

Read the [second-model report, charts and cross-model comparisons](reports/extensions/qwen3-1.7b/REPORT.md). The two original study campaigns comprise **10,496 real generations in 30 GPU runs**, including **6,144 formal responses**. The [repository execution ledger](reports/execution-ledger.json) also counts subsequent bounded workflow validation separately. This is one agent-assisted study; upstream model provenance, parameter-count effects and general security are not established.

## ReproLLM upstream documentation contribution

A concrete isolated-condition recording guide from [Mosionca2/ReproLLM](https://github.com/Mosionca2/ReproLLM) was accepted through [Docs Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11) and [merged PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12), upstream commit `ad8b2c7`. Its four documentation files cover independent workspaces, local/offline lock scope, bindings, explicit cross-workspace diff and selected historical export.

[The validation receipt](reports/reprollm-contribution-validation.json) records four CPU-only command rehearsals across released 0.6.1 and source 0.7.0, link/navigation checks, the approving review and five successful upstream CI platform jobs. Maintainer assistance covered content/placement review, fork-workflow approval and merge; it did not independently replicate the scientific results. The CPU rehearsals add no model generations; current model-response totals are in the repository execution ledger.

## Real-GPU interruption and recovery

A controlled 0.6.1 SIGTERM case retained 8 completed responses and resumed with 56 new responses, with full unique 64-sample coverage. The recovered outputs and scores differ from a fresh uninterrupted 64-response reference in 0 and 0 rows respectively. The [validation report](reports/recovery-validation/REPORT.md) preserves the interrupted record, both actual attempt IDs, provenance tags and explicit limits.

At the recovery checkpoint, the repository contained **10,624 completed model responses across 33 GPU captures**: 32 completed and one intentionally interrupted. Formal results remain 6,144 responses. Research updates continue directly on main; historical recording tags are provenance, not integration branches.

## Preparing later recording workspaces

The extension adapter now supports source checkouts with committed recording metadata and protects conflicting rules and existing condition directories. A real local-asset preparation and full offline-lock check passed alongside 25 repository tests. This setup check adds no model generations or run captures. Read the [workspace preparation validation](reports/workspace-preparation/REPORT.md) before preparing a later model study.

## Source recorder GPU validation

Three pinned-source 0.7.0 GPU conditions and a released-0.6.1 reference completed 256 new responses. Schema-2 baselines preserve the original diagnostic input while post-child checks detect its deliberate change. Installed distribution metadata remains 0.6.1; no environment upgrade occurred. [The report](reports/source-recorder-validation/REPORT.md) records source identity, actual run IDs, diffs, historical exports and limits.

Current repository totals are **10,880 completed responses and 37 GPU captures**, with **6,144 formal responses** unchanged. All 37 repository tests and the full published-evidence consistency check pass.
