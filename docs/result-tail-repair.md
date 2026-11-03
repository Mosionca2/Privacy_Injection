# Preserve a checkpoint with an unfinished JSONL tail

`tools/repair_result_tail.py` inspects this study's result format: one identity header followed by sample/failure objects. It reads the source and creates a separate recovery bundle. It never truncates, rewrites or replaces the source file. Stop the writer and retain a trusted earlier identity before deciding which output to resume.

Inspect first:

```sh
python tools/repair_result_tail.py --input raw/results.jsonl --identity raw/expected-identity.json --mode inspect
```

`expected-identity.json` contains the identity object from a trusted earlier checkpoint or independently checked scientific inputs. Copying an unchecked damaged header into this file does not independently establish model, data or code identity. The frozen inference runner still checks scientific identity before resuming.

If the report identifies a narrow unfinished object prefix, review its `source_sha256` and use that exact digest:

```sh
python tools/repair_result_tail.py --input raw/results.jsonl --identity raw/expected-identity.json --mode repair --sha256 REPLACE_WITH_INSPECTED_SHA256 --output-directory raw/repair-001
```

Choose a new bundle directory under an existing parent. The bundle contains:

| File | Preserved content |
|---|---|
| `damaged.jsonl` | Exact original bytes, including the unfinished tail |
| `repaired.jsonl` | Exact complete prefix, including valid failure records |
| `unfinished-tail.bin` | Exact bytes excluded from the repaired copy |
| `receipt.json` | Source/output/tail hashes, byte counts, sample/failure counts and actual tool run ID when recorded |

The inspected digest is required for repair, and source bytes are checked again before copying. An existing output directory is refused. Inspection and clean-checkpoint no-ops create no bundle. Source reads do not exclude a live writer, and file synchronization here is not a power-loss durability guarantee. Installing a repaired copy into a stopped experiment is a separate deliberate operation; this utility does not launch inference or edit ReproLLM's own run records.

The utility refuses mismatched identities, invalid complete lines, duplicate successful IDs, ambiguous JSON keys, non-finite JSON numbers, unrecognized tail data and syntax errors outside the narrow accepted unfinished-prefix cases. A complete sample or failure object missing only its final newline is also refused: a valid record must not be silently discarded. Incomplete UTF-8, truncated literals and some escape/number fragments require manual review. Every excluded tail remains available in both the backup and tail file.

The tool checks structure and caller-supplied identity; it does not score responses, reconstruct missing data, attest model consumption or verify a real crash. See [the controlled validation](../reports/tail-repair-validation/REPORT.md) for actual ReproLLM recordings and their limits. Repairing or recording an old result copy creates no new model responses.
