import argparse, json, os, time
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--case', required=True)
a = p.parse_args()
raw = Path('raw'); raw.mkdir(exist_ok=True)
value = dict(run_id=os.environ['REPROLLM_RUN_ID'], case=a.case,
             work_units=1, checksum=sum(range(1000)))
(raw/'artifact.json').write_text(json.dumps(value)+'\n')
marker = dict(value, pid=os.getpid(), parent=os.getppid(),
              nonce=os.environ['BOUNDARY_NONCE'])
(raw/'ready.tmp').write_text(json.dumps(marker))
(raw/'ready.tmp').replace(raw/'ready.json')
print(json.dumps(value), flush=True)
if a.case != 'success':
    time.sleep(180)
(raw/'completion.json').write_text(json.dumps(value)+'\n')
