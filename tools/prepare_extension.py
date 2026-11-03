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


RULE_BINDINGS = (
    ('defense', '--defense'),
    ('dataset_split', '--split'),
    ('batch_size', '--batch-size'),
)


def ensure_rules(work, cli):
    from reprollm.core.project_rules import load_project_rules

    document = load_project_rules(work)
    existing = {rule.id: rule for rule in document.rules} if document else {}
    missing = []
    for field, flag in RULE_BINDINGS:
        identifier = f'project.{field}'
        rule = existing.get(identifier)
        if rule is None:
            missing.append((identifier, field, flag))
        elif (rule.field != f'custom.{field}' or rule.severity != 'CRITICAL'
              or rule.bindings is None or rule.bindings.cli != flag
              or rule.bindings.config is not None or rule.bindings.env is not None):
            raise ValueError(f'Conflicting project rule {identifier}; expected CRITICAL '
                             f'custom.{field} bound only to {flag}. Review the source rules.')
    for identifier, field, flag in missing:
        record.command([cli, 'rules', 'add', '--id', identifier, '--field', f'custom.{field}',
                        '--severity', 'CRITICAL', '--reason',
                        'This declared value must agree with actual execution.', f'--cli={flag}'], work)


def extension_workspace(source, destination, model):
    """Reuse committed recording setup only inside a new disposable clone."""
    source, work = Path(source).resolve(), Path(destination).resolve()
    if work.exists():
        raise ValueError('Use a new condition workspace, or resume its existing declaration.')
    record.command(['git', 'clone', '--quiet', '--no-hardlinks', source, work], source)
    record.command(['git', 'remote', 'set-url', 'origin',
                    'https://github.com/Mosionca2/Privacy_Injection.git'], work)
    cli = Path(sys.executable).with_name('reprollm')
    if not (work / 'reprollm.yaml').exists():
        record.command([cli, 'init', '.', '--profiles', 'inference,evaluation,privacy'], work,
                       output=work / 'raw/init.txt')
    ensure_rules(work, cli)
    # An inherited condition's lock must never be mistaken for this new declaration.
    (work / 'reprollm.lock').unlink(missing_ok=True)
    record.link_model(model, work)
    return work


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
    validate_study(study, ROOT)
    frozen = study / 'protocol.freeze.json'
    if split == 'test' and (not frozen.exists() or limit is not None):
        raise ValueError('Formal extension needs its own freeze and all held-out cases.')
    identity = c.read_json(study / 'model.identity.json')
    c.asset_state(model, identity, verify_large=True)
    work = extension_workspace(ROOT, destination, model)
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
