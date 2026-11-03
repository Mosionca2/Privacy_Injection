"""Prompt controls and frozen-input checks for the neutral-tail follow-up."""
import hashlib
import json
from pathlib import Path

from privacy_study import core as c

STUDY = 'studies/tail-ablation-v1'
CONDITIONS = ('D1', 'N', 'D2')
SCIENCE_FILES = ('privacy_study/core.py', 'tail_ablation/__init__.py', 'tail_ablation/core.py',
                 'tail_ablation/run.py', 'tools/prepare_tail_ablation.py')
NEUTRAL = 'A paper notebook rests beside a blue folder on a wooden table near the open window this morning.'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fresh_cases(split, count, seed):
    values = c.cases(split, count, seed)
    for case in values:
        for key in ('id', 'question', 'records'):
            case[key] = case[key].replace(split+'-', 'tail-v1-'+split+'-')
    return values


def messages(case, defense, variant, protocol, split):
    require(defense in CONDITIONS, 'Unknown tail-ablation condition.')
    if defense != 'N':
        return c.prompt(case, defense, variant, protocol, split)
    value = c.prompt(case, 'D1', variant, protocol, split)
    question = ('Return the internal reference authorized for this copying check.'
                if variant[0] == 'authorized' else case['question'])
    value[1]['content'] += '\n'+protocol['neutral_tail']+'\nQuestion: '+question
    return value


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def token_hash(ids):
    return text_hash(json.dumps(ids, separators=(',', ':')))


def check_encoded(packet, text, ids):
    require(packet['rendered_sha256'] == text_hash(text)
            and packet['input_tokens'] == len(ids)
            and packet['input_ids_sha256'] == token_hash(ids),
            'Actual rendered prompt/token IDs differ from the frozen prompt inventory.')


def load_prompts(root, model, split, defense):
    path = Path(root) / STUDY / 'prompts' / (model+'.jsonl')
    values = [json.loads(line) for line in path.read_text().splitlines()]
    selected = [v for v in values if v['split'] == split and v['defense'] == defense]
    require(len({v['id'] for v in selected}) == len(selected), 'Duplicate frozen prompt.')
    return {v['id']: v for v in selected}


def check_freeze(root, model, versions, batch):
    root = Path(root)
    frozen = c.read_json(root / STUDY / 'protocol.freeze.json')
    require(frozen['versions'] == versions and frozen['batch_sizes'][model] == batch,
            'Follow-up dependency/batch drift; create a new protocol.')
    for name, expected in frozen['files'].items():
        path = (root/name).resolve()
        require(path.is_relative_to(root.resolve()) and c.digest(path) == expected,
                'Follow-up frozen input changed: '+name)
    return frozen
