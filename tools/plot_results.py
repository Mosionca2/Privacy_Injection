"""Plot actual completed analysis tables; never synthesize experimental results."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reports',default='reports/formal')
p.add_argument('--model-label',default='Local Qwen3-8B');a=p.parse_args()
root=Path(a.reports)
with (root/'summary.csv').open() as f: rows=list(csv.DictReader(f))
if len(rows)!=4 or any(int(r['n_cases'])!=96 for r in rows):raise SystemExit('Expected four complete 96-case formal conditions.')
labels=[r['defense'] for r in rows]; colors=['#4667a6','#d58b32','#289481','#995ca4']
fig,ax=plt.subplots(figsize=(7,5))
for row,color in zip(rows,colors):
    x=100*float(row['leak']);y=100*float(row['safe_utility'])
    ax.scatter(x,y,s=90,color=color);ax.annotate(row['defense'],(x,y),xytext=(7,5),textcoords='offset points')
ax.set(xlabel='Attack-query leakage (%) — lower is better',ylabel='Safe task success under attack (%)',title=f'{a.model_label}: 96 paired cases')
ax.grid(alpha=.2);ax.margins(x=.15,y=.15);fig.tight_layout()
for ext in ('png','svg'):fig.savefig(root/f'privacy-utility.{ext}',dpi=180)
plt.close(fig)
fig,ax=plt.subplots(figsize=(7,5));x=list(range(4))
ax.bar([i-.18 for i in x],[100*float(r['clean_acc']) for r in rows],width=.36,label='Clean task success')
ax.bar([i+.18 for i in x],[100*float(r['auth_recall']) for r in rows],width=.36,label='Authorized-copy recall')
ax.set(xticks=x,xticklabels=labels,ylim=(0,105),ylabel='Percent',title='Ability controls, kept separate from attacks')
ax.legend(loc='lower right');fig.tight_layout()
for ext in ('png','svg'):fig.savefig(root/f'ability-controls.{ext}',dpi=180)
plt.close(fig)
fig,ax=plt.subplots(figsize=(7,5))
for key,label in [('prefix_leak','Injection at document start'),('suffix_leak','Injection at document end')]:
    ax.plot(labels,[100*float(r[key]) for r in rows],marker='o',label=label)
ax.set(ylabel='Attack-query leakage (%)',ylim=(0,100),title='Position effects within the fixed attack set');ax.legend();ax.grid(alpha=.2);fig.tight_layout()
for ext in ('png','svg'):fig.savefig(root/f'attack-position.{ext}',dpi=180)
plt.close(fig)
for svg in root.glob('*.svg'):
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
print('Generated three figures as PNG and SVG from actual formal CSVs.')
