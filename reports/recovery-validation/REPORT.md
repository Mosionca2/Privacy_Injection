# Real-GPU interruption and recovery validation

## Observed result

A controlled **SIGTERM** interrupted a genuine local Qwen3-8B development run after completed output was present. ReproLLM 0.6.1 finalized the first capture as `interrupted`, retaining the child's actual nonzero signal exit. The unchanged experiment command then resumed in the same workspace: **8 completed responses were retained and 56 new responses were added**, producing all **64 unique expected samples**.

A separately launched uninterrupted reference generated another 64 responses with the identical scientific identity, runtime and batch. Comparing the recovered 64 rows to this fresh reference found **0 changed output strings** and **0 changed scores**. Both actual attempt IDs remain in the recovered result index. This is a bounded tool/workflow validation, not a new formal defense comparison.

| Capture | Recorded status | Child exit | Newly completed responses | Cumulative file rows | Actual run ID |
|---|---|---:|---:|---:|---|
| interrupted | interrupted | -15 | 8 | 8 | `20261102T130519Z-ed0731` |
| resumed | completed | 0 | 56 | 64 | `20261102T130747Z-3af6cf` |
| reference | completed | 0 | 64 | 64 | `20261102T130519Z-c87082` |

For this POSIX/Python launcher, the interrupted command returned `241` while its stored child exit was `-15` (SIGTERM). Both observed codes are retained; the negative child result and `interrupted` status identify the signal outcome rather than a completed experiment.

`Cumulative file rows` counts successful samples, excluding the identity header. The resumed file already includes the interrupted run's 8 rows; it is not evidence of 64 new resumed generations. Completed-response accounting is **8 + 56 + 64 = 128**, across three genuine GPU captures. An in-flight generation terminated before a completed row was written may have consumed compute but is excluded from the completed-response count.

## Conditions fixed before execution

The [validation protocol](protocol.json) fixed D0, the first eight development base cases, all eight variants per case, batch1, the existing local model fingerprints and unchanged scientific sources. FP16, SDPA, offline native loading, greedy decoding and thinking-disabled state were inherited from the same verified environment. No model or environment download was needed. Two available A100 devices hosted the recovery and reference workspaces; GPU availability was checked before every launch.

The controller signalled only its newly launched recorder process after observing incomplete real progress. ReproLLM forwarded the signal to the experiment child and finalized its record. Resume and sample skipping belong to the experiment script, not a ReproLLM checkpoint scheduler. Each workspace's actual manifest, lock, mechanism parameters, project rules and runtime declarations were committed before execution; offline locks included large-file hashing. Full local model content was independently checked before and after the campaign.

Condition commits are retained by immutable provenance tags, not research integration PRs:

- `recordings/gpu-recovery-20261102T125855Z-recovered` → [`13e5890185ac`](https://github.com/Mosionca2/Privacy_Injection/tree/13e5890185ac884bb1d46cfa257c893e33c62d22)
- `recordings/gpu-recovery-20261102T125855Z-reference` → [`1d1f6a302c97`](https://github.com/Mosionca2/Privacy_Injection/tree/1d1f6a302c97df7a41b94a7734b89106d692151d)

## Checks and evidence

- The initial partial output is retained under [interrupted evidence](../../evidence/recovery-validation/interrupted/results.jsonl), along with its original capture and original-byte artifact hash.
- The [resumed result](../../evidence/recovery-validation/resumed/results.jsonl) preserves the initial successful rows and file prefix byte-for-byte. There are no missing, extra or duplicate successful sample IDs.
- The final rows link to the two distinct actual interrupted/resumed ReproLLM IDs; newly completed counts agree with the second child's completion summary.
- The [fresh reference](../../evidence/recovery-validation/reference/results.jsonl) has the same cases, code, protocol, model identity, batch, software and decoding settings.
- The reusable [controller](../../tools/validate_gpu_resume.py) and its three ownership/progress/corruption guards were included in the **20 passing repository unit tests** before this real validation. No upstream ReproLLM product-suite pass is claimed.
- [comparison.json](comparison.json) records all observed outcomes, counts, exits and limits. The [repository ledger](../execution-ledger.json) now contains **10,624 completed model responses in 33 GPU captures**, including 32 completed captures and this one expected interrupted capture. The 6,144 formal responses and their statistical results are unchanged.

Each `current-audit-after-recovery.json` is explicitly a current-tree/latest-run audit after recovery. It is not a re-audit of the historical interrupted state. Selected-run exports retain their snapshot source labels and current-audit limits. Original host records remain private; reviewed publication copies remove raw device identifiers while original-byte input hashes remain intact.

## Reproduce the capture sequence

Prepare two separate checkouts using the tagged declarations and matching local assets. Keep their inputs committed and their working output ignored. With the existing study environment selected, from the research checkout:

```sh
python tools/validate_gpu_resume.py --workspace ../prepared-recovery --gpu-index 0 --name recovery-interrupted --expected-samples 64 --interrupt-after 8
python tools/validate_gpu_resume.py --workspace ../prepared-recovery --gpu-index 0 --name recovery-resumed --expected-samples 64
python tools/validate_gpu_resume.py --workspace ../prepared-reference --gpu-index 1 --name recovery-reference --expected-samples 64
```

The reference can run concurrently in its independent workspace. Choose available devices and retain the actual run IDs; the command names alone do not identify an execution. Preserve the finalized partial results before resuming and compare the complete scientific identities before comparing outputs.

## Limits

This validates one controlled SIGTERM case in the tested environment, local snapshot and batch. It does not establish hard-kill/power-loss recovery, repair of a corrupted or truncated JSONL file, recovery on the second model, or current-source 0.7.0 GPU interruption. The controller rejects finalized incomplete lines rather than dropping them. The 0.6.1 schema-1 input phase remains unknown; independent immutable-input checks do not change that recorder contract.

The [upstream documentation PR](https://github.com/EnumaElish123/ReproLLM/pull/12) is separate: its source/doc validation remains version-scoped and its CI/maintainer review status must be checked independently. No new upstream defect is inferred from a successful interruption/recovery case.
