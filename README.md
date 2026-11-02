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
