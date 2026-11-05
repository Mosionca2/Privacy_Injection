# Delivery status and evidence map

As of 2026-11-04, the two-snapshot study and the documented ReproLLM workflow follow-ups are complete. This page indexes the public results and their limits.

## Completed work

| Deliverable | Published result | Evidence |
|---|---|---|
| Primary local snapshot | Four formal defense conditions, 3,072 formal responses and a fresh 768-response repeat | [Research report](../../REPORT.md), [completion ledger](../completion.json) |
| Second local snapshot | Separately frozen four-condition study, 3,072 formal responses and a fresh 768-response repeat | [Research report](../extensions/qwen3-1.7b/REPORT.md), [completion ledger](../extensions/qwen3-1.7b/completion.json) |
| Statistical outputs and figures | Per-defense results, attack/position comparisons, paired intervals, capability controls and resource observations | [Primary analysis](../formal/summary.csv), [second-snapshot analysis](../extensions/qwen3-1.7b/formal/summary.csv), [report and figures](../../REPORT.md) |
| Neutral-tail control | Separate frozen follow-up with 5,760 responses, including 4,608 follow-up test responses; token-matched neutral and reminder conditions | [Follow-up report](../tail-ablation-v1/REPORT.md), [completion ledger](../tail-ablation-v1/completion.json) |
| ReproLLM execution and provenance | Actual run IDs, committed condition declarations, bindings, offline locks, audit findings, cross-condition CLI diffs and explicitly selected exports | [Functional evidence index](REPORT.md#functional-coverage-and-evidence), [case study](../../docs/reprollm-case-study.md) |
| Recorder version boundaries | Released 0.6.1/schema 1 and pinned source 0.7.0/schema 2 are documented separately, with runtime import witnesses | [Source recorder validation](../source-recorder-validation/REPORT.md), [source recovery](../source-recovery-validation/REPORT.md) |
| Interruption and repair | Controlled SIGTERM recovery, CPU termination semantics, copy-only tail preservation/refusal and real GPU child-kill repair/resume against fresh references | [Released recovery](../recovery-validation/REPORT.md), [termination checks](../termination-validation/REPORT.md), [repair checks](../tail-repair-validation/REPORT.md), [GPU repair/resume](../gpu-tail-recovery-validation/REPORT.md) |
| Upstream contribution | Documentation accepted in PR #12; Issues #11 and #13 closed. Maintainer help and agent assistance are disclosed | [Contribution receipt](../reprollm-contribution-validation.json), [case study](../../docs/reprollm-case-study.md#accepted-upstream-documentation-contribution) |
| Ongoing evidence checks | Offline result accounting, frozen-score recomputation, source hashes, archived schema reading and CPU workflow checks | [Verification inventory](evidence-verification.json), [CI workflow](../../.github/workflows/evidence.yml), [closeout receipt](closeout-validation.json) |

The repository accounts for **17,152 distinct completed model responses across 61 GPU captures**: 56 completed captures and five deliberately interrupted captures. The original **6,144 formal responses** and the separate **4,608 follow-up test responses** are not pooled. CPU tool fixtures and repeated appearances of retained responses are excluded from the distinct model-response total. The [execution ledger](../execution-ledger.json) defines the campaign boundaries.

The validated implementation `9780e6ff4f45c2d8b8d13d082238c7e22ec9f15d` passed [59 local tests](../gpu-tail-recovery-validation/unit-checks.json) and [49 CI unit tests](https://github.com/Mosionca2/Privacy_Injection/actions/runs/41766034328). Its CI also verified all published model captures, all 148 pinned ReproLLM package files, unchanged schema-1/schema-2 archive reading, eight fresh CPU termination recordings and six fresh CPU tail-repair recordings. These are maintenance checks and add no model responses. The documentation closeout reruns the evidence and archived-reader check; it does not rerun inference or the full local suite.

## External decision still pending

The [case-index proposal](https://github.com/EnumaElish123/ReproLLM/issues/11#issuecomment-6593163665) is submitted. Acceptance into an upstream case index has not been confirmed. The [existing fork](https://github.com/Mosionca2/ReproLLM) and upstream main were both rechecked at `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`; [PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12) is merged. No new maintainer response or product defect was found in this closeout. No duplicate Issue or PR was opened.

This is one agent-assisted research project. Maintainer assistance covered documentation review, workflow authorization and merge; it did not independently replicate the scientific experiments. The accepted documentation contribution does not establish independent adopters, long-term deployment or paper citations. Only the linked public material is offered as case evidence.

## Optional extensions and limits

- Commercial-provider experiments remain optional and have not been run.
- Actual power loss, naturally torn writes and arbitrary-corruption recovery have not been tested. The GPU repair/resume case appends an explicitly constructed unfinished suffix after the owned model writer exits.
- Local model upstream revisions and original-versus-modified status remain unknown; results bind the exact published fingerprints. Four A100 80GB devices were used, without validation under a 5–8GB hardware limit.
- Offline local-weight locks retain their documented partial scope. Full local-model fingerprints were checked separately; the lightweight verifier does not rehash model weights or independently rerun scientific inference.
- Neutral-tail results do not show a consistent additional advantage from the reminder across both snapshots. Lower leakage must be read alongside authorized-copy capability; see the [follow-up interpretation](../tail-ablation-v1/REPORT.md).

Further experiments require a separately defined question and protocol. They are not unfinished items in the completed study above. A new upstream contribution should address a concrete reproducible issue or reusable improvement.

## Recheck

Use a full Git clone so historical scientific source is available. With the documented evidence dependencies and the exact ReproLLM source checkout available:

```sh
python tools/ci_verify.py --consumer-source /path/to/pinned-reprollm --output raw/ci
```

The required source commit is `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`. The command verifies the existing evidence and invokes the actual pinned ReproLLM reader on both archive schemas. It preserves archived bytes and performs no model inference. The GitHub workflow additionally runs the CPU tests and termination/repair matrices on every main push.

## New user-directed extension

On 2026-11-05, a separately scoped [project-rule lifecycle validation](../rule-lifecycle-validation/protocol.json) was defined. It covers removal, recovery archives, restoration, refusal behavior and lock freshness using CPU fixtures. The [completed validation](../rule-lifecycle-validation/REPORT.md) retains three actual source CPU recordings, twenty inner CLI commands and the released-capability boundary. All 62 local tests pass. It adds no model responses and preserves the completed scientific study.
