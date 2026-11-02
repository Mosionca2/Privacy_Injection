"""Freeze scientific files, software versions and the selected inference batch."""
import argparse
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from privacy_study import core as c
from privacy_study.run import science_files, versions

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--batch-size',required=True,type=int)
args=parser.parse_args()
if args.batch_size<1: parser.error('Batch size must be positive.')
if Path('protocol.freeze.json').exists(): raise SystemExit('Protocol is already frozen; create an explicitly new study version.')
c.write_json('protocol.freeze.json',dict(schema_version=1,protocol_id=c.read_json('configs/protocol.json')['protocol_id'],
    batch_size=args.batch_size,versions=versions(),files=science_files('.'),
    scientific_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
print('Frozen scientific files, actual package versions, and batch size.')
