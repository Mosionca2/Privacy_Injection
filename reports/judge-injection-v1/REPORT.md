# Judge-injection V1: diagnostic evidence only

All 12,928 judge outputs in 14 GPU captures are retained, including 9,984 intended formal outputs. The length-control construction failed independent verification: `len(BatchEncoding)` measured mapping keys, not input tokens. Attack and neutral views therefore differed in encoded length. These results are excluded from confirmatory attack-versus-length-control claims.

The correction keeps the prompts and attack templates fixed and uses fresh base cases in [V2](../../studies/judge-injection-v2/protocol.json). Original frozen source, inputs, output artifacts and run records remain unchanged. This was a study integration error, not a demonstrated ReproLLM defect.
