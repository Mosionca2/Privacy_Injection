"""Prepare an isolated recording workspace for an explicitly versioned model study."""
import argparse
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacy_study import core as c
from privacy_study import record
from tools.complete_recording_metadata import complete


def validate_study(study, source=ROOT):
    study, source = Path(study), Path(source)
    spec = c.read_json(study / 'study.json')
    original = c.read_json(source / 'configs/protocol.json')
    proposed = c.read_json(study / 'protocol.json')
    allowed = {'protocol_id', 'model_label'}
    if {k: v for k, v in original.items() if k not in allowed} != {
        k: v for k, v in proposed.items() if k not in allowed
    }:
        raise ValueError('Extension changes prompts, data policy, scoring or decoding.')
    if proposed['protocol_id'] == original['protocol_id']:
        raise ValueError('A replacement model requires a distinct protocol identifier.')
    if proposed['model_label'] != c.read_json(study / 'model.identity.json')['model_label']:
        raise ValueError('Model labels disagree.')
    for name, expected in spec['shared_files'].items():
        if c.digest(source / name) != expected:
            raise ValueError(f'Shared scientific input drift: {name}')
    return spec


def prepare(study, destination, model, defense, split, batch_size, limit=None):
    study = Path(study).resolve()
    validate_study(study)
    frozen = study / 'protocol.freeze.json'
    if split == 'test' and (not frozen.exists() or limit is not None):
        raise ValueError('Formal extension needs its own freeze and all held-out cases.')
    identity = c.read_json(study / 'model.identity.json')
    c.asset_state(model, identity, verify_large=True)
    work = record.workspace(ROOT, destination, model, defense, split, batch_size, limit)
    for entry in identity['files']:
        target = work / 'assets/model' / entry['name']
        if not target.exists():
            os.link(Path(model) / entry['name'], target)
    shutil.copyfile(study / 'protocol.json', work / 'configs/protocol.json')
    shutil.copyfile(study / 'model.identity.json', work / 'model.identity.json')
    (work / 'protocol.freeze.json').unlink(missing_ok=True)
    if frozen.exists():
        shutil.copyfile(frozen, work / 'protocol.freeze.json')
    previous = Path.cwd()
    try:
        os.chdir(work)
        declared = record.manifest(defense, split, batch_size, limit)
        declared['project']['name'] = 'Privacy_Injection-' + study.name
        declared['experiment']['name'] = f'{study.name}-{split}-{defense}-b{batch_size}'
        c.write_json('reprollm.yaml', declared)
        complete(work)
    finally:
        os.chdir(previous)
    return work


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', required=True)
    p.add_argument('--destination', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--defense', required=True, choices=c.DEFENSES)
    p.add_argument('--split', required=True, choices=['dev', 'test'])
    p.add_argument('--batch-size', required=True, type=int)
    p.add_argument('--limit', type=int)
    a = p.parse_args()
    if a.batch_size < 1 or (a.limit is not None and a.limit < 1):
        p.error('Batch size and optional limit must be positive.')
    print(prepare(a.study, a.destination, a.model, a.defense, a.split, a.batch_size, a.limit))
