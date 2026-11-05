# Project-rule removal, recovery archives and restoration

This user-directed extension tests ReproLLM project-rule lifecycle behavior using three isolated CPU fixtures. The [protocol](protocol.json) was committed before execution at `8cd69a7`. It adds **three selected source CPU recordings and zero model responses or GPU captures**. The completed scientific study and its ledger remain unchanged.

## Results

| Scenario | Actual inner CLI commands | Observed result |
|---|---:|---|
| Normal roundtrip | 14 | Removal retains the complete recovery copy; removed-rule and restored-rule states invalidate their respective locks; refreshing restores freshness. Duplicate restoration exits 2. |
| Conflicting active rule | 4 | Restoring the archived rule exits 2 and changes no active rules, archive or lock. Attempting to remove a built-in ID also exits 2. |
| Controlled archive modification | 2 | A changed removal reason with the original content ID is rejected with exit 2; the damaged copy and active rules are preserved. |

All three outer validation drivers exit 0 because their expected outcomes, including the deliberately refused inner commands, were observed. The [selected records](local-results.json) retain actual run IDs, command exits and input changes. A successful outer fixture is not a claim that every inner CLI request succeeded.

## Preserved state and version scope

The manual rule retains its ID, field, severity, original rule reason, source, null candidate ID, approval timestamp and all three CLI/config/environment bindings. Each capture observes the same synthetic defense through all three sources. The child also reads those values, while the recorder's consumption field correctly remains `unverified`.

The recovery content ID is recomputed independently using the canonical JSON rule in the pinned specification section 7.2. Restoration is checked against the complete original rule, with byte inventories for current rules, lock, archives and immutable experiment inputs. The archive itself remains unchanged. The deliberate archive modification uses an isolated copy with its original retained under `inputs`; it is not a real data-loss incident or an origin-authentication guarantee.

Source `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9` (module 0.7.0, run schema 2) produced all three records. The installed distribution remains 0.6.1. The [local installed-CLI help probe](released-rules-help.txt) does not list `remove` or `restore`, so these source features are not presented as released-0.6.1 acceptance. No packages were replaced and no model assets or paid endpoints were used.

## Input and Git phase boundaries

The normal roundtrip produces a real recorded dirty Git state: it refreshes a tracked lock and creates a new recovery archive. Inputs were clean and committed before launch, and their original captured bytes are independently compared with that commit. The initial assessor incorrectly required the recorded Git state to remain clean. All three actual children had already succeeded; the assessor was corrected and those original records were evaluated without repeating them. Their original metadata, including the dirty flag and patch, is preserved.

The normal rule file returns to its initial bytes after removal and restoration. Consequently the pre/post input check reports it unchanged, despite the independently saved intermediate inactive state. Only the lock differs at the end of this actual recording. This demonstrates the boundary of pre/post comparison; it does not establish continuous monitoring. Refreshing the lock while the rule is inactive is necessary for the restored-rule staleness test, since the restored original rules may legitimately match an older lock.

## Published evidence and validation

The [publication inventory](publication.json) lists the 86 reviewed fixture files and their hashes. Original recorder directories remain byte-identical; selected exports identify the actual run. CLI command output in `result.json` replaces the disposable workspace root with `<workspace>` and retains digests of the original private output. The original per-command logs remain in the private execution workspace. Snapshots and rule archives retain their exact bytes. The published released-help text has terminal padding removed; its original output remains private.

The [independent verifier](../../tools/verify_rule_lifecycle.py) checks snapshot and artifact hashes, runtime/source identity, three-source observations, independent before/after inventories, derived archive states, required exit codes and complete restored-rule semantics. The [62-test local receipt](unit-checks.json) includes regressions that reject a falsely relabeled refusal and a lost archive binding even after the affected artifact digests are updated. It also accepts the truthful post-run Git changes in the positive case.

The [CI workflow](../../.github/workflows/evidence.yml) verifies these published records and creates three new CPU lifecycle captures on each main push, alongside its existing evidence, termination and tail-repair checks. Exact delivery-head CI is checked after push. Its CPU fixtures add no model responses. This consumer validation does not qualify an upstream release or replace upstream quality/resource gates.

No new product defect was confirmed. The assessment-phase mistake belonged to this consumer harness; the source CLI behavior matches its documented lifecycle contract. Existing upstream contributions remain in the [case study](../../docs/reprollm-case-study.md); no duplicate Issue or PR is submitted for expected behavior.
