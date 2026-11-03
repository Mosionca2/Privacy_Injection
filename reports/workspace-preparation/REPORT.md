# Extension workspace preparation validation

## Result and cause

The research adapter now prepares a new model-study workspace from a checkout that already contains committed ReproLLM metadata. The previous adapter called the frozen original `privacy_study.record.workspace`, which unconditionally ran `reprollm init`; the installed CLI correctly refused to overwrite the cloned manifest with exit 2. This was an integration regression after recording metadata became part of main, not a confirmed ReproLLM product defect.

The failing source was `76392b0d95bcb4d44a8e70ce755c4e17b7cbd729`. The repaired source and actual setup check use `e3731fccfca6a1de00a936a9d37ca1119531e0c2`. [The structured receipt](validation.json) records commands, exit statuses, timing and input identities. Full local logs and the disposable validation condition remain private.

## Behavior and regression coverage

The extension adapter initializes only an uninitialized clone. It preserves matching rule bytes, adds missing required rules without discarding unrelated rules, and rejects a conflicting field, severity or CLI binding. It removes an inherited lock so that the new declaration must be locked explicitly. Existing destination directories are refused and preserved for their own recovery procedure. All changes are confined to the new disposable clone.

Five added regression cases exercise existing metadata, fresh setup, partial rule sets, conflicting rules and destination preservation. They use local Git repositories, synthetic model metadata and the actual installed CLI without network access or inference. The complete repository suite passed **25 tests**. The frozen scientific source files, primary formal freeze and shared extension inputs remain unchanged.

## Actual local-model setup check

An isolated D1/dev workspace was prepared with batch16 and one selected base case, using the already available exact local 1.7B snapshot. Preparation verified all 9 identity files (4,079,423,234 bytes); assets were hard-linked rather than downloaded. The existing three rule definitions were preserved byte-for-byte, and the source manifest, lock, rules and freezes were unchanged.

The inherited lock was absent before creating a new `reprollm lock . --offline --hash-large-files`. The new lock records fully hashed local weights; `reprollm lock . --check` returned 0. The condition inputs were committed locally and both the source and condition were clean. The existing OSNIP distribution remains ReproLLM 0.6.1 with no environment replacement.

This is setup validation: **0 model generations and 0 new run captures**. The repository ledger remains 10,624 completed responses across 33 GPU captures, including 6,144 formal responses. The prepared command was not executed as model inference. This check makes no source-0.7.0 GPU or hard-kill recovery claim.

## Upstream contribution outcome

[ReproLLM PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12) was merged as `ad8b2c7057b6473072b65102eaf8e122b647acec`, and Issue #11 is closed. [CI attempt 2](https://github.com/EnumaElish123/ReproLLM/actions/runs/41445173597) passed five platform jobs at contribution head `5ddbf4b`. The Mosionca2 fork main was synchronized with that upstream merge. [The contribution receipt](../reprollm-contribution-validation.json) distinguishes original local checks, the initial approval-pending state and the final successful CI/review outcome.

Maintainer assistance covered document placement/content review, workflow authorization and merge. It did not independently replicate the scientific experiment. The adapter repair belongs to this research repository and does not justify another upstream bug report.
