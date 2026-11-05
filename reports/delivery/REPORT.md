# Research and ReproLLM delivery checkpoint

This checkpoint brings together the published experiments, functional checks and accepted documentation contribution. It describes one agent-assisted research project using exact local model snapshots. The scientific findings remain in the [primary report](../../REPORT.md) and [second-snapshot report](../extensions/qwen3-1.7b/REPORT.md).

The two-snapshot study and documented workflow follow-ups are complete. The [delivery status and evidence map](CHECKLIST.md) distinguishes finished work from the pending external case-index proposal and optional extensions. The validated implementation at `9780e6f` passed 59 local tests and 49 CI unit tests; the [closeout receipt](closeout-validation.json) records a fresh evidence/reader check and the corresponding implementation CI. Earlier validation receipts and test counts below remain scoped to their original checkpoints.

## Execution accounting

| Campaign | Completed responses | GPU captures | Original formal responses |
|---|---:|---:|---:|
| Primary local 8B study | 5,120 | 17 | 3,072 |
| Second local 1.7B study | 5,376 | 13 | 3,072 |
| Released recorder recovery/reference | 128 | 3 | 0 |
| Source recorder input checks | 256 | 4 | 0 |
| Source recorder recovery/reference | 256 | 6 | 0 |
| Fresh paired neutral-tail follow-up | 5,760 | 12 | 0 |
| GPU child kill, controlled tail repair/resume | 256 | 6 | 0 |
| Total | **17,152** | **61** | **6,144** |

There are 56 completed captures and five deliberately interrupted captures. The [new neutral-tail report](../tail-ablation-v1/REPORT.md) separately counts 4,608 fresh follow-up test responses. Its original-study results and the new dataset are not pooled. CPU fixtures and completed-condition skips add no model responses.

The [offline evidence verification](evidence-verification.json) checks 61 published GPU capture directories, 17,192 result-row appearances and 501 saved input-snapshot hashes, with large follow-up prompt inventories checked against their original captured hashes and the frozen public files. Across recovery snapshots, 40 unchanged retained copies are deduplicated, leaving **17,152 distinct completed responses**. Scores, coverage, declarations, actual exit states, selected exports and all phase ledgers are checked. Follow-up result/completion bytes also match their original recorded artifact hashes.

Four initial calibration captures precede the scientific freeze. Their differing scientific source files match recorded commit `8aa388b0992bee09cf90a3aa10361d00b7eafd12`. The scorer's syntax tree matches the frozen scorer. Historical source is read from Git without executing it. The primary and extension formal freezes still match their scientific inputs.

## Functional coverage and evidence

| Capability | Observed scope | Evidence |
|---|---|---|
| Initialization and project rules | Existing setup is reused, missing rules are added, conflicting definitions and existing destinations are protected | [Preparation validation](../workspace-preparation/REPORT.md), [regression guards](../../tests/test_extension.py) |
| Offline local identity and lock | Explicit local fingerprints and full-weight hashing; freshness checks cover manifest/rules rather than rehashing assets | [Actual setup/lock receipt](../workspace-preparation/validation.json), [CPU contract checks](../reprollm-validation.json) |
| Actual model execution | Two local snapshots, four defenses, genuine child captures and output-row run IDs | [Primary D0](../../evidence/formal/D0/REPRODUCIBILITY.md), [extension D0](../../evidence/extensions/qwen3-1.7b/formal/D0/REPRODUCIBILITY.md) |
| Custom-field bindings | Recorded defense, split and batch agree with executed flags; a deliberate contradiction is CRITICAL | [Contract receipt](../reprollm-validation.json), [verification inventory](evidence-verification.json) |
| Semantic diff | Real defense changes compared within each model's independent workspaces | [Primary D1–D0](../formal/diff-D1-D0.json), [extension D1–D0](../extensions/qwen3-1.7b/formal/diff-D1-D0.json) |
| Selected historical export | Explicit run selection preserves historical declarations after current manifest changes | [Contract checks](../reprollm-validation.json), [selected history](../../evidence/tool-validation/selected-history.md) |
| Nonzero exits and launch failure | CPU fixtures preserve exit 7 and failed launch; GPU interruption records actual child exit -15 | [Contract checks](../reprollm-validation.json), [recovery report](../recovery-validation/REPORT.md) |
| Resumption and repeats | Retained rows remain unchanged; fresh 768-response repeats match within each snapshot | [Recovery](../recovery-validation/comparison.json), [primary repeat](../repeat/comparison.json), [extension repeat](../extensions/qwen3-1.7b/repeat/comparison.json) |
| Copy-only checkpoint tail repair | Controlled copies preserve complete successes/failures, back up the damaged bytes and refuse complete unterminated JSON; actual model recovery is outside this CPU test | [Usage guide](../../docs/result-tail-repair.md), [actual CLI matrix](../tail-repair-validation/REPORT.md) |
| GPU child kill and repaired-prefix resume | Real child SIGKILL, explicitly constructed unfinished suffix, recorded backup/copy repair and actual resumed inference against fresh references on both snapshots | [Recovery evidence](../gpu-tail-recovery-validation/REPORT.md), [byte-chain verifier](../../tools/verify_gpu_tail_recovery.py) |
| Redaction | Tested synthetic patterns absent from tool-owned persistence; reviewed publication copies remove device identifiers | [Bounded contract check](../reprollm-validation.json), [publication boundary](../formal/publication.json) |
| Version-scoped documentation | Released 0.6.1 and source 0.7.0 command rehearsals, with source/input-phase differences retained | [Contribution receipt](../reprollm-contribution-validation.json) |

