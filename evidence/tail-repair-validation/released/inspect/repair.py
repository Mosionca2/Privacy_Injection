"""Inspect a torn result tail and create a backed-up repaired copy; never edit the source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


class RepairError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RepairError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate JSON keys require manual review.')
        value[key] = item
    return value


def reject_constant(value):
    raise RepairError('Non-finite JSON numbers require manual review.')


def loads(data):
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=reject_constant)


def canonical_identity(identity):
    return json.dumps(identity,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()


def inspect_bytes(data, identity):
    require(isinstance(identity, dict) and bool(identity), 'Supply a nonempty trusted identity object.')
    boundary = data.rfind(b'\n') + 1
    prefix, tail = data[:boundary], data[boundary:]
    lines = prefix.splitlines()
    require(bool(lines), 'No complete identity header; preserve the file for manual review.')
    documents = []
    for number, line in enumerate(lines, 1):
        try:
            document = loads(line)
        except (ValueError, UnicodeError):
            raise RepairError(f'Complete line {number} is invalid or ambiguous; manual review is required.') from None
        require(isinstance(document, dict), f'Complete line {number} must be a JSON object.')
        documents.append(document)
    require(documents[0].get('type') == 'meta' and isinstance(documents[0].get('identity'),dict)
            and canonical_identity(documents[0]['identity']) == canonical_identity(identity),
            'Checkpoint identity differs from the supplied trusted identity.')
    seen, failures = set(), 0
    for number, row in enumerate(documents[1:], 2):
        kind = row.get('type')
        require(kind in ('sample', 'failure'), f'Unexpected complete record on line {number}; manual review is required.')
        if kind == 'sample':
            identifier = row.get('id')
            require(isinstance(identifier, str) and bool(identifier) and identifier not in seen,
                    'Missing or duplicate successful sample ID; manual review is required.')
            seen.add(identifier)
        else:
            failures += 1
    if tail:
        try:
            text = tail.decode('utf-8')
        except UnicodeError:
            raise RepairError('The tail is not complete UTF-8; manual review is required.') from None
        require(text.strip().startswith('{'), 'The tail is not a recognizable object prefix; manual review is required.')
        try:
            loads(text)
        except json.JSONDecodeError as error:
            # Accept only a narrow, demonstrably incomplete prefix. Other syntax errors
            # may be corruption within a record, so absence of a newline is insufficient.
            require(error.pos == len(text.rstrip()) or error.msg.startswith('Unterminated string'),
                    'Tail damage is not confined to an unfinished JSON prefix; manual review is required.')
        except RepairError:
            raise RepairError('The tail is ambiguous; manual review is required.') from None
        else:
            raise RepairError('The final record is complete JSON without a newline; preserve it for manual review.')
    plan = dict(schema_version=1, repair_needed=bool(tail), source_sha256=digest(data),
        repaired_sha256=digest(prefix), tail_sha256=digest(tail), source_bytes=len(data),
        valid_prefix_bytes=len(prefix), unfinished_tail_bytes=len(tail),
        complete_sample_rows=len(seen), complete_failure_rows=failures,
        identity_sha256=digest(canonical_identity(identity)),
        action='copy_complete_prefix' if tail else 'none',
        scope='Structural tail inspection against caller-supplied identity; no scoring, live-writer exclusion, or model recovery attestation.')
    return plan, prefix, tail


def read_snapshot(source):
    source = Path(source)
    require(source.is_file() and not source.is_symlink(), 'Use a regular source file, not a symlink.')
    with source.open('rb') as stream:
        before = os.fstat(stream.fileno())
        data = stream.read()
        after = os.fstat(stream.fileno())
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    require(all(getattr(before,k) == getattr(after,k) for k in fields) and len(data) == after.st_size,
            'Source changed while reading; inspect a stopped writer checkpoint.')
    return data


def repair(source, identity, *, mode='inspect', expected_sha256=None, output_directory=None):
    require(mode in ('inspect', 'repair'), 'Choose inspect or repair mode.')
    data = read_snapshot(source)
    plan, prefix, tail = inspect_bytes(data, identity)
    if expected_sha256 is not None:
        require(plan['source_sha256'] == expected_sha256, 'Source digest changed since inspection; inspect it again.')
    plan.update(mode=mode, source_name=Path(source).name, tool_run_id=os.environ.get('REPROLLM_RUN_ID'))
    if mode == 'inspect' or not tail:
        return plan
    require(expected_sha256 is not None, 'Repair mode requires the inspected source SHA-256.')
    require(output_directory is not None, 'Repair mode requires a new output directory.')
    target = Path(output_directory)
    require(not target.exists() and not target.is_symlink(), 'Output directory exists; preserve it and choose a new name.')
    # Recheck immediately before creating copies. This does not lock a cooperative or
    # uncooperative writer; the source is deliberately never truncated or replaced.
    require(read_snapshot(source) == data, 'Source changed after inspection; inspect it again.')
    target.mkdir()
    for name, payload in [('damaged.jsonl',data), ('repaired.jsonl',prefix), ('unfinished-tail.bin',tail)]:
        with (target/name).open('xb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    plan.update(source_modified=False, backup_name='damaged.jsonl', repaired_name='repaired.jsonl',
                tail_name='unfinished-tail.bin')
    with (target/'receipt.json').open('x') as stream:
        json.dump(plan, stream, sort_keys=True, indent=2)
        stream.write('\n')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--identity',type=Path,required=True)
    parser.add_argument('--mode',choices=['inspect','repair'],default='inspect')
    parser.add_argument('--sha256')
    parser.add_argument('--output-directory',type=Path)
    args = parser.parse_args()
    try:
        identity = loads(args.identity.read_bytes())
        result = repair(args.input,identity,mode=args.mode,expected_sha256=args.sha256,
                        output_directory=args.output_directory)
    except (ValueError, UnicodeError) as error:
        # JSON decoder details can echo caller content; expose only our fixed diagnostics.
        message = str(error) if isinstance(error,RepairError) else 'Invalid identity JSON; inspect the trusted identity file.'
        print(json.dumps(dict(error=message)),file=sys.stderr)
        return 2
    except OSError as error:
        print(json.dumps(dict(error='File operation failed: '+str(error.strerror))),file=sys.stderr)
        return 3
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
