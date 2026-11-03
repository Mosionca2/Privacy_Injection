"""Check published capture consistency and response accounting without inference."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacy_study import core as c
from tools.validate_source_recorder import check_input_capture


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_file(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    require(not Path(name).is_absolute() and path.is_relative_to(root),
            'Evidence path must stay within its root.')
    return path


def flag(argv, name, default=None):
    require(argv.count(name) <= 1, f'Duplicate command flag: {name}')
    return argv[argv.index(name) + 1] if name in argv else default


def verify_source(root, name, digest, commit):
    current = local_file(root, name)
    if c.digest(current) == digest:
        return False
    require(re.fullmatch('[0-9a-f]{40}', commit), 'Invalid recorded Git commit.')
    result = subprocess.run(['git', 'show', f'{commit}:{name}'], cwd=root, capture_output=True)
    require(result.returncode == 0 and hashlib.sha256(result.stdout).hexdigest() == digest,
            f'Historical source unavailable or mismatched: {name}; use a full Git clone.')
    if name == 'privacy_study/core.py':
        def scorer(source):
            return next(ast.dump(node, include_attributes=False) for node in ast.parse(source).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'score')
        require(scorer(result.stdout) == scorer(current.read_bytes()),
                'Historical scoring definition differs; separate scoring validation is required.')
    return True


def check_capture(root, directory):
    root, directory = Path(root).resolve(), Path(directory).resolve()
    require(c.digest(root / 'privacy_study/core.py') == c.digest(Path(c.__file__)),
            'Selected repository scorer differs from this verifier; use its matching checkout.')
    relative = directory.relative_to(root).as_posix()
    run = c.read_json(directory / 'run/run.json')
    snapshots = [run['manifest'], run['lock'], *run['files']]
    for item in snapshots:
        require(item.get('snapshot') and not item.get('redacted', False),
                f'Unsupported missing/redacted input snapshot: {relative}')
        path = local_file(directory / 'run', item['snapshot'])
        require('sha256:' + c.digest(path) == item['sha256'],
                f'Snapshot hash mismatch: {relative}/{item["snapshot"]}')
    result_bytes = (directory / 'results.jsonl').read_bytes()
    require(result_bytes.endswith(b'\n'), f'Incomplete final result line: {relative}')
    documents = [json.loads(line) for line in result_bytes.splitlines()]
    require(documents[0]['type'] == 'meta', f'Missing identity header: {relative}')
    identity, rows = documents[0]['identity'], {}
    for row in documents[1:]:
        require(row['type'] == 'sample', f'Non-success result row: {relative}')
        require(row['id'] not in rows, f'Duplicate sample: {relative}/{row["id"]}')
        rows[row['id']] = row
    split, defense, batch = (identity[key] for key in ('split', 'defense', 'batch_size'))
    manifest = yaml.safe_load(local_file(directory / 'run', run['manifest']['snapshot']).read_text())
    argv = run['command']['argv']
    require('privacy_study.run' in argv, f'Unexpected experiment entry point: {relative}')
    declared = shlex.split(manifest['execution']['command'])
    for key, value, option in (('defense', defense, '--defense'),
                               ('dataset_split', split, '--split'),
                               ('batch_size', batch, '--batch-size')):
        require(manifest['custom'][key] == value
                and flag(argv, option) == str(value) and flag(declared, option) == str(value),
                f'Declared/command condition mismatch: {relative}/{key}')
        require([v['value'] for v in run['bindings_observed'][f'custom.{key}']] == [value],
                f'Observed condition mismatch: {relative}/{key}')
    all_cases = c.load_cases(root, split)
    limit = flag(argv, '--limit')
    require(flag(declared, '--limit') == limit, f'Case limit mismatch: {relative}')
    cases = all_cases if limit is None else all_cases[:int(limit)]
    require(identity['cases'] == [case['id'] for case in cases], f'Case selection mismatch: {relative}')
    require(manifest['datasets']['eval']['sampling']['n'] == len(cases),
            f'Declared case count mismatch: {relative}')
    require(identity['dataset'] == c.digest(root / f'data/{split}.jsonl'),
            f'Dataset identity mismatch: {relative}')
    historical = [name for name, digest in identity['code'].items()
                  if verify_source(root, name, digest, run['code']['commit'])]
    parts = directory.relative_to(root / 'evidence').parts
    source_case = parts[0] in ('source-recorder-validation', 'source-recovery-validation')
    source_protocol = c.read_json(root / 'reports' / parts[0] / 'protocol.json') if source_case else None
    model_study = (source_protocol['conditions'][parts[1]].get('model_study', source_protocol.get('model_study'))
                   if source_case else None)
    study = (root / 'studies' / model_study if source_case and model_study else root if source_case else
             root / 'studies' / parts[1] if parts[0] == 'extensions' else root)
    protocol = study / ('protocol.json' if study != root else 'configs/protocol.json')
    require(identity['protocol'] == c.digest(protocol)
            and identity['model'] == c.read_json(study / 'model.identity.json'),
            f'Protocol/model identity mismatch: {relative}')
    if source_case:
        condition = source_protocol['conditions'][parts[1]]
        source_doc = c.read_json(directory / 'recorder-source.json')
        witness = c.read_json(directory / 'runtime-witness.json')
        require(identity['versions']['reprollm'] == source_doc['installed_distribution_version']
                == witness['installed_distribution_version']
                and run['reprollm_version'] == source_doc['module_version'] == witness['module_version'],
                f'Recorder module/distribution version mismatch: {relative}')
        if condition['source_recorder']:
            require(source_doc['source_commit'] == source_protocol['upstream_source_commit']
                    and source_doc['module_version'] == source_protocol['source_module_version']
                    and witness['module_file'] == 'assets/recorder-source/reprollm/__init__.py'
                    and witness['module_sha256'] == next(v['sha256'] for v in source_doc['files']
                                                        if v['name'] == 'reprollm/__init__.py'),
                    f'Pinned source witness mismatch: {relative}')
        expected_changes = condition['expected_input_changes']
    else:
        require(identity['versions']['reprollm'] == run['reprollm_version'],
                f'Recorder version mismatch: {relative}')
        expected_changes = []
    input_changes = check_input_capture(run, expected_changes)
    expected = c.expected_ids(cases)
    require(set(rows) <= expected and bool(rows), f'Unexpected or empty sample coverage: {relative}')
    if run['status'] == 'completed':
        require(run['exit_code'] == 0, f'Nonzero completed child: {relative}')
        require(set(rows) == expected, f'Incomplete sample coverage: {relative}')
    else:
        require(run['status'] == 'interrupted' and run['exit_code'] != 0 and len(rows) < len(expected),
                f'Unexpected capture outcome: {relative}')
        require(not (directory / 'completion.json').exists(), f'Interrupted capture has completion: {relative}')
    by_case = {case['id']: case for case in cases}
    for row in rows.values():
        require(row['id'] == ':'.join(row[k] for k in ('case_id', 'variant', 'family', 'position')),
                f'Sample fields disagree with ID: {relative}')
        case = by_case[row['case_id']]
        require(row['task'] == case['task'] and row['scores'] == c.score(case, row['variant'], row['output']),
                f'Score mismatch: {relative}/{row["id"]}')
    new = sum(row['reprollm_run_id'] == run['run_id'] for row in rows.values())
    if run['status'] == 'completed':
        completion = c.read_json(directory / 'completion.json')
        require(completion['reprollm_run_id'] == run['run_id']
                and completion['new_generations'] == new and completion['expected'] == len(expected),
                f'Completion accounting mismatch: {relative}')
    if (directory / 'controller.json').exists():
        controller = c.read_json(directory / 'controller.json')
        require(controller['run_id'] == run['run_id'] and controller['status'] == run['status']
                and controller['child_exit_code'] == run['exit_code']
                and controller['new_completed_samples'] == new
                and controller['completed_after'] == len(rows)
                and controller['completed_before'] == len(rows) - new,
                f'Controller accounting mismatch: {relative}')
    if (directory / 'recording.json').exists():
        recording = c.read_json(directory / 'recording.json')
        require(recording['run_id'] == run['run_id'] and recording['defense'] == defense
                and recording['split'] == split, f'Recording index mismatch: {relative}')
    require(run['run_id'] in (directory / 'REPRODUCIBILITY.md').read_text(),
            f'Selected-run export missing: {relative}')
    if split == 'test':
        frozen = c.read_json(study / 'protocol.freeze.json')
        require(limit is None and batch == frozen['batch_size'] and identity['versions'] == frozen['versions'],
                f'Formal freeze mismatch: {relative}')
    summary = dict(evidence=relative, run_id=run['run_id'], status=run['status'],
                   child_exit_code=run['exit_code'], recorder_version=run['reprollm_version'],
                   run_schema_version=run['schema_version'], split=split, defense=defense,
                   model_label=identity['model']['model_label'], new_responses=new,
                   result_rows=len(rows), snapshot_hashes_checked=len(snapshots),
                   results_sha256=c.digest(directory / 'results.jsonl'),
                   capture_warning_count=len(run['warnings']),
                   historical_source_files=historical, recorded_commit=run['code']['commit'],
                   input_baseline_phase='pre_child' if run['schema_version'] == 2 else 'unknown',
                   input_changes=input_changes)
    return summary, identity, rows


def reconcile(captures):
    owners, originals = {}, {}
    for summary, identity, rows in captures:
        run_id = summary['run_id']
        require(run_id not in owners, f'Duplicate capture ID: {run_id}')
        owners[run_id] = identity
        for row in rows.values():
            if row['reprollm_run_id'] == run_id:
                originals[run_id, row['id']] = row
    for _, identity, rows in captures:
        for row in rows.values():
            key = row['reprollm_run_id'], row['id']
            require(key in originals and owners[key[0]] == identity, 'Unknown originating run or condition.')
            require(originals[key] == row, 'Retained response changed across result snapshots.')
    return len(originals)


def compare_recovery_records(partial, resumed, reference):
    """Compare complete independent coverage while retaining attempt ownership."""
    require(partial[1] == resumed[1] == reference[1], 'Recovery scientific identity mismatch.')
    old, final, fresh = partial[2], resumed[2], reference[2]
    require(set(old) < set(final) == set(fresh), 'Recovery partial/final coverage mismatch.')
    require(all(final[key] == row for key, row in old.items()), 'Recovery retained response changed.')
    require(all(row['reprollm_run_id'] == partial[0]['run_id'] for row in old.values())
            and all(row['reprollm_run_id'] == resumed[0]['run_id'] for key, row in final.items() if key not in old)
            and all(row['reprollm_run_id'] == reference[0]['run_id'] for row in fresh.values()),
            'Recovery originating attempt mismatch.')
    return dict(completed_before_interruption=len(old), resumed_new_samples=len(final)-len(old),
                reference_new_samples=len(fresh), completed_responses=len(final)+len(fresh),
                changed_outputs=sum(row['output'] != fresh[key]['output'] for key, row in final.items()),
                changed_scores=sum(row['scores'] != fresh[key]['scores'] for key, row in final.items()))


def verify(root=ROOT):
    root = Path(root).resolve()
    captures = [check_capture(root, p.parent) for p in sorted((root / 'evidence').rglob('results.jsonl'))]
    require(bool(captures), 'No published inference captures found.')
    responses = reconcile(captures)
    summaries = [capture[0] for capture in captures]
    for study in (root, root / 'studies/qwen3-1.7b'):
        frozen = c.read_json(study / 'protocol.freeze.json')
        for name, digest in frozen['files'].items():
            path = (study / 'protocol.json' if study != root and name == 'configs/protocol.json'
                    else study / name if name == 'model.identity.json' else local_file(root, name))
            require(c.digest(path) == digest, f'Frozen scientific input changed: {name}')
    ledger = c.read_json(root / 'reports/execution-ledger.json')
    for study in ledger['studies']:
        completion = c.read_json(local_file(root, study['completion']))
        model_root = root / 'studies' / completion['study_id'] if 'study_id' in completion else root
        model_label = c.read_json(model_root / 'model.identity.json')['model_label']
        require(study['model_label'] == completion['model_label'], 'Study display label mismatch.')
        observed = [s for s in summaries if s['model_label'] == model_label
                    and not s['evidence'].startswith(('evidence/recovery-validation/',
                                                      'evidence/source-recorder-validation/',
                                                      'evidence/source-recovery-validation/'))]
        require(sum(s['new_responses'] for s in observed) == study['generations']
                == completion['real_model_generations_published'], 'Study response total mismatch.')
        require(len(observed) == study['gpu_runs'] == completion['real_gpu_runs'], 'Study capture total mismatch.')
        for phase in completion['phases']:
            selected = [s for s in observed if s['evidence'].split('/')[-2] == phase['phase']]
            require({s['run_id'] for s in selected} == set(phase['run_ids'])
                    and len(selected) == phase['gpu_runs']
                    and sum(s['new_responses'] for s in selected) == phase['new_generations'],
                    f'Study phase ledger mismatch: {phase["phase"]}')
        formal = [s for s in observed if s['split'] == 'test' and '/formal/' in s['evidence']]
        require({s['defense'] for s in formal} == set(c.DEFENSES)
                and sum(s['new_responses'] for s in formal) == completion['formal_generations'],
                'Formal defense coverage mismatch.')
    recovery = {s['evidence'].split('/')[-1]: (s, identity, rows)
                for s, identity, rows in captures if '/recovery-validation/' in s['evidence']}
    comparison = c.read_json(root / 'reports/recovery-validation/comparison.json')
    require(set(recovery) == set(comparison['runs']), 'Recovery capture set mismatch.')
    for stage, (summary, _, _) in recovery.items():
        expected = comparison['runs'][stage]
        require(summary['run_id'] == expected['run_id']
                and summary['new_responses'] == expected['new_completed_samples'], 'Recovery ledger mismatch.')
    partial, resumed, reference = (recovery[name] for name in ('interrupted', 'resumed', 'reference'))
    require(partial[1] == resumed[1] == reference[1], 'Recovery scientific identity mismatch.')
    prefix = (root / partial[0]['evidence'] / 'results.jsonl').read_bytes()
    require((root / resumed[0]['evidence'] / 'results.jsonl').read_bytes().startswith(prefix),
            'Recovery result prefix changed.')
    for column, report_key in (('output', 'changed_outputs'), ('scores', 'changed_scores')):
        changed = sum(row[column] != reference[2][key][column] for key, row in resumed[2].items())
        require(changed == comparison[report_key], f'Recovery comparison mismatch: {column}')
    for campaign in ledger['validation_campaigns']:
        if campaign['completion'] == 'reports/recovery-validation/comparison.json':
            selected = [s[0] for s in recovery.values()]
            completion = comparison
        elif campaign['completion'] == 'reports/source-recorder-validation/comparison.json':
            selected = [s for s in summaries if s['evidence'].startswith('evidence/source-recorder-validation/')]
            completion = c.read_json(root / campaign['completion'])
            require({s['run_id'] for s in selected} == {v['run_id'] for v in completion['runs'].values()},
                    'Source campaign capture IDs disagree.')
            protocol = c.read_json(root / 'reports/source-recorder-validation/protocol.json')
            require({s['evidence'].split('/')[-1] for s in selected} == set(protocol['conditions']),
                    'Source campaign condition coverage mismatch.')
        elif campaign['completion'] == 'reports/source-recovery-validation/comparison.json':
            selected = [s for s in summaries if s['evidence'].startswith('evidence/source-recovery-validation/')]
            completion = c.read_json(root / campaign['completion'])
            protocol = c.read_json(root / 'reports/source-recovery-validation/protocol.json')
            require({s['evidence'].split('/')[-1] for s in selected} == set(protocol['conditions'])
                    and {s['run_id'] for s in selected} == {v['run_id'] for v in completion['runs'].values()},
                    'Source recovery campaign capture set mismatch.')
            stages = {s['evidence'].split('/')[-1]: (s, identity, rows) for s, identity, rows in captures
                      if s['evidence'].startswith('evidence/source-recovery-validation/')}
            for model, expected in completion['pairs'].items():
                partial, resumed, reference = (stages[model+'-'+stage] for stage in ('interrupted','resumed','reference'))
                actual = compare_recovery_records(partial, resumed, reference)
                require(all(expected[key] == value for key,value in actual.items()), 'Source recovery comparison mismatch.')
                require((root/resumed[0]['evidence']/'results.jsonl').read_bytes().startswith(
                        (root/partial[0]['evidence']/'results.jsonl').read_bytes()), 'Source recovery prefix changed.')
        else:
            raise ValueError('Unrecognized validation campaign; define its evidence contract explicitly.')
        require(campaign['gpu_runs'] == len(selected)
                and campaign['completed_gpu_runs'] == sum(s['status'] == 'completed' for s in selected)
                and campaign['interrupted_gpu_runs'] == sum(s['status'] == 'interrupted' for s in selected)
                and campaign['completed_responses'] == sum(s['new_responses'] for s in selected)
                == completion['completed_responses_published'], 'Validation campaign ledger mismatch.')
    totals = dict(real_model_generations_published=responses, real_gpu_runs=len(summaries),
                  formal_generations=sum(s['new_responses'] for s in summaries if '/formal/' in s['evidence']),
                  completed_gpu_runs=sum(s['status'] == 'completed' for s in summaries),
                  interrupted_gpu_runs=sum(s['status'] == 'interrupted' for s in summaries))
    require(all(ledger[key] == value for key, value in totals.items()), 'Repository execution ledger mismatch.')
    return dict(schema_version=1, all_passed=True, totals=totals, runs=summaries,
                result_rows_checked=sum(s['result_rows'] for s in summaries),
                retained_row_copies=sum(s['result_rows'] for s in summaries) - responses,
                snapshot_hashes_checked=sum(s['snapshot_hashes_checked'] for s in summaries),
                scoring='Recomputed with the frozen study scorer and published synthetic truth; historical scorer AST equality is required when core.py differs.',
                new_model_generations=0,
                limits=['Offline consistency verification, not a new model execution or external attestation.',
                        'Public run/log copies were sanitized; original run.json and output artifact hashes are not re-attested.',
                        'Model weights are not distributed or rehashed by this verifier.',
                        'A full Git clone is needed for earlier scientific source versions; historical code is read, never executed.',
                        'Bootstrap intervals and charts are not recomputed by this verifier.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify(args.root)
    if args.output:
        c.write_json(args.output, result)
    else:
        print(json.dumps(result, sort_keys=True, indent=2))
