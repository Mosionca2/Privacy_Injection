# Copy-only result-tail recovery

This stage implements the study's unfinished-JSONL-tail handling as a separate utility. [The usage guide](../../docs/result-tail-repair.md) explains inspection, the trusted identity, required source digest, recovery bundle and explicit refusal cases. The source file is never edited. Complete samples and failure records stay byte-identical in the repaired prefix; the excluded unfinished bytes stay in the backup and tail file.

Validation uses copies of the first eight genuine sample rows from the published primary neutral-tail development run. A deliberately synthetic complete failure marker and controlled unfinished suffix exercise preservation. A second controlled input ends with complete failure JSON lacking only its newline and must be refused. These are fixture modifications, not newly generated model outcomes or observed disk/power-loss events.

The actual CLI matrix covers inspection, copy repair and refusal under installed ReproLLM 0.6.1 and pinned source 0.7.0 at `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`. Each condition uses its own committed declaration, project rules and fresh offline lock. Inspection/repair mode and the input file are bound to the executed flags. The source package is verified against all 148 recorded hashes; per-condition import witnesses distinguish the source module from installed distribution metadata.

The seven regression cases cover backup/prefix/failure-byte preservation, inspection side effects, complete unterminated records, damage inside complete lines, identity/JSON ambiguity and duplicate successes, stale inspection digests/existing bundles, and clean-checkpoint no-ops. Identity checks preserve JSON types, so `true` and `1` do not compare as the same configuration. The initial review exposed and fixed that Python equality pitfall before publication; its earlier fixture artifacts remain private and are not the final acceptance.

All **54 local repository tests** pass; [the unit receipt](unit-checks.json) binds them to the corrected utility. The corrected [local matrix](local-results.json) completed six genuine CPU recordings:

| Engine | Operation | Child exit | Saved status | Result |
|---|---|---:|---|---|
| Released 0.6.1 | Inspect | 0 | completed | No bundle or input changes |
| Released 0.6.1 | Repair copy | 0 | completed | Eight original successes and one synthetic failure preserved |
| Released 0.6.1 | Refuse complete unterminated failure | 2 | completed | Input preserved; no bundle |
| Pinned source 0.7.0 | Inspect | 0 | completed | No bundle or input changes |
| Pinned source 0.7.0 | Repair copy | 0 | completed | Eight original successes and one synthetic failure preserved |
| Pinned source 0.7.0 | Refuse complete unterminated failure | 2 | completed | Input preserved; no bundle |

Both producers correctly retain `status: completed` with the nonzero child exit 2. Selected exports and real [released](released-mode-diff.json)/[source](source-mode-diff.json) inspection-versus-repair CLI diffs passed. Source outcome filtering includes the refused attempt as a failure. The frozen scientific resume reader retained the eight original successful IDs from each repaired copy. This reader compatibility check performs no inference.

The [curated evidence](../../evidence/tail-repair-validation/) retains input derivations, actual declarations/locks, tool source, runtime witnesses, original run directories, captured output, explicit exports and complete recovery bundles. [The publication inventory](publication.json) covers 122 selected files and eight recorded output-artifact hashes. Original model result files and original run-directory bytes were preserved. Fixture Git commits identify disposable local repositories; the selected input/snapshot bytes are published without claiming those private Git objects can be fetched from research main.

[GitHub run #41602335343](https://github.com/Mosionca2/Privacy_Injection/actions/runs/41602335343) passed **44 CPU unit tests**, the unchanged 55-capture model-evidence gate, archived-record reading, eight actual CPU termination fixtures and six fresh repair/refusal CLI captures at implementation commit `980c1ba`. [The permanent CI receipt](github-ci.json) and [downloaded repair matrix](github-results.json) distinguish its run IDs from the local captures. Later evidence/report commits receive their own CI runs. CI creates no model responses.

This is a research-output utility, not a change to ReproLLM's run-record recovery contract. The model-resume reader is checked by reading the repaired copy and retaining its eight original success IDs; no model is loaded or resumed. Complete failure markers are preserved, not scored as successes. Minimal CPU manifests declare no model, so their exported current-tree audits can report absent model fields; they are not presented as clean model experiments.

No source file is automatically installed into an experiment. Live-writer exclusion, arbitrary corrupt records, incomplete UTF-8/number/escape fragments, GPU corruption/resume and power-loss durability remain outside the tested scope. Existing scientific freezes and all original model records remain unchanged. The repository still contains **16,896 completed model responses across 55 GPU captures**, including 6,144 original formal responses and 4,608 separately scoped follow-up test responses. Each CPU/CI execution has its own fixture run IDs and adds zero model generations.

The existing [fork](https://github.com/Mosionca2/ReproLLM), [merged PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12) and [closed specification clarification #13](https://github.com/EnumaElish123/ReproLLM/issues/13) were rechecked for context. The last case-index comment remains the same project's dated evidence update, without a new maintainer response at this checkpoint. The observations do not establish a new upstream product defect, so no duplicate Issue, PR or outreach is created.
