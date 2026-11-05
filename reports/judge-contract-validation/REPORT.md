# Judge-only CLI contract validation

Seven bounded synthetic audit scenarios completed **31 actual CLI calls** against source module 0.7.0 at `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`. No model inference or model download occurred. The synthetic local asset is explicitly an audit fixture, not a usable judge model.

- Explicit shipped `judge_only` skips the primary-model requirement; adding shipped `privacy` preserves that exception.
- Adding `inference` or replacing the shipped judge-only profile with a user profile restores the primary-model requirement.
- An empty judge-model declaration, empty judge prompt and absent judge temperature fail the corresponding judge rules. Invalid local IDs/references are separately rejected by manifest validation; early fixture construction errors were corrected rather than reported as upstream defects.
- Changing judge `max_tokens` from 16 to 17 in controlled offline lock copies produces **HIGH** drift and exit 1 under `--fail-on HIGH`.
- A separate actual J0/J1 GPU-run comparison preserves both historical records. Those V1 records are retained diagnostic experiments with a known length-control construction error; their run-state comparison is tool evidence, not a valid scientific effect estimate.

[The command receipt](../../evidence/judge-contract-validation/validation.json) lists exact argument vectors and expected exits. Per-scenario manifests, actual audit reports, source identity, import witnesses and both diffs are in the same evidence directory. The unchanged installed distribution reports 0.6.1; process-local imports use the recorded 0.7.0 source payload. The checks establish these bounded contracts, not complete tool conformance.

Reproduce with a fresh workspace and the exact source checkout:

```sh
python tools/validate_judge_contract.py --consumer-source /path/to/pinned/ReproLLM --workspace raw/fresh-judge-contract --published raw/judge-contract-evidence
```