The scientific campaigns and GPU recovery used installed **ReproLLM 0.6.1**. Source 0.7.0 was first exercised by CPU documentation rehearsals and later by three [bounded GPU conditions](../source-recorder-validation/REPORT.md), alongside a released reference. A later [two-snapshot source recovery campaign](../source-recovery-validation/REPORT.md) adds six source captures. The source-module version and installed-distribution metadata are recorded separately. The existing environment was preserved. Schema-1 records retain their original input-phase limitations; this verification does not retroactively give them the source-0.7.0 capture contract.

## Practical feedback and contribution outcome

The run IDs, custom bindings, actual exit states, explicit exports and cross-workspace diff supplied useful evidence alongside the study's own identities and scoring. Audits exposed incomplete mechanism declarations in the initial integration. Those findings remain published; four later corrected-declaration runs generated 256 real responses with zero CRITICAL findings. Batch-size changes affected a few second-snapshot outputs, so calibration retained batch16 under the declared agreement rule. A seed alone did not establish batching equivalence.

The existing-manifest setup failure was a research adapter issue: repeated initialization correctly encountered ReproLLM's overwrite protection. The repair belongs to this repository. The observed lock freshness scope and diff exit semantics also matched their contracts. No upstream product defect was confirmed.

The reusable recording tutorial was contributed through [Mosionca2's fork](https://github.com/Mosionca2/ReproLLM), [Docs Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11) and [PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12). The PR is merged as `ad8b2c7057b6473072b65102eaf8e122b647acec`; Issue #11 is closed. Five upstream CI platform jobs passed on attempt 2 at contribution head `5ddbf4b`. The fork main was synchronized with the upstream merge. A [follow-up case-index proposal](https://github.com/EnumaElish123/ReproLLM/issues/11#issuecomment-6593163665) now links this consolidated public evidence from Issue #11. The proposal is submitted; index inclusion and adoption-metric changes are not claimed.

Maintainer assistance covered document placement/content review, fork-workflow authorization and merge. The reviewer did not independently repeat the private fixtures or scientific GPU experiments. This is an accepted documentation contribution from one agent-assisted project; independent-adopter counts, extended deployment history and publication citations are not established by these records. No invitation or personal-relationship claim is inferred from account ownership.

## Recheck the published evidence

From a matching full Git clone with the study's Python dependencies available:

```sh
python tools/verify_evidence.py --output reports/delivery/evidence-verification.json
python -m unittest discover -s tests -v
```

[The historical source-recovery checkpoint receipt](validation.json) preserves that stage's local results; [the closeout receipt](closeout-validation.json) links the current evidence check to its validated implementation. Verification is offline and runs no inference. It checks internal consistency of published artifacts, including scores recomputed with the study's frozen scoring definition. It is not an external attestation or independent scientific replication. Large model weights, bootstrap intervals and charts are not revalidated by this command. Device-sanitized run/log copies also cannot be treated as the private originals' complete byte identity.

The later [CPU CI gate](../ci-validation/REPORT.md) automates this complete evidence check and checks actual pinned-source ReproLLM reading of schema-1 and schema-2 archives. It compares a fresh verification result to the committed receipt on each main push or pull request. Its 30 CPU tests cover scoring, evidence, recovery and source guards; the full local scientific-environment suite has 40 passing tests. These maintenance checks add no model responses.

The subsequent [forced-termination stage](../termination-validation/REPORT.md) retains eight real CPU records across released and source recorders. Child SIGKILL records an interrupted child; recorder SIGKILL leaves unfinished evidence. Source-only outcome filters and explicit historical exports were exercised without rewriting records. Two additional guards bring the local suite to 42 tests and CI to 32 unit tests, alongside a fresh CPU matrix. The report preserves the first CI failure and its research-controller ordering correction. GPU and model-response accounting remain unchanged.

The later [copy-only tail-repair stage](../tail-repair-validation/REPORT.md) adds seven preservation/refusal guards, reaching 54 local tests and 44 CI tests after the intervening neutral-tail follow-up. Six actual CPU CLI captures validate both recorder producers, mode bindings, the refused child's exit 2, explicit exports and cross-mode diff. New repaired copies retain the trusted prefix while originals and complete failure markers remain preserved. This adds no model generations and does not establish GPU corruption recovery or power-loss durability.

The later [GPU child-kill and tail-recovery stage](../gpu-tail-recovery-validation/REPORT.md) connects six real GPU captures to four independent CPU inspection/repair records. Original interrupted output, constructed damaged copies, exact repair bundles and resumed/fresh-reference comparisons are verified together; only the 256 newly completed model responses enter the ledger.

## Remaining boundaries

- Local upstream revisions and original-versus-modified status remain unverified; conclusions bind exact published fingerprints. Four A100 80GB devices were used, without a test under a 5–8GB hardware limit.
- Controlled current-source GPU SIGTERM and child-SIGKILL recovery are validated on both local snapshots. The later repair/resume path uses a deliberately constructed unfinished suffix after the writer exits. Naturally torn writes, arbitrary corruption and power-loss durability remain untested.
- The separately frozen neutral-tail follow-up is documented above. A commercial-model extension has not been run.
- Original environment and completed-condition-skip receipts describe their historical checkpoints. Their initial pending/untested labels remain intact; the later version-scoped receipts establish the subsequent results.

The main two-snapshot comparison, recorded functional checks, fresh repeats, controlled recovery and accepted documentation contribution now have linked completion evidence. The boundaries above remain explicit rather than being counted as completed extensions.

## Later user-directed rule lifecycle extension

The [2026-11-05 consumer extension](../rule-lifecycle-validation/REPORT.md) adds three selected CPU recordings and twenty inner CLI operations for rule removal, immutable recovery copies, restoration, lock freshness and expected refusals. It retains all CLI/config/environment bindings and the real recorded Git state. The complete local suite passes 62 tests; CI additionally exercises fresh lifecycle cases. No model-response or GPU-capture totals change.
