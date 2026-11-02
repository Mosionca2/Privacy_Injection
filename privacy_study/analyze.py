"""Require full paired coverage before producing study statistics."""
import argparse
import json
from pathlib import Path
import statistics
from privacy_study import core as c


def analyze(root, input_dir, output_dir, split):
    root=Path(root); input_dir=Path(input_dir); output_dir=Path(output_dir)
    cases=c.load_cases(root,split); grouped={}; sample_rows={}; summaries=[]; detail=[]; deltas=[]; identities=[]
    for defense in c.DEFENSES:
        file=input_dir/defense/'results.jsonl'; lines=file.read_text().splitlines(); identity=json.loads(lines[0])['identity']
        if identity['backend']!='transformers' or identity['split']!=split or identity['defense']!=defense: raise ValueError('Wrong backend/condition.')
        identities.append(identity)
        rows=c.completed_rows(file,identity); grouped[defense]=c.per_case(rows,cases); sample_rows[defense]=rows
    for key in ('protocol','dataset','code','model','versions','batch_size','cases'):
        if any(ident[key]!=identities[0][key] for ident in identities): raise ValueError(f'Mixed scientific identities: {key}')
    cohort={i for i,row in grouped['D0'].items() if row['clean_acc'] and row['auth_recall']}
    for defense,metrics in grouped.items():
        rows=sample_rows[defense]
        row=dict(defense=defense,n_cases=len(cases),n_generations=len(rows),baseline_capable_n=len(cohort))
        for key in next(iter(metrics.values())):
            if key!='task': row[key]=statistics.mean(r[key] for r in metrics.values())
        row['capable_leak']=statistics.mean(metrics[i]['leak'] for i in cohort) if cohort else None
        row['capable_safe_utility']=statistics.mean(metrics[i]['safe_utility'] for i in cohort) if cohort else None
        row['output_cap_rate']=statistics.mean(int(r['hit_output_cap']) for r in rows.values())
        row['peak_reserved_gib']=max(r['peak_reserved_gib'] for r in rows.values())
        row['zero_any_leak_upper95']=1-.05**(1/len(cases)) if not row['any_leak'] else None
        summaries.append(row)
        for family in c.FAMILIES:
            for position in ('prefix','suffix'):
                selected=[r for r in rows.values() if r['family']==family and r['position']==position]
                detail.append(dict(defense=defense,family=family,position=position,n=len(selected),
                    leak=statistics.mean(int(r['scores']['leak']) for r in selected),
                    safe_utility=statistics.mean(int(r['scores']['safe_utility']) for r in selected)))
    for left,right in [('D0','D1'),('D1','D2'),('D1','D3')]:
        for metric in ('leak','clean_acc','safe_utility'):
            deltas.append(dict(comparison=right+'-'+left,metric=metric,**c.paired_interval(grouped[left],grouped[right],metric)))
    c.csv_file(output_dir/'summary.csv',summaries); c.csv_file(output_dir/'attack-position.csv',detail)
    c.csv_file(output_dir/'paired-differences.csv',deltas)
    c.write_json(output_dir/'analysis.json',dict(schema_version=1,split=split,case_count=len(cases),
        generations=sum(len(rows) for rows in sample_rows.values()),bootstrap_repetitions=2000,
        bootstrap_unit='Base case, stratified by task; all six attacks remain grouped.',baseline_capable_n=len(cohort),summary=summaries))
    return summaries

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True)
    p.add_argument('--split',choices=['dev','test'],required=True); a=p.parse_args()
    analyze('.',a.input,a.output,a.split)
