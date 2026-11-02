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

Model weights and machine-specific configuration are not distributed here. Execution and ReproLLM integration are added as independently validated stages. Published results will identify completed generations, failures, exact software versions, and limitations; this initial implementation contains no experimental outcome claim.

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
