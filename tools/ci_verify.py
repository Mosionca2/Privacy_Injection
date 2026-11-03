"""Verify published evidence and consume archived runs with pinned ReproLLM source."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacy_study import core as c
from tools.verify_evidence import require, verify

SOURCE_COMMIT = 'f7bd2ad7686ff603f8508d9eedfb919d35edb8e9'
SOURCE_IDENTITY = 'evidence/source-recovery-validation/primary-reference/recorder-source.json'
READER_CASES = (
    ('schema-1', 'evidence/calibration/b1/run/run.json', 1),
    ('schema-2', 'evidence/source-recovery-validation/primary-reference/run/run.json', 2),
)


def check_consumer(source, document, expected_commit=SOURCE_COMMIT):
    """Check both Git identity and package bytes before importing the reader."""
    source = Path(source).resolve()
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=source,
                            check=True, capture_output=True, text=True).stdout.strip()
    require(commit == expected_commit == document['source_commit'],
            'Consumer source commit differs from the fixed source identity.')
    package = source / 'src/reprollm'
    paths = [p for p in package.rglob('*') if '__pycache__' not in p.parts]
    require(package.is_dir() and not any(p.is_symlink() for p in paths),
            'Consumer package is missing or contains symlinks.')
    actual = {p.relative_to(source / 'src').as_posix(): c.digest(p)
              for p in paths if p.is_file()}
    expected = {item['name']: item['sha256'] for item in document['files']}
    require(bool(expected) and actual == expected,
            'Consumer package bytes differ from the recorded source payload.')
    return dict(source_commit=commit, module_version=document['module_version'],
                package_files_checked=len(actual))


def directory_hashes(directory):
    return {p.relative_to(directory).as_posix(): c.digest(p)
            for p in sorted(directory.rglob('*')) if p.is_file()}


def reader_probe(root, source, output, label, name, schema, document):
    run = root / name
    require(c.read_json(run)['schema_version'] == schema, 'Reader fixture schema changed.')
    before = directory_hashes(run.parent)
    env = dict(os.environ, PYTHONPATH=str(source / 'src'), PYTHONDONTWRITEBYTECODE='1',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    # Witness the actual import in the same process that invokes the product CLI.
    script = (
        'from pathlib import Path; import sys; import reprollm; '
        'assert Path(reprollm.__file__).resolve() == Path(sys.argv.pop(1)).resolve(); '
        'assert reprollm.__version__ == sys.argv.pop(1); '
        'from reprollm.cli.main import cli; cli()'
    )
    command = [sys.executable, '-s', '-c', script, str(source / 'src/reprollm/__init__.py'),
               document['module_version'], 'diff', name, name, '--format', 'json']
    result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=120)
    (output / f'{label}-diff.json').write_text(result.stdout)
    (output / f'{label}-stderr.txt').write_text(result.stderr)
    require(before == directory_hashes(run.parent), 'Reader modified an archived run directory.')
    require(result.returncode == 0, f'ReproLLM reader failed for {label}; inspect its saved output.')
    diff = json.loads(result.stdout)
    require(diff['reprollm_version'] == document['module_version']
            and diff['changes'] == [] and diff['summary']['highest'] == 'NONE'
            and diff['summary']['same'] > 0, f'Unexpected self-diff result: {label}')
    return dict(run=name, run_schema_version=schema, reader_version=diff['reprollm_version'],
                exit_code=result.returncode, changes=0, same=diff['summary']['same'],
                archived_directory_unchanged=True, run_sha256=c.digest(run))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--consumer-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'raw/ci')
    args = parser.parse_args()
    source, output = args.consumer_source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    document = c.read_json(ROOT / SOURCE_IDENTITY)
    consumer = check_consumer(source, document)
    fresh = verify(ROOT)
    require(fresh == c.read_json(ROOT / 'reports/delivery/evidence-verification.json'),
            'Published verification receipt is stale; review and regenerate it.')
    c.write_json(output / 'evidence-verification.json', fresh)
    probes = [reader_probe(ROOT, source, output, *case, document) for case in READER_CASES]
    receipt = dict(schema_version=1, all_passed=True, consumer=consumer, reader_probes=probes,
                   evidence_receipt_matches=True, totals=fresh['totals'],
                   snapshot_hashes_checked=fresh['snapshot_hashes_checked'],
                   new_model_generations=0,
                   scope='Offline public-evidence consistency and pinned-source archived-run reading; no inference, model-weight verification, or full upstream product gate.')
    c.write_json(output / 'receipt.json', receipt)
    print(json.dumps(receipt, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
