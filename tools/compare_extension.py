"""Compare two completed local snapshots on shared cases; preserve model identities."""
import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacy_study import core as c
from tools.prepare_extension import validate_study


def compare(study, output):
    study, output = Path(study), Path(output)
    validate_study(study)
    cases = c.load_cases(ROOT, 'test')
    sources = {
        'primary': ROOT / 'evidence/formal',
        'extension': ROOT / 'evidence/extensions' / study.name / 'formal',
    }
    grouped, identities = {}, {}
    for label, directory in sources.items():
        grouped[label], identities[label] = {}, {}
        for defense in c.DEFENSES:
            file = directory / defense / 'results.jsonl'
            identity = json.loads(file.read_text().splitlines()[0])['identity']
            if identity['split'] != 'test' or identity['defense'] != defense:
                raise ValueError('Wrong formal condition identity.')
            rows = c.completed_rows(file, identity)
            grouped[label][defense] = c.per_case(rows, cases)
            identities[label][defense] = identity
        for key in ('protocol', 'dataset', 'code', 'model', 'versions', 'batch_size', 'cases'):
            if any(identities[label][d][key] != identities[label]['D0'][key] for d in c.DEFENSES):
                raise ValueError(f'Mixed within-model scientific input: {key}')
    for key in ('dataset', 'code', 'versions', 'cases', 'dtype', 'thinking'):
        if identities['primary']['D0'][key] != identities['extension']['D0'][key]:
            raise ValueError(f'Unplanned cross-model scientific drift: {key}')
    if identities['primary']['D0']['model'] != c.read_json(ROOT / 'model.identity.json'):
        raise ValueError('Primary model identity mismatch.')
    if identities['primary']['D0']['protocol'] != c.digest(ROOT / 'configs/protocol.json'):
        raise ValueError('Primary protocol mismatch.')
    if identities['extension']['D0']['model'] != c.read_json(study / 'model.identity.json'):
        raise ValueError('Extension model identity mismatch.')
    if identities['extension']['D0']['protocol'] != c.digest(study / 'protocol.json'):
        raise ValueError('Extension protocol mismatch.')
    rows = []
    for defense in c.DEFENSES:
        for metric in ('leak', 'clean_acc', 'safe_utility'):
            rows.append(dict(defense=defense, metric=metric,
                **c.paired_interval(grouped['primary'][defense], grouped['extension'][defense], metric)))
    c.csv_file(output / 'cross-model-paired-differences.csv', rows)
    combined = []
    for label in sources:
        path = ROOT / ('reports/formal/analysis.json' if label == 'primary' else
                       f'reports/extensions/{study.name}/formal/analysis.json')
        analysis = c.read_json(path)
        combined += [dict(model=identities[label]['D0']['model']['model_label'], **row) for row in analysis['summary']]
    c.csv_file(output / 'cross-model-summary.csv', combined)
    common = {case['id'] for case in cases if all(
        grouped[label]['D0'][case['id']]['clean_acc'] and
        grouped[label]['D0'][case['id']]['auth_recall'] for label in sources)}
    common_rows = []
    if common:
        for label in sources:
            for defense in c.DEFENSES:
                common_rows.append(dict(model=identities[label]['D0']['model']['model_label'],
                    defense=defense, n_cases=len(common), **{
                        metric: statistics.mean(grouped[label][defense][i][metric] for i in common)
                        for metric in ('clean_acc', 'auth_recall', 'leak', 'safe_utility')}))
        c.csv_file(output / 'common-capability-summary.csv', common_rows)
    c.write_json(output / 'cross-model-comparison.json', {
        'schema_version': 1, 'case_count_per_model': len(cases),
        'formal_generations': 6144, 'direction': 'extension minus primary',
        'scope': 'Exploratory paired comparison across two exact local model/tokenizer snapshots. Primary-model test outcomes were already known. This does not isolate parameter count or establish a scaling law.',
        'batch_sizes': {label: identities[label]['D0']['batch_size'] for label in sources},
        'model_identities': {label: identities[label]['D0']['model'] for label in sources},
        'common_capability_cohort': {'n_cases': len(common), 'case_ids': sorted(common),
            'definition': 'D0 clean task and authorized-copy control both succeed in both models. The same intersection is used for every defense.'},
        'shared_input_checks_passed': True, 'paired_differences': rows,
    })
    return combined


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    print(json.dumps(compare(a.study, Path(a.output)), indent=2))
