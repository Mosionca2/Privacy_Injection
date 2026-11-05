"""Actual local judge inference, with independent identities and strict resume checks."""
import argparse,json,os,time
from pathlib import Path
from privacy_study import core as c
from judge_injection import core as j

def main():
 p=argparse.ArgumentParser();p.add_argument('--judge-model',required=True);p.add_argument('--inputs',required=True)
 p.add_argument('--judge-guard',choices=['J0','J1'],required=True);p.add_argument('--judge-max-tokens',type=int,default=16)
 p.add_argument('--judge-temperature',type=float,default=0);p.add_argument('--judge-repetitions',type=int,default=1)
 p.add_argument('--batch-size',type=int,required=True);p.add_argument('--output',default='raw/judge-predictions.jsonl')
 a=p.parse_args()
 if a.judge_temperature!=0 or a.judge_repetitions<1:raise ValueError('This protocol requires greedy generation and positive repetitions.')
 source=[json.loads(x) for x in Path(a.inputs).read_text().splitlines()]
 identity=dict(schema_version=1,input_sha256=c.digest(a.inputs),model=c.read_json('model.identity.json'),
  guard=a.judge_guard,max_tokens=a.judge_max_tokens,repetitions=a.judge_repetitions,batch_size=a.batch_size,
  code={str(f):c.digest(f) for f in sorted(Path('judge_injection').glob('*.py'))})
 out=Path(a.output);out.parent.mkdir(exist_ok=True)
 done={}
 if out.exists():
  lines=[json.loads(x) for x in out.read_text().splitlines()]
  if lines[0]['identity']!=identity:raise ValueError('Resume identity mismatch.')
  for r in lines[1:]:
   if r['type']=='sample':
    if r['id'] in done:raise ValueError('Duplicate judge response.')
    done[r['id']]=r
 else:out.write_text(json.dumps(dict(type='meta',identity=identity))+'\n')
 jobs=[(row,rep,row['id']+':'+str(rep)) for row in source for rep in range(a.judge_repetitions)]
 jobs=[x for x in jobs if x[2] not in done]
 if not jobs:raise ValueError('Already complete; do not record empty inference.')
 import torch
 from transformers import AutoTokenizer,AutoModelForCausalLM,set_seed
 from transformers.utils.logging import disable_progress_bar
 disable_progress_bar();set_seed(90217)
 if not torch.cuda.is_available():raise RuntimeError('CUDA required.')
 tok=AutoTokenizer.from_pretrained(a.judge_model,local_files_only=True,padding_side='left',trust_remote_code=False)
 if tok.pad_token_id is None:tok.pad_token=tok.eos_token
 model=AutoModelForCausalLM.from_pretrained(a.judge_model,local_files_only=True,trust_remote_code=False,
          dtype=torch.float16,attn_implementation='sdpa').to('cuda').eval()
 torch.cuda.reset_peak_memory_stats();start=time.perf_counter();new=0
 with out.open('a') as stream:
  for offset in range(0,len(jobs),a.batch_size):
   batch=jobs[offset:offset+a.batch_size]
   texts=[tok.apply_chat_template(j.messages(row['target'],row['candidate'],a.judge_guard),tokenize=False,
             add_generation_prompt=True,enable_thinking=False) for row,rep,sid in batch]
   tensors=tok(texts,padding=True,return_tensors='pt',add_special_tokens=False)
   counts=tensors['attention_mask'].sum(dim=1).tolist()
   if max(counts)>1024:raise ValueError('Input exceeds protocol; truncation prohibited.')
   width=tensors['input_ids'].shape[1];tensors=tensors.to('cuda')
   with torch.inference_mode():generated=model.generate(**tensors,max_new_tokens=a.judge_max_tokens,do_sample=False,
                    num_beams=1,pad_token_id=tok.pad_token_id)[:,width:]
   torch.cuda.synchronize()
   for (row,rep,sid),tokens,n_input in zip(batch,generated,counts):
    ids=tokens.tolist();ended=tok.eos_token_id in ids
    if ended:ids=ids[:ids.index(tok.eos_token_id)+1]
    text=tok.decode(ids,skip_special_tokens=True)
    value=dict(type='sample',id=sid,case_id=row['case_id'],gold=row['gold'],view=row['view'],family=row['family'],
       position=row['position'],task=row['task'],repeat_index=rep,output=text,scores=j.score(row['target'],text,row['gold']),
       input_tokens=n_input,output_tokens=len(ids),hit_output_cap=not ended and len(ids)>=a.judge_max_tokens,
       reprollm_run_id=os.environ.get('REPROLLM_RUN_ID'))
    stream.write(json.dumps(value,sort_keys=True)+'\n');stream.flush();new+=1
   print(json.dumps(dict(event='progress',new_outputs=new,total=len(jobs))),flush=True)
 c.write_json('raw/completion.json',dict(schema_version=1,expected=len(source)*a.judge_repetitions,new_judge_outputs=new,
       seconds=time.perf_counter()-start,peak_reserved_gib=torch.cuda.max_memory_reserved()/2**30,
       reprollm_run_id=os.environ.get('REPROLLM_RUN_ID')))
if __name__=='__main__':main()
