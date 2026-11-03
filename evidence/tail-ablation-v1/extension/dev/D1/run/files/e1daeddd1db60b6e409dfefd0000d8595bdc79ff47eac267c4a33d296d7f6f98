"""Prepare a fresh, length-controlled follow-up without modifying the original freezes."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacy_study import core as c
from privacy_study.run import versions
from tail_ablation import core as a
from tools.ci_verify import SOURCE_COMMIT


def prepare(models):
    import os
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    from transformers import AutoTokenizer
    study = ROOT / a.STUDY
    a.require(not study.exists(), 'Use a new study version; preserve existing prepared inputs.')
    protocol = c.read_json(ROOT/'configs/protocol.json')
    protocol.pop('model_label',None)
    protocol.update(protocol_id='neutral-tail-v1', data_seed=20261103, namespace='tail-v1',
        defenses=list(a.CONDITIONS), neutral_tail=a.NEUTRAL,
        upstream_source_commit=SOURCE_COMMIT, source_module_version='0.7.0',
        models={'primary':dict(identity='model.identity.json', batch_size=64),
                'extension':dict(identity='studies/qwen3-1.7b/model.identity.json', batch_size=16)},
        matching=dict(max_absolute_token_difference=1, scope='N and D2 include the same repeated question; only their preceding sentence differs.'),
        interpretation='Exploratory follow-up after original results; fresh synthetic identifiers and names. D2-N compares reminder wording to one neutral sentence at matched length/repetition; N-D1 combines added length and question repetition.',
        contrasts=[['D1','N'],['D1','D2'],['N','D2']],
        acceptance='Freeze before any follow-up GPU work. Complete development with no OOM/truncation/output caps before test. Do not tune conditions based on leakage outcomes.')
    datasets = {s:a.fresh_cases(s,n,protocol['data_seed']) for s,n in protocol['samples'].items()}
    all_codes = [v[k] for rows in datasets.values() for v in rows for k in ('public','private')]
    original = [v[k] for s in ('dev','test') for v in c.load_cases(ROOT,s) for k in ('public','private')]
    a.require(len(set(all_codes)) == len(all_codes) and not set(all_codes) & set(original),
              'Follow-up identifiers overlap each other or the original data.')
    inventories, diagnostics = {}, {}
    for model, path in models.items():
        c.asset_state(path, c.read_json(ROOT/protocol['models'][model]['identity']), verify_large=True)
        tokenizer = AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False,padding_side='left')
        rows, differences = [], []
        for split, cases in datasets.items():
            for case in cases:
                for variant in c.VARIANTS:
                    lengths = {}
                    for defense in a.CONDITIONS:
                        msg = a.messages(case,defense,variant,protocol,split)
                        text = tokenizer.apply_chat_template(msg,tokenize=False,add_generation_prompt=True,enable_thinking=False)
                        ids = tokenizer.encode(text,add_special_tokens=False)
                        a.require(len(ids) <= protocol['max_input_tokens'], 'Prepared input exceeds the fixed token cap.')
                        lengths[defense] = len(ids)
                        rows.append(dict(id=':'.join((case['id'],*variant)),split=split,defense=defense,
                            messages=msg,input_tokens=len(ids),rendered_sha256=a.text_hash(text),input_ids_sha256=a.token_hash(ids)))
                    differences.append(lengths['N']-lengths['D2'])
        a.require(max(map(abs,differences)) <= 1, 'Neutral/reminder prompt lengths exceed the declared tolerance.')
        inventories[model] = rows
        diagnostics[model] = dict(prompt_count=len(rows),matched_pairs=len(differences),
            minimum_token_difference=min(differences),maximum_token_difference=max(differences),
            maximum_input_tokens=max(v['input_tokens'] for v in rows))
    study.mkdir(parents=True)
    c.write_json(study/'protocol.json',protocol)
    for split, rows in datasets.items():
        target=study/'data'/(split+'.jsonl');target.parent.mkdir(exist_ok=True)
        target.write_text(''.join(json.dumps(v,sort_keys=True)+'\n' for v in rows))
    for model, rows in inventories.items():
        target=study/'prompts'/(model+'.jsonl');target.parent.mkdir(exist_ok=True)
        target.write_text(''.join(json.dumps(v,sort_keys=True)+'\n' for v in rows))
    c.write_json(study/'preparation.json',dict(schema_version=1,diagnostics=diagnostics,
        fresh_case_count=sum(map(len,datasets.values())),original_identifier_overlap=0,new_model_generations=0))
    names=[p.relative_to(ROOT).as_posix() for p in sorted(study.rglob('*')) if p.is_file()]
    names+=['privacy_study/core.py','configs/protocol.json','requirements.runtime.txt']
    names += list(a.SCIENCE_FILES)
    names += [v['identity'] for v in protocol['models'].values()]
    c.write_json(study/'protocol.freeze.json',dict(schema_version=1,files={n:c.digest(ROOT/n) for n in sorted(set(names))},
        versions=versions(),batch_sizes={m:v['batch_size'] for m,v in protocol['models'].items()},
        stage='Frozen before any follow-up GPU generation; original freezes unchanged.'))
    print(diagnostics)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--primary-model',type=Path,required=True)
    parser.add_argument('--extension-model',type=Path,required=True)
    args=parser.parse_args()
    prepare(dict(primary=args.primary_model,extension=args.extension_model))
