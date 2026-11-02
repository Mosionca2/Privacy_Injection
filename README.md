# Privacy Injection

A controlled local-model study of confidentiality and task completion under injected instructions in retrieved text. ReproLLM records actual executions and their declared inputs. All identifiers are synthetic; models have no tools, network actions, or access to real credentials.

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

`privacy_study.record` prepares separate condition workspaces, declares relative local-model assets, adds project rules, creates an offline lock, and wraps genuine GPU inference with ReproLLM. On filesystems supporting hard links, existing local weights can be shared without duplicating their bytes. Model assets remain ignored by Git.

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

Read the [second-model report, charts and cross-model comparisons](reports/extensions/qwen3-1.7b/REPORT.md). Across both exact local snapshots, the [repository execution ledger](reports/execution-ledger.json) records **10,496 real generations in 30 GPU runs**, including **6,144 formal responses**. This is one agent-assisted study; upstream model provenance, parameter-count effects and general security are not established.

## ReproLLM upstream documentation contribution

A concrete isolated-condition recording guide has been submitted from [Mosionca2/ReproLLM](https://github.com/Mosionca2/ReproLLM) as [Docs Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11) and [Draft PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12). Its four documentation files cover independent workspaces, local/offline lock scope, bindings, explicit cross-workspace diff and selected historical export. The proposal is awaiting maintainer review.

[Local validation evidence](reports/reprollm-contribution-validation.json) records four CPU-only command rehearsals across released 0.6.1 and source 0.7.0, plus link/navigation checks. The scientific generation count remains 10,496. Upstream CI currently reports `action_required`; no CI success or upstream acceptance is claimed.
