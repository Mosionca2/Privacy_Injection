# GPU child SIGKILL and controlled checkpoint-tail recovery

This bounded follow-up connects a real killed model child to backed-up JSONL repair and actual resumed inference on two exact local snapshots. The unfinished suffix is deliberately appended after the writer exits. It does not demonstrate naturally torn writes or power-loss durability. The committed [protocol](protocol.json) precedes all six GPU captures; the original scientific code, data, defenses, freezes and environment remain unchanged.

## Observed results

| Snapshot | Completed before kill | New after repair/resume | Fresh reference | Changed outputs | Changed scores |
|---|---:|---:|---:|---:|---:|
| Local 1.7B snapshot | 8 | 56 | 64 | 0 | 0 |
| Local 8B snapshot | 8 | 56 | 64 | 0 | 0 |

The campaign adds **256 completed development responses in six GPU captures**: four completed and two interrupted. Both model children actually exit **-9**, while the recorder CLI exits **247** and saves status `interrupted`. Four separate successful CPU recordings run the actual inspection and repair CLI; they add zero model responses and are excluded from GPU counts. Interrupted in-flight computation is also excluded. The [comparison](comparison.json) preserves all actual run IDs and counts.

## Reproducible byte chain

1. Each recovery condition starts from clean, independently committed inputs. A Linux process descriptor identifies only the immediate scientific child after checking its exact command, directory, parent, process group and session. Negative CPU guards reject other commands/directories before signalling. The recorder remains alive to save the real child outcome.
2. The complete interrupted JSONL is archived before modification. Its trusted identity and all complete successes are retained. This protocol would stop for separate review if the kill itself left an unfinished line; neither actual interrupted file did.
3. After the owned writer exits, the declared synthetic unfinished suffix is appended. Independent CPU declarations bind that damaged checkpoint, the trusted identity, derivation and repair code. Actual pinned-source ReproLLM runs record inspection and copy-only repair, with the inspected source hash required by repair.
4. Each new bundle keeps the exact damaged backup, original complete prefix, excluded tail and a receipt bearing the actual repair-tool run ID. The damaged input is unchanged. Only after these checks does the controller install the repaired prefix in the stopped model workspace; the original and damaged checkpoints remain retained.
5. The unchanged scientific command resumes only missing successful IDs. The final file retains every original byte and originating run ID, covers all 64 unique samples and is compared against an independent 64-response reference with the same scientific identity. Output and score differences are reported above rather than assumed.

The [offline verifier](../../tools/verify_gpu_tail_recovery.py) rechecks this chain, input-snapshot hashes, command bindings, source import witnesses, original recorded output-artifact hashes, repair receipts and selected exports. Tampering with a backup, public checkpoint or signal target is covered by regression tests. The [publication inventory](publication.json) lists all reviewed files. GPU text-log newline normalization is disclosed; original GPU run JSON and all CPU run-directory bytes remain unchanged, and model/repair output artifact hashes are independently checked.

## Actual ReproLLM use and upstream status

All ten new recordings use source `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`, module 0.7.0/schema 2. Installed distribution metadata remains 0.6.1. The recorder source payload and complete local-model fingerprints were checked before and after. Source records retain pre-child baselines, post-child checks and unverified consumption; auxiliary-file hashing does not prove the child consumed an input. Offline lock scope retains the earlier documented local-weight limitation, supplemented by independent full model hashes.

Actual interrupted/resumed CLI diffs, repair-mode diffs, selected historical exports and current-tree GPU audits are retained. Audits taken after each pair completed describe that current tree/latest run; they are not historical re-audits of the killed attempt. Resume and tail repair belong to this study; ReproLLM supplies records and provenance.

The existing [fork](https://github.com/Mosionca2/ReproLLM), [Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11), merged [PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12) and closed [clarification #13](https://github.com/EnumaElish123/ReproLLM/issues/13) were rechecked on 2026-11-04. There was no new maintainer feedback on the existing case-index thread or confirmed product defect. This extension therefore uses the tool and publishes concrete evidence without submitting duplicate Issues or PRs. It remains one agent-assisted project, without an independent-adopter or maintainer-replication claim.

## Limits

This small D0/development recovery exercise does not change the formal defense findings or establish general crash safety, concurrent-writer exclusion, power-loss durability, recovery from arbitrary corruption, or commercial-provider behavior. Complete failure records must remain preserved; their refusal/preservation cases are covered separately by the [copy-only tool matrix](../tail-repair-validation/REPORT.md), not injected into the present model counts.

## Validation

The complete local suite passes 59 tests with zero failures, errors or skips. The [unit receipt](unit-checks.json) records the actual run. A separate [local consumer check](local-consumer.json) verifies the complete published ledger, all 148 pinned package files and actual unchanged schema-1/schema-2 archived-run self-diffs. No inference is performed by these maintenance checks.
