# Download transport benchmark

## Wall-clock + integrity

| size | transport | reps | verified | mean (s) | min (s) | max (s) |
|---|---|---|---|---|---|---|
| 1,024 | base64 | 10/10 | yes | 1.6230 | 1.5433 | 1.7155 |
| 1,024 | rm_rsync | 10/10 | yes | 1.9906 | 1.8835 | 2.2562 |
| 1,024 | rsync | 10/10 | yes | 1.9007 | 1.8612 | 1.9634 |
| 1,024 | scp | 10/10 | yes | 1.9720 | 1.9034 | 2.1376 |
| 1,048,576 | base64 | 10/10 | yes | 2.2935 | 2.1397 | 2.5031 |
| 1,048,576 | rm_rsync | 10/10 | yes | 2.7007 | 2.4445 | 3.7676 |
| 1,048,576 | rsync | 10/10 | yes | 2.6989 | 2.3482 | 3.2040 |
| 1,048,576 | scp | 10/10 | yes | 2.5858 | 2.4252 | 2.7908 |
| 10,485,760 | base64 | 10/10 | yes | 6.8303 | 6.3420 | 7.4293 |
| 10,485,760 | rm_rsync | 10/10 | yes | 9.2450 | 5.2719 | 10.9286 |
| 10,485,760 | rsync | 10/10 | yes | 5.8269 | 5.4302 | 6.0905 |
| 10,485,760 | scp | 10/10 | yes | 5.6487 | 5.2951 | 6.8201 |
| 104,857,600 | base64 | 10/10 | yes | 52.7400 | 46.9263 | 64.5851 |
| 104,857,600 | rm_rsync | - | SKIP | - | - | - (could not communicate with process) |
| 104,857,600 | rsync | 10/10 | yes | 39.6070 | 35.1135 | 52.3500 |
| 104,857,600 | scp | 10/10 | yes | 53.7698 | 44.4777 | 79.1566 |

## Token / context cost: legacy base64-in-context vs new metadata-only path

| size | legacy b64 bytes | legacy est. tokens | new-path est. tokens | breaches ~10k tool cap? |
|---|---|---|---|---|
| 1,024 | 1,368 | 342 | 40 | no |
| 1,048,576 | 1,398,104 | 349526 | 40 | YES |
| 10,485,760 | 13,981,016 | 3495254 | 40 | YES |
| 104,857,600 | 139,810,136 | 34952534 | 40 | YES |

Ground truth (real `fs_download` call, size=1,024 bytes): actual result length 1,385 bytes (1.806s).

Total bytes moved this sweep: 3,607,142,400

## Notes

- SKIPPED transport=rm_rsync at size=104,857,600: RuntimeError: could not communicate with process
