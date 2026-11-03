"""Paired descriptive follow-up comparisons with complete case clusters."""
import statistics
from pathlib import Path

from privacy_study import core as c
from tail_ablation import core as a
from tail_ablation.evidence import check_capture


def analyze(root, split):
    protocol=c.read_json(root/a.STUDY/'protocol.json');cases=c.load_cases(root/a.STUDY,split)
    output=dict(schema_version=1,split=split,new_responses=0,models={})
    for model in protocol['models']:
        per_case={};summaries={}
        for defense in a.CONDITIONS:
            summary,_,rows=check_capture(root,root/'evidence/tail-ablation-v1'/model/split/defense)
            per_case[defense]=c.per_case(rows,cases)
            summaries[defense]=dict(run_id=summary['run_id'],responses=len(rows),
                metrics={key:statistics.mean(v[key] for v in per_case[defense].values())
                         for key in ('leak','safe_utility','clean_acc','auth_recall','any_leak')},
                output_caps=sum(v['hit_output_cap'] for v in rows.values()),
                peak_reserved_gib=max(v['peak_reserved_gib'] for v in rows.values()))
            output['new_responses']+=len(rows)
        contrasts={right+'-'+left:{metric:c.paired_interval(per_case[left],per_case[right],metric)
            for metric in ('leak','safe_utility','clean_acc')} for left,right in protocol['contrasts']}
        output['models'][model]=dict(conditions=summaries,contrasts=contrasts)
    return output


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split',choices=['dev','test'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    c.write_json(args.output,analyze(Path.cwd(),args.split))
