# Source 0.7.0 controlled GPU recovery

## Result

The [predeclared protocol](protocol.json) completed controlled SIGTERM/recovery cases on the exact existing local 8B and 1.7B snapshots. Each model has an interrupted/resumed condition and an independently generated uninterrupted reference. Across both pairs there are **256 newly completed responses and six genuine captures**: four completed and two intentionally interrupted.

| Snapshot / stage | Recorded status | Child exit | Recorder launcher exit | Newly completed responses | Actual run ID |
|---|---|---:|---:|---:|---|
| primary / interrupted | interrupted | -15 | 241 | 8 | `20261103T043353Z-10a90e` |
| primary / resumed | completed | 0 | 0 | 56 | `20261103T043631Z-064d2a` |
| primary / reference | completed | 0 | 0 | 64 | `20261103T043353Z-1c944b` |
| extension / interrupted | interrupted | -15 | 241 | 8 | `20261103T043353Z-47ecd5` |
| extension / resumed | completed | 0 | 0 | 56 | `20261103T043617Z-216816` |
| extension / reference | completed | 0 | 0 | 64 | `20261103T043353Z-e9ac1f` |

| Snapshot | Retained responses | Resumed new responses | Fresh reference | Changed outputs vs reference | Changed scores vs reference |
|---|---:|---:|---:|---:|---:|
| extension | 8 | 56 | 64 | 0 | 0 |
| primary | 8 | 56 | 64 | 0 | 0 |

Each recovered result contains all 64 unique expected samples. The resumed file retains the interrupted prefix byte-for-byte and preserves each row's originating run ID; only missing successes are added. The resumed cumulative file is not counted as 64 new resumed responses. Terminated in-flight work is excluded from completed-response counts. Results bind these exact snapshots and this batch; observed agreement is not a general determinism guarantee.

## Recorder and scientific identity

All six attempts used source module **0.7.0** at `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`, with schema 2, pre-child baselines, separate post-child checks and unverified consumption. The existing installed distribution remains **0.6.1**. Each attempt has an observed runtime witness and source identity; 148 copied package files were checked before and after capture. No upstream product code or installed package was changed.

The model weights were already local and linked into four independent working checkouts. Full model identities were verified before and after the campaign. All conditions use D0, eight development base cases, eight variants per case and batch1. Existing formal freezes, prompts, datasets and scoring source remain unchanged. Four available A100 80GB devices hosted the recovery and reference jobs, with free memory checked before every capture. A recorder receives the controller's signal only after real partial progress; it forwards the signal to its owned experiment child.

The controller persists the actual observed interruption count before final assessment, avoiding the precision loss encountered by the earlier diagnostic controller. The per-attempt `interruption-progress.json` files retain those observations. No completed workload is wrapped in an empty recovery capture. Resume is implemented by the scientific script; ReproLLM supplies the actual statuses, child exits, input baselines and selected-run evidence.

## Evidence and inspection

- [Comparison and provenance tags](comparison.json) retain all six actual IDs and four committed input snapshots. These refs preserve history; they do not create research integration PRs.
- [Primary interrupted](../../evidence/source-recovery-validation/primary-interrupted/REPRODUCIBILITY.md), [resumed](../../evidence/source-recovery-validation/primary-resumed/REPRODUCIBILITY.md) and [reference](../../evidence/source-recovery-validation/primary-reference/REPRODUCIBILITY.md) exports select the exact corresponding captures.
- [Extension interrupted](../../evidence/source-recovery-validation/extension-interrupted/REPRODUCIBILITY.md), [resumed](../../evidence/source-recovery-validation/extension-resumed/REPRODUCIBILITY.md) and [reference](../../evidence/source-recovery-validation/extension-reference/REPRODUCIBILITY.md) exports preserve the second pair separately.
- Real attempt diffs are retained for [primary](diff-primary-attempts.json) and [extension](diff-extension-attempts.json). Input checks remain unchanged, including absent optional prose candidates under the clarified contract.
- Each `current-audit-after-completion.json` is explicitly a current-tree/latest-run audit after its pair completed, not an historical re-audit of the interrupted attempt. Original records remain private; reviewed publication copies preserve input snapshots and hashes.

## Issue #13 feedback closure

The maintainer closed [Issue #13](https://github.com/EnumaElish123/ReproLLM/issues/13) and applied `spec`. The documented interpretation retains optional text-or-path candidates: missing before/after and unchanged means continued absence, not a required-input failure. A sentence may also be a real filename, so no punctuation/whitespace path heuristic was introduced. The research verifier preserves these candidates and checks real saved baselines separately.

The contributing account repeated the CPU fixture on the clarified commit, observed the same two optional candidates, verified unchanged product payload bytes, and observed five successful exact-head official CI jobs. [The receipt](clarification-recheck.json) separates those checks from the maintainer's own regression report. [The contributor follow-up](https://github.com/EnumaElish123/ReproLLM/issues/13#issuecomment-6595448514) closes the reproduction → clarification → revisit loop. No duplicate upstream product-fix PR is needed for that documentation resolution.

## Verification and accounting

All **39 repository tests pass** ([receipt](unit-checks.json)); added guards check the actual selected module versus installed metadata and reject mixed recovery identities or changed retained responses. The [complete offline evidence verification](evidence-verification.json) checks all **43 published GPU captures**, 11,160 row appearances and **243 saved input snapshots**. Retained rows repeated in later snapshots are counted once.

The repository now contains **11,136 completed responses**, **40 completed captures** and **three intentionally interrupted captures**. Formal results remain **6,144 responses**. This campaign adds no new formal defense estimate, adopter count, paid call, training or model download. It is not upstream five-project acceptance or release qualification.

## Remaining limits

This validates controlled SIGTERM on two local snapshots in the observed environment. It does not establish hard-kill/power-loss recovery, corrupted-output repair, unknown upstream model revisions, general RAG security or independent laboratory replication. The scientific runner rejects finalized truncated rows rather than repairing them. Known agent and maintainer assistance remain explicit.
