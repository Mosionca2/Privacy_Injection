# Automated public-evidence checks

The [Published evidence workflow](../../.github/workflows/evidence.yml) checks every main push, pull request and manual dispatch on an Ubuntu CPU runner with Python 3.12. It installs only the [pinned evidence/reader dependencies](../../requirements.ci.txt). Model weights and inference packages are not needed.

The workflow checks the full published inventory: **43 GPU captures, 243 input-snapshot hashes, 11,160 result-row appearances and 11,136 distinct completed responses**. Formal responses remain 6,144. It recomputes stored scores with the frozen study scorer and compares the fresh complete verification result against the committed delivery receipt. Full Git history is required to check the earlier calibration sources; historical source is read rather than executed. The checkout configuration follows the [official full-history option](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/README.md#fetch-all-history-for-all-tags-and-branches).

## Actual ReproLLM use

The reader is upstream source commit `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`, module version 0.7.0. Before importing it, the gate checks the checkout commit and all **148 package-file hashes** against the source identity retained with the GPU campaign. The CLI process also checks its actual imported module path and version. Installed distribution metadata remains 0.6.1; selecting the source reader does not rewrite the archived writers' identities.

The real ReproLLM CLI performs two local run-versus-itself diffs:

| Archived run | Input schema | Matching fields | Changes |
|---|---:|---:|---:|
| Initial primary calibration, batch1 | 1 | 126 | 0 |
| Source recovery, primary uninterrupted reference | 2 | 134 | 0 |

Both commands exited 0 in the [local integration receipt](local-reader-and-evidence.json). The complete archived run directories were hashed before and after reading and remained unchanged. These checks establish bounded archived-record reading and self-diff compatibility. The earlier scientific cross-condition diffs remain separately published; self-diff alone does not validate drift detection for changed runs or retroactively strengthen schema-1 input capture.

## Validation and operation

All **40 local repository tests** passed; the [unit receipt](local-unit-checks.json) records the command and timing. CI runs the **30 CPU tests** for scoring, published evidence, recovery-controller behavior and recorder-source guards. The other ten workspace-preparation/metadata tests run in the existing scientific environment because they inspect installed inference-dependency metadata. A new regression case rejects changed or added package bytes despite an unchanged commit/version, as well as a wrong source commit.

GitHub actions are pinned by complete commit SHA. The job has read-only repository permission, does not persist checkout credentials, and uploads only its generated verification receipts and test output with 14-day retention. It uses no repository secrets. The server environment and frozen scientific files are unchanged.

To reproduce the CPU gate from a full study clone with `requirements.ci.txt` installed and the pinned upstream checkout available:

```sh
PYTHONPATH=tests python -m unittest -v test_ci test_core test_evidence test_gpu_resume test_source_recorder
python tools/ci_verify.py --consumer-source /path/to/pinned/ReproLLM
```

The integration command writes to ignored `raw/ci/`. It fails if the consumer source bytes change, the published evidence is inconsistent, the delivery receipt is stale, either reader fails, or a reader changes an archived run directory. A GitHub run will be checked after this workflow is first pushed; this local checkpoint does not claim a remote CI result.

This maintenance step adds **zero model generations**. It is an internal-consistency and consumer check, without model-weight verification, statistical-figure regeneration, independent scientific replication or a complete upstream product-quality gate. The [accepted upstream contribution](https://github.com/EnumaElish123/ReproLLM/pull/12) remains merged and [Issue #13](https://github.com/EnumaElish123/ReproLLM/issues/13) remains closed after the documented clarification. The case-index proposal has no new maintainer response at this checkpoint; no new product defect was found in these reader checks.
