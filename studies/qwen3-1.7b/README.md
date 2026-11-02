# Second local-model extension

This separately versioned study tests the existing local Qwen3-1.7B snapshot. Its exact file identity is recorded; upstream revision and original-versus-modified status remain unverified. The primary Qwen3-8B study stays frozen and unchanged.

The tasks, case identifiers, attack wording, four defenses, scoring, seeds and decoding remain identical. Only model/tokenizer content and protocol/model metadata change. Primary-model results were already known, so this is an exploratory comparison across two exact local snapshots, not a claim about model-size scaling or unseen benchmark generalization.

## Execution

1. Calibrate D0 on all 24 development cases at batches 16, 64, 128 and 192. Select the fastest candidate that exactly matches batch 16 outputs and scores.
2. Complete all four development defenses. Inspect capability and output-cap events without changing the attacks or scores.
3. Freeze this model identity, shared scientific input hashes, runtime and selected batch before any second-model test generation.
4. Run all four formal defenses through ReproLLM in separate workspaces with committed manifests, locks and truthful mechanism/runtime declarations.
5. Generate a fresh D0 repeat; publish paired statistics, captures and explicit limitations.

To prepare a condition, run from the repository root, replacing the two local paths:

```sh
python tools/prepare_extension.py --study studies/qwen3-1.7b --destination /path/to/new-workspace --model /path/to/matching-model --defense D0 --split dev --batch-size 64
```

The destination is an independent clone outside this research checkout. For formal runs use `--split test` only after the extension freeze has been created. Full file hashes must match. In each condition workspace, create the offline lock with `--hash-large-files`, commit the manifest/lock/runtime declarations and project rules, then execute the declared real command with ReproLLM. The original top-level freeze is replaced only inside these separate extension workspaces. Model assets and raw host records are excluded from Git.

Status and results are updated after each completed stage.
