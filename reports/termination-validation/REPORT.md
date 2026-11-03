# Forced-termination recording boundaries

This stage uses real, bounded Linux CPU commands to check released ReproLLM 0.6.1 and pinned source 0.7.0 at `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`. It adds no model inference. [The protocol](protocol.json) defines the targets and expected outcomes; [the local receipt](local-results.json) identifies all eight selected CPU captures.

| Recorder | Target of SIGKILL | Saved status | Saved child exit | Actual CLI exit | Saved input evidence |
|---|---|---|---|---:|---|
| Released 0.6.1 | Experiment child | interrupted | -9 | 247 | Schema-1 completed capture; input phase remains unknown |
| Released 0.6.1 | Recorder | running | unknown | -9 | Minimal initial record; no manifest/lock copies |
| Source 0.7.0 | Experiment child | interrupted | -9 | 247 | Schema-2 pre-child baseline and final checks |
| Source 0.7.0 | Recorder | running | unknown | -9 | Schema-2 pre-child baseline; final checks stay unavailable/unknown |

Each engine also performed two fresh successful CPU controls, with `completed`, child exit 0 and CLI exit 0. Each child computed a small checksum and wrote its real injected run ID before readiness. The POSIX CLI exit 247 is the process exit corresponding to `SystemExit(-9)`; the saved experiment-child exit remains -9. A recorder killed directly has process exit -9, while its unfinished record has no confirmed child exit.

## What was checked

Each independent condition had its own declaration, project rule, offline lock and committed fixture inputs. The source checkout commit and 148 package hashes were verified before materializing the process-local source package. No environment upgrade occurred: installed distribution metadata remains 0.6.1.

Before sending a signal, the controller checks its nonce, the child's parent PID, process group and session. Its Linux subreaper scope adopts and reaps the orphaned fixture after recorder loss. Cleanup also checks the original owned process group, so another subprocess created by the same controller cannot become a cleanup target. The child and recorder are separate signal targets. Cleanup belongs to this validation controller; it is not a ReproLLM automatic recovery feature.

Both engines listed and showed their actual records, exported each explicitly selected run, and read self-diffs or a comparison of their two fresh successful controls. Source outcome filters excluded the unfinished `running` record from both success and failure. Source latest-successful selection matched the documented start-time/run-ID ordering. Complete run-directory hashes stayed unchanged through inspection.

The [published copies](../../evidence/termination-validation/) retain run JSON, snapshots, captured logs, selected exports, query/diff results and checked CPU outputs. [The publication inventory](publication.json) maps each retained file and output hash. A successful control overwrites the fixture's shared output path; the earlier control's byte-identical captured stdout preserves its original JSON and is checked against the original recorded output hash. A recorder-kill attempt has no finalized output-hash attestation. PID/nonce readiness files and unreviewed launcher logs are not published.

In the local receipt, `input_baseline_saved` records whether a manifest snapshot reference exists. For schema 1, a present snapshot still has unknown capture phase. The pre-child guarantee applies specifically to the pinned schema-2 producer. Hardware metadata may mention installed GPUs; these CPU commands allocate no model or CUDA workload.

## Validation and corrections

The eight local recordings used the controller at implementation commit `e2bc2ee876250defd2b55a3939c9ba20a8156218`. Their saved controller hash identifies that exact implementation. The first GitHub run at the same commit [failed its final selection assertion](https://github.com/Mosionca2/Privacy_Injection/actions/runs/41588858334): unlike the slower local execution, the two CI controls started in the same recorded second. The controller incorrectly expected launch order; ReproLLM correctly used run ID as the documented tie-breaker.

Correction `91dd8a7f68d9a0235a90973e727233b965d71fd0` changes only that expected ordering and adds a deterministic same-second regression case. An earlier local ownership test also caught the controller's missing cleanup group check; that was fixed before the eight selected local captures. Superseded trial artifacts remain private and are not accepted results. Neither finding is attributed to a ReproLLM product defect.

The final local repository suite passes **42 tests**, including the two new guards; [the unit receipt](unit-checks.json) binds it to the corrected controller. Current CI runs **32 CPU unit tests**, the full 43-capture scientific-evidence gate, archived schema-1/schema-2 reading, and a fresh eight-record CPU termination matrix. [Corrected run #41589563151](https://github.com/Mosionca2/Privacy_Injection/actions/runs/41589563151) passed at `91dd8a7`: all 32 tests and its eight new CPU captures passed. The [permanent CI receipt](github-run.json) and [downloaded matrix results](github-results.json) record that execution separately from the local captures. The scientific evidence receipt remains identical to the published checkpoint. Later report commits receive their own CI runs.

Run the matrix in an existing compatible environment, using a fresh ignored workspace:

```sh
python tools/validate_termination.py --consumer-source /path/to/pinned/ReproLLM --workspace raw/termination --output raw/termination-results.json
```

## Scope and upstream status

These results match the [pinned run contract](https://github.com/EnumaElish123/ReproLLM/blob/f7bd2ad7686ff603f8508d9eedfb919d35edb8e9/docs/run.md) and [selection contract](https://github.com/EnumaElish123/ReproLLM/blob/f7bd2ad7686ff603f8508d9eedfb919d35edb8e9/docs/diff.md). A saved `running` state is incomplete evidence after recorder loss, not live process monitoring or an inferred success. Query and export do not repair it. The minimal CPU declarations intentionally contain no model; missing model/dependency findings in an export's current-tree audit are retained rather than presented as a clean model experiment.

The [Mosionca2 fork](https://github.com/Mosionca2/ReproLLM) and [accepted PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12) remain the existing contribution route. [Issue #13](https://github.com/EnumaElish123/ReproLLM/issues/13) remains closed after its documentation clarification. The reader/termination observations do not establish a new upstream defect, so no duplicate Issue or PR is submitted. The existing case-index proposal still has no new maintainer response at this checkpoint. All implementation and validation here are agent-assisted, without a new independent maintainer replication.

The scientific ledger remains **11,136 completed model responses, 43 GPU captures and 6,144 formal responses**. CPU captures are separate and every fresh CI execution creates its own fixture records. This is not a GPU SIGKILL recovery experiment, power-loss/disk-durability test, corrupted-output repair, or model rerun. Local fixture commits identify their disposable repositories; the published inputs and snapshots are retained, without claiming those private Git objects are fetchable from the research main branch.
