"""Real inference on separately frozen tail-ablation prompts and fresh paired cases."""
from __future__ import annotations
import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import time
from privacy_study import core as c
from tail_ablation import core as a


def versions():
    return {name:metadata.version(name) for name in ('torch','transformers','accelerate','safetensors','tokenizers','reprollm')}


def run(args):
    root=Path.cwd(); study=root/a.STUDY; protocol=c.read_json(study/'protocol.json')
    values=c.load_cases(study,args.split)
    model_identity=c.read_json(root/protocol['models'][args.study_model]['identity'])
    a.check_freeze(root,args.study_model,versions(),args.batch_size)
    packets=a.load_prompts(root,args.study_model,args.split,args.defense)
    identity=dict(schema_version=1, backend='transformers', defense=args.defense, split=args.split,
                  cases=[case['id'] for case in values], batch_size=args.batch_size,
                  protocol=c.digest(study/'protocol.json'), dataset=c.digest(study/f'data/{args.split}.jsonl'),
                  code={p.as_posix():c.digest(p) for p in map(Path,a.SCIENCE_FILES)},
                  study_id='tail-ablation-v1',study_model=args.study_model,
                  prompt_index=c.digest(study/'prompts'/(args.study_model+'.jsonl')),
                  model=model_identity, versions=versions(), dtype='float16', thinking=False)
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    done=c.completed_rows(output,identity)
    jobs=[(case,variant,f"{case['id']}:{variant[0]}:{variant[1]}:{variant[2]}") for case in values for variant in c.VARIANTS]
    pending=[job for job in jobs if job[2] not in done]
    if not pending:
        print(json.dumps({'event':'already_complete','new_generations':0}),flush=True); return
    if not output.exists():
        output.write_text(json.dumps({'type':'meta','identity':identity})+'\n')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false')
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, set_seed
    from transformers.utils.logging import disable_progress_bar
    disable_progress_bar()
    if not torch.cuda.is_available(): raise RuntimeError('Real CUDA inference is required.')
    set_seed(protocol['run_seed'])
    model_state=c.asset_state(args.model,model_identity)
    start=time.perf_counter()
    tokenizer=AutoTokenizer.from_pretrained(args.model,local_files_only=True,trust_remote_code=False,padding_side='left')
    if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
    model=AutoModelForCausalLM.from_pretrained(args.model,local_files_only=True,trust_remote_code=False,
          use_safetensors=True,dtype=torch.float16,attn_implementation='sdpa').to('cuda').eval()
    torch.cuda.synchronize(); load_seconds=time.perf_counter()-start
    torch.cuda.reset_peak_memory_stats(); inference_start=time.perf_counter(); new_count=0
    print(json.dumps({'event':'model_loaded','load_seconds':load_seconds,'batch_size':args.batch_size}),flush=True)
    with output.open('a') as stream:
        for offset in range(0,len(pending),args.batch_size):
            batch_jobs=pending[offset:offset+args.batch_size]
            texts=[tokenizer.apply_chat_template(packets[sid]['messages'],
                   tokenize=False,add_generation_prompt=True,enable_thinking=False) for case,variant,sid in batch_jobs]
            tensors=tokenizer(texts,padding=True,return_tensors='pt',add_special_tokens=False)
            lengths=tensors['attention_mask'].sum(dim=1).tolist(); width=tensors['input_ids'].shape[1]
            if max(lengths)>protocol['max_input_tokens']: raise ValueError('Input exceeds the protocol; truncation is forbidden.')
            for row_index,((case,variant,sid),text) in enumerate(zip(batch_jobs,texts)):
                ids=tensors['input_ids'][row_index][tensors['attention_mask'][row_index].bool()].tolist()
                a.check_encoded(packets[sid],text,ids)
            tensors=tensors.to('cuda'); torch.cuda.synchronize(); tick=time.perf_counter()
            try:
                with torch.inference_mode():
                    generated=model.generate(**tensors,max_new_tokens=protocol['max_new_tokens'],do_sample=False,
                           num_beams=1,pad_token_id=tokenizer.pad_token_id)[:,width:]
                torch.cuda.synchronize(); elapsed=time.perf_counter()-tick
                for (case,variant,sid),tokens,n_input in zip(batch_jobs,generated,lengths):
                    token_ids=tokens.tolist()
                    ended=tokenizer.eos_token_id in token_ids
                    if ended: token_ids=token_ids[:token_ids.index(tokenizer.eos_token_id)+1]
                    text=tokenizer.decode(token_ids,skip_special_tokens=True)
                    row=dict(type='sample',id=sid,case_id=case['id'],task=case['task'],variant=variant[0],
                             family=variant[1],position=variant[2],output=text,scores=c.score(case,variant[0],text),
                             prompt_sha256=packets[sid]['rendered_sha256'],input_ids_sha256=packets[sid]['input_ids_sha256'],
                             input_tokens=n_input,output_tokens=len(token_ids),hit_output_cap=not ended and len(token_ids)>=protocol['max_new_tokens'],
                             batch_seconds=elapsed,amortized_seconds=elapsed/len(batch_jobs),
                             peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
                             peak_reserved_gib=torch.cuda.max_memory_reserved()/2**30,
                             reprollm_run_id=os.environ.get('REPROLLM_RUN_ID'))
                    stream.write(json.dumps(row,sort_keys=True)+'\n'); stream.flush(); new_count+=1
                print(json.dumps({'event':'batch_complete','new_samples':new_count,'total_pending':len(pending)}),flush=True)
            except Exception as error:
                stream.write(json.dumps({'type':'failure','sample_ids':[j[2] for j in batch_jobs],'error_type':type(error).__name__})+'\n')
                stream.flush(); raise
    if model_state!=c.asset_state(args.model,model_identity): raise ValueError('Model assets changed during inference.')
    summary=dict(schema_version=1,defense=args.defense,split=args.split,batch_size=args.batch_size,
                 expected=len(jobs),new_generations=new_count,load_seconds=load_seconds,
                 inference_seconds=time.perf_counter()-inference_start,
                 peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
                 peak_reserved_gib=torch.cuda.max_memory_reserved()/2**30,
                 reprollm_run_id=os.environ.get('REPROLLM_RUN_ID'))
    c.write_json(output.parent/'completion.json',summary)
    print(json.dumps({'event':'completed',**summary}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',default='assets/model'); p.add_argument('--defense',choices=a.CONDITIONS,required=True)
    p.add_argument('--split',choices=['dev','test'],required=True); p.add_argument('--batch-size',type=int,default=1)
    p.add_argument('--study-model',choices=['primary','extension'],required=True); p.add_argument('--output',default='raw/results.jsonl')
    args=p.parse_args()
    if args.batch_size<1: p.error('Batch size must be positive.')
    run(args)

if __name__=='__main__': main()
