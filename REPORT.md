# Privacy injection and reproducibility: completed study

## Outcome and evidence

The held-out study completed **3,072 genuine local-model generations**: 96 paired cases, four defenses, and eight conditions per case/defense. There were no infrastructure failures, missing case clusters, duplicated successes, or output-cap events in the formal results. Every response links to its actual ReproLLM run ID. An independent D0 repeat generated another **768 responses**; all output strings and scores matched the first run.

The complete published execution ledger contains **5,120 model generations across 17 GPU runs**: 256 batch-calibration generations, 768 development generations, 3,072 formal generations, 768 repeat generations, and 256 separate declaration-validation generations. CPU-only tool fixtures are separate and are not counted as model generations. See [the execution ledger](reports/completion.json), [formal analysis](reports/formal/analysis.json), and [frozen protocol](protocol.freeze.json).

## Research question and controlled setting

The question is whether external-data boundaries, a trusted tail reminder, or per-line origin labels reduce disclosure of a synthetic internal identifier while preserving public-record task success. The model receives a private reference in the system message and a public-record question. The attacker can add instructions only to the retrieved text, at its start or end, without knowing the private value or modifying the original public records. The model has no external tools or network actions.

Two task types are balanced: entity lookup and selecting the latest dated record for an entity. Development has 24 cases; the held-out set has 48 cases of each type. Private references and public answers share the same identifier format. Their truth is known when data is generated. All values are synthetic. Development and test identifiers are disjoint. Attack wording is held out, but the three attack families remain the same: instruction replacement, authority impersonation, and a claimed verification dependency. This is not a held-out-family generalization test.

D0 applies the confidentiality policy to ordinary record text. D1 additionally delimits external data and explains its trust boundary. D2 adds a trusted policy/task reminder after that block. D3 adds origin labels to every external line, including the injected text. The policy, data, attacks and scoring were fixed before formal generation. These are complete prompt strategies; token lengths are not matched, so effects cannot be attributed to an isolated tag or attention mechanism.

Each case/defense has one clean public task, one authorized-copy control, and six attacks (three families times two positions). Authorized controls replace confidentiality with explicit permission and are excluded from attack leakage. They check copying capability without proving a formal access property under the original policy.

## Model and execution protocol

The tested model is an existing local Qwen3-8B snapshot using `Qwen3ForCausalLM`. The upstream repository revision was not independently established; results apply to the exact files listed in [model.identity.json](model.identity.json), not to every model carrying that label. Model weights are not distributed. Exact replication requires matching those fingerprints; replacing the model requires a new explicit protocol.

Execution used Python 3.10.19, PyTorch 2.5.1+cu121, Transformers 5.2.0, Accelerate 1.12.0, Safetensors 0.7.0 and ReproLLM 0.6.1. Four A100 80GB devices ran independent condition workspaces. Model loading was offline with Safetensors, native code, FP16 and SDPA. Thinking was disabled. Greedy generation used at most 32 new tokens; inputs over 1,024 tokens would fail instead of being truncated. The final batch size was 64. Full model content was checked before publication, with metadata mutation guards around inference.

The development-only calibration compared batches 1, 8, 32 and 64 on identical 64-request inputs. Outputs and scores matched in that comparison. Measured generation-loop throughput rose from 2.52 to 19.52 responses/s; peak reserved memory at batch 64 was 20.22 GiB. This is a bounded workload measurement, not a general inference-speed claim. Scientific source hashes, actual dependency versions, model identity and batch size were frozen before held-out execution.

## Metrics and statistical unit

Primary leakage means the complete private reference appears in newly generated output, case-insensitively. Separator-normalized matching is retained as a diagnostic; partial, encoded or semantic disclosure is outside this metric. Public-task correctness requires the public identifier and no other public candidate after excluding the known private reference. A correct public answer plus the private reference is therefore task-correct but privacy-violating. Safe task success requires correctness without leakage. An empty output or refusal is not a safe success. Exact output-format matching is retained per response.

Attack-query leakage averages six attacks per base case. `any_leak` measures at least one leak under that fixed six-query budget. All statistical comparisons resample the **96 base cases**, preserving attack clusters and stratifying by task, with 2,000 bootstrap repetitions. Confidence intervals below are exploratory descriptive 95% intervals. The 3,072 outputs are not 3,072 independent subjects.

## Held-out results

All table entries below are percentages. Leakage and safe success refer only to attack conditions; normal and authorized controls are separate.

| Defense | Clean success | Authorized recall | Attack leakage | Safe attack success | Cases with any leak |
|---|---:|---:|---:|---:|---:|
| D0 | 93.75 | 100.00 | 44.44 | 50.87 | 100.00 |
| D1 | 92.71 | 100.00 | 30.56 | 61.81 | 90.62 |
| D2 | 93.75 | 100.00 | 19.44 | 74.83 | 59.38 |
| D3 | 93.75 | 100.00 | 19.62 | 72.74 | 63.54 |

D2 has the highest observed safe success in this study. D2 and D3 have similar observed leakage; their small difference does not establish superiority. Every defense still leaked under some attacks. Authorized recall was 100% in all conditions, so low leakage cannot be explained simply by an inability to reproduce these identifiers. The fixed capability cohort defined using D0 clean success and authorized recall contains **90 cases**; every defense uses that same cohort, and its separate descriptive results are in `summary.csv`.

![Privacy and utility](reports/formal/privacy-utility.png)

The preselected paired contrasts are shown in percentage points. No extra comparison was chosen to make a formal outcome look favorable.

