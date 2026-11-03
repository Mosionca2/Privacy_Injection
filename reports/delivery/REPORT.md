# Research and ReproLLM delivery checkpoint

This checkpoint brings together the published experiments, functional checks and accepted documentation contribution. It describes one agent-assisted research project using exact local model snapshots. The scientific findings remain in the [primary report](../../REPORT.md) and [second-snapshot report](../extensions/qwen3-1.7b/REPORT.md).

## Execution accounting

| Campaign | Completed responses | GPU captures | Formal responses |
|---|---:|---:|---:|
| Primary local 8B study, including calibration, development, repeat and corrected declarations | 5,120 | 17 | 3,072 |
| Second local 1.7B study, including calibration, development and repeat | 5,376 | 13 | 3,072 |
| Controlled interruption/resume and fresh reference | 128 | 3 | 0 |
| Total | **10,624** | **33** | **6,144** |

There are 32 completed captures and one deliberately interrupted capture. The interrupted child's eight retained responses and the resumed child's 56 new responses count once each. The separate reference contributes 64. CPU fixtures and completed-condition skips add no model responses.

The [offline evidence verification](evidence-verification.json) checks all 33 published capture directories, 10,632 result-row appearances and 172 input-snapshot hashes. Eight unchanged rows appear in both the interrupted and resumed snapshots, leaving **10,624 distinct completed responses**. It recomputes stored scores from published synthetic truth, checks case coverage, declared/observed conditions, child outcomes, selected-run export references, per-phase ledgers and repository totals. Recovery prefix bytes and reference comparisons also agree.

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
| Redaction | Tested synthetic patterns absent from tool-owned persistence; reviewed publication copies remove device identifiers | [Bounded contract check](../reprollm-validation.json), [publication boundary](../formal/publication.json) |
| Version-scoped documentation | Released 0.6.1 and source 0.7.0 command rehearsals, with source/input-phase differences retained | [Contribution receipt](../reprollm-contribution-validation.json) |

The scientific campaigns and GPU recovery used installed **ReproLLM 0.6.1**. Source 0.7.0 was exercised by CPU documentation rehearsals. The existing environment was preserved. Schema-1 records retain their original input-phase limitations; this verification does not retroactively give them the source-0.7.0 capture contract.

## Practical feedback and contribution outcome

The run IDs, custom bindings, actual exit states, explicit exports and cross-workspace diff supplied useful evidence alongside the study's own identities and scoring. Audits exposed incomplete mechanism declarations in the initial integration. Those findings remain published; four later corrected-declaration runs generated 256 real responses with zero CRITICAL findings. Batch-size changes affected a few second-snapshot outputs, so calibration retained batch16 under the declared agreement rule. A seed alone did not establish batching equivalence.

The existing-manifest setup failure was a research adapter issue: repeated initialization correctly encountered ReproLLM's overwrite protection. The repair belongs to this repository. The observed lock freshness scope and diff exit semantics also matched their contracts. No upstream product defect was confirmed.

The reusable recording tutorial was contributed through [Mosionca2's fork](https://github.com/Mosionca2/ReproLLM), [Docs Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11) and [PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12). The PR is merged as `ad8b2c7057b6473072b65102eaf8e122b647acec`; Issue #11 is closed. Five upstream CI platform jobs passed on attempt 2 at contribution head `5ddbf4b`. The fork main was synchronized with the upstream merge.

Maintainer assistance covered document placement/content review, fork-workflow authorization and merge. The reviewer did not independently repeat the private fixtures or scientific GPU experiments. This is an accepted documentation contribution from one agent-assisted project; independent-adopter counts, extended deployment history and publication citations are not established by these records. No invitation or personal-relationship claim is inferred from account ownership.

## Recheck the published evidence

From a matching full Git clone with the study's Python dependencies available:

```sh
python tools/verify_evidence.py --output reports/delivery/evidence-verification.json
python -m unittest discover -s tests -v
```

[The checkpoint validation receipt](validation.json) records the actual local results. Verification is offline and runs no inference. It checks internal consistency of published artifacts, including scores recomputed with the study's frozen scoring definition. It is not an external attestation or independent scientific replication. Large model weights, bootstrap intervals and charts are not revalidated by this command. Device-sanitized run/log copies also cannot be treated as the private originals' complete byte identity.

## Remaining boundaries

- Local upstream revisions and original-versus-modified status remain unverified; conclusions bind exact published fingerprints. Four A100 80GB devices were used, without a test under a 5–8GB hardware limit.
- Current-source 0.7.0 GPU execution, hard-kill/power-loss recovery and corrupted-output repair remain untested.
- A neutral-tail ablation and commercial-model extension have not been run. They would require separately specified conditions and evidence.
- Original environment and completed-condition-skip receipts describe their historical checkpoints. Their initial pending/untested labels remain intact; the later version-scoped receipts establish the subsequent results.

The main two-snapshot comparison, recorded functional checks, fresh repeats, controlled recovery and accepted documentation contribution now have linked completion evidence. The boundaries above remain explicit rather than being counted as completed extensions.
