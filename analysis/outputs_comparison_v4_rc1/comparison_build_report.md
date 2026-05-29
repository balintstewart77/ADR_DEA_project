# v4 rc1 Comparison Build Report

## Run Completion

| Run | Status | Projects | Retry lines | Error lines |
| --- | --- | --- | --- | --- |
| Opus 4.8 | completed with traceback in log | 1272 | 6 | 3 |
| Opus 4.6 | complete | 1272 | 0 | 0 |

## Cache Hit Rates

| Run | Cache read tokens | Cache creation tokens | Approx hit rate |
| --- | --- | --- | --- |
| Opus 4.8 | 1472256 | 27553 | 98.2% |
| Opus 4.6 | 844812 | 25701 | 97.0% |

Project counts and ID sets match: yes

## Failed or Retried Batches

### Opus 4.8

- Retry: `[retry] Attempt 1/3 failed (missing IDs: ['2024/136']); retrying in 2s...`
- Retry: `[retry] Attempt 2/3 failed (unexpected IDs: ['2024/076b_placeholder']; missing IDs: ['2024/136']); retrying in 4s...`
- Retry: `[retry] Attempt 1/3 failed (unexpected IDs: ['2024/076b']; missing IDs: ['2024/136', '2024/014/a']); retrying in 2s...`
- Retry: `[retry] Attempt 2/3 failed (unexpected IDs: ['2024/005']; missing IDs: ['2024/136']); retrying in 4s...`
- Retry: `[retry] Attempt 1/3 failed (unexpected IDs: ['2024/005']; missing IDs: ['2024/136']); retrying in 2s...`
- Retry: `[retry] Attempt 2/3 failed (unexpected IDs: ['2024/076b']; missing IDs: ['2024/136']); retrying in 4s...`
- Error: `[error] Batch 76 failed after 3 attempts: unexpected IDs: ['2024/076b']; missing IDs: ['2024/136', '2024/014/a', '2024/142', '2024/131', '2024/121', '2024/081']`
- Error: `[error] Batch 1 failed after 3 attempts: unexpected IDs: ['2024/076b']; missing IDs: ['2024/136', '2024/014/a', '2024/142', '2024/131', '2024/121', '2024/081']`
- Error: `[error] Batch 1 failed after 3 attempts: unexpected IDs: ['2024/076b', '2024/076c']; missing IDs: ['2024/136', '2024/014/a', '2024/142']`

## Targeted Cache Fill

### Opus 4.8

- `[targeted-cache-fill] 10 missing record(s): 2024/116, 2024/096, 2024/076, 2024/106, 2024/136, 2024/014/a, 2024/142, 2024/131, 2024/121, 2024/081`
- `[targeted-cache-fill] cached 2024/116 on attempt 1`
- `[targeted-cache-fill] cached 2024/096 on attempt 1`
- `[targeted-cache-fill] cached 2024/076 on attempt 1`
- `[targeted-cache-fill] cached 2024/106 on attempt 1`
- `[targeted-cache-fill] cached 2024/136 on attempt 1`
- `[targeted-cache-fill] cached 2024/014/a on attempt 1`
- `[targeted-cache-fill] cached 2024/142 on attempt 1`
- `[targeted-cache-fill] cached 2024/131 on attempt 1`
- `[targeted-cache-fill] cached 2024/121 on attempt 1`
- `[targeted-cache-fill] cached 2024/081 on attempt 1`

## Anomalies

- Opus 4.8: traceback text appears in run.log.