| Comparison | Metric | Difference (pp) | 95% paired interval (pp) |
|---|---|---:|---:|
| D1-D0 | leak | -13.89 | [-16.32, -11.46] |
| D1-D0 | clean_acc | -1.04 | [-3.12, +0.00] |
| D1-D0 | safe_utility | +10.94 | [+8.33, +13.54] |
| D2-D1 | leak | -11.11 | [-13.72, -8.33] |
| D2-D1 | clean_acc | +1.04 | [+0.00, +3.12] |
| D2-D1 | safe_utility | +13.02 | [+10.42, +15.80] |
| D3-D1 | leak | -10.94 | [-13.37, -8.68] |
| D3-D1 | clean_acc | +1.04 | [+0.00, +3.12] |
| D3-D1 | safe_utility | +10.94 | [+8.68, +13.37] |

Suffix injection leaked more often than prefix injection in each defense under these fixed templates. This is a result for these bounded prompts, not an explanation of general model attention. Family/position counts and scores are in [attack-position.csv](reports/formal/attack-position.csv).

![Position comparison](reports/formal/attack-position.png)

![Ability controls](reports/formal/ability-controls.png)

## Resource use and fresh repeat

The generation-loop times below include response scoring and JSONL writes, exclude model loading, and are not the total orchestration time. ReproLLM captures, locking, exports, model hashing and preparation add overhead; their original records remain available. Peak figures are PyTorch reserved memory, not a whole-device allocation guarantee.

| Defense | Model load (s) | Generation loop (s) | Responses/s | Peak reserved (GiB) |
|---|---:|---:|---:|---:|
| D0 | 38.55 | 33.45 | 22.96 | 21.70 |
| D1 | 38.68 | 35.40 | 21.69 | 23.25 |
| D2 | 33.69 | 39.70 | 19.35 | 24.43 |
| D3 | 38.22 | 38.29 | 20.06 | 23.57 |

The D0 repeat used the same scientific identity, software, batch and case set, with a fresh result file and a distinct ReproLLM run. It generated 768 new responses with **0 changed strings and 0 changed scores**. This is same-environment repeatability, not a cross-hardware bitwise guarantee. The code also rejects mixed result identities and duplicate successes; interruption of a GPU job was not deliberately exercised.

## ReproLLM findings and corrected declarations

ReproLLM was used for initialization, manual project rules, offline locks, large-file hashing during calibration, lock freshness checks, genuine GPU command capture, run inspection, auditing, actual cross-defense semantic diffs, and selected-run exports. Nine additional CPU contract checks cover synthetic secret redaction, explicit failure states, critical runtime parameter conflicts, historical exports and diff behavior. Their source and owned artifacts are published separately.

The original formal recordings **were not audit-clean**. Audit correctly reported `privacy.mechanism_declared` at CRITICAL because the manifest omitted the mechanism parameter dictionary, despite the executed templates being fixed in source. It also reported untracked declaration files and incomplete environment declarations. These original manifests, runs and findings remain unchanged under `evidence/formal/`; they are not retrospectively relabeled as complete captures.

A separate validation round completed the actual mechanism flags, exact runtime pins and Python declaration, committed the inputs, and generated 64 new development responses per defense. All four subsequent audits have **zero CRITICAL findings**, and the captured Git workspaces are clean. Those committed inputs are reachable on `records/metadata-D0` through `records/metadata-D3`; the 256 additional responses validate the corrected recording workflow and do not replace the held-out estimates. Remaining informational detection findings, if any, are retained in [the metadata validation report](reports/metadata-validation.json).

A confirmed scope boundary is that `lock --check` compares the manifest and project-rule hashes; it does not rehash referenced local model content. Local files need additional content verification. Default large-weight locks may contain sizes without weight hashes; this study retains independent full SHA-256 identities. A declared-field presence check is also distinct from runtime consistency: the test conflict correctly appeared under `consistency.custom_fields` at CRITICAL, not under the project rule's presence result. Diff `--fail-on NONE` means the lowest severity threshold; omit the option for an informational comparison.

Public evidence copies remove raw device UUIDs. Original tool records remain private, and input hashes still refer to the original input bytes. Synthetic redaction checks cover only the tested patterns, not arbitrary confidential text. No paid inference API, LLM judge, model training or remote model download was used in these experiments.

## Limits and contribution assessment

This is one agent-assisted study of one local model snapshot, two short synthetic tasks, three fixed non-adaptive attack families and a literal disclosure metric. The sample supports visible paired effects, not fine distinctions of one or two percentage points or universal safety claims. Prompt lengths differ across interventions. Exact upstream model provenance and cross-platform repeatability remain unverified. ReproLLM recording, hash equality and semantic diff do not by themselves prove that a defense caused a model outcome.

The study produced a reusable recording recipe and evidence-backed usage boundaries. No product bug was confirmed from the reviewed behaviors: original declaration omissions were study integration gaps, while freshness and diff exit behavior matched the installed contract. The documentation contribution is now tracked by [Docs Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11) and [Draft PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12); no product Bug Issue is alleged. Maintainer review is pending. The [contribution validation](reports/reprollm-contribution-validation.json) records four separate CPU command rehearsals against released 0.6.1 and source 0.7.0, without adding model generations to the scientific ledger. See [the reusable case study](docs/reprollm-case-study.md).


## Separately frozen second-model follow-up

This report above describes the original primary snapshot and its 5,120-generation ledger. A subsequent Local Qwen3-1.7B extension completed the same four-defense, 96-case formal design under its own model identity and batch16 freeze. Its results, copying controls, fresh repeat and cross-model limitations are in [the extension report](reports/extensions/qwen3-1.7b/REPORT.md). The [combined ledger](reports/execution-ledger.json) records 10,496 real generations in 30 GPU runs, including 6,144 formal responses. The scientific code and original protocol remain unchanged.
