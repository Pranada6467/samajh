# ACQ scores

Unit: customer. Per 100 with Wilson 95% intervals; exact McNemar on paired customers.
No pooling across cells; each arm is given as its own count. A flag counts toward refer_ground and
gap_found only when its quote is from an own or again reply (and, on a false field, its reason is not
a `_dont_know`); the `_any_source` lines count every flag. Calls with a degraded turn are kept.

Primary tests (pre-declared): P1 at a=0, r in {0.5, 0.75, 1}; P2a at a=0, every r.

## Cell r=0,a=0

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground_any_source | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_customer_statement | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete_on_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early.declined | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.25,a=0

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground_any_source | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_customer_statement | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete_on_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early.declined | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.5,a=0

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground_any_source | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_customer_statement | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete_on_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early.declined | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.75,a=0

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground_any_source | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_customer_statement | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete_on_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early.declined | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=1,a=0

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_ground_any_source | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_customer_statement | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete_on_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early.declined | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught_ground | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_ground_any_source | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_customer_statement | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete_on_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early.declined | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.strict_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_caught_ground | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_confirmed | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.gap_flag_any_tier | 46/48 = 95.8 per 100 [86.0, 98.8] |
| open.gap_found_any_source | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.understanding_gap | 45/48 = 93.8 per 100 [83.2, 97.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 2/48 = 4.2 per 100 [1.2, 14.0] |
| open.ended_early.declined | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.understanding_gap | 2/32 = 6.2 per 100 [1.7, 20.1] |
| open.clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| open.ended_early | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.ended_early.declined | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0,a=0.25

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground_any_source | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_customer_statement | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.ended_early.declined | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.miss | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| closed.lenient_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground_any_source | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_customer_statement | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.incomplete_on_ground | 20/40 = 50.0 per 100 [35.2, 64.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.ended_early.declined | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.miss | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_confirmed | 7/40 = 17.5 per 100 [8.7, 31.9] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground_any_source | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_customer_statement | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 8/80 = 10.0 per 100 [5.2, 18.5] |
| open.incomplete_on_ground | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.ended_early.declined | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.miss | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 75/80 = 93.8 per 100 [86.2, 97.3] |
| closed.strict_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.strict_confirmed | 5/80 = 6.2 per 100 [2.7, 13.8] |
| closed.lenient_caught | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_confirmed | 12/80 = 15.0 per 100 [8.8, 24.4] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.25,a=0.25

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground_any_source | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_customer_statement | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.ended_early.declined | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.miss | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| closed.lenient_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground_any_source | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_customer_statement | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.incomplete_on_ground | 20/40 = 50.0 per 100 [35.2, 64.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.ended_early.declined | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.miss | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 39/40 = 97.5 per 100 [87.1, 99.6] |
| closed.strict_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.strict_confirmed | 1/40 = 2.5 per 100 [0.4, 12.9] |
| closed.lenient_caught | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_confirmed | 7/40 = 17.5 per 100 [8.7, 31.9] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground_any_source | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_customer_statement | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 8/80 = 10.0 per 100 [5.2, 18.5] |
| open.incomplete_on_ground | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.ended_early.declined | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.miss | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 74/80 = 92.5 per 100 [84.6, 96.5] |
| closed.strict_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.strict_confirmed | 6/80 = 7.5 per 100 [3.5, 15.4] |
| closed.lenient_caught | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_confirmed | 12/80 = 15.0 per 100 [8.8, 24.4] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.5,a=0.25

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground_any_source | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_customer_statement | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.ended_early.declined | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.miss | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| closed.lenient_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground_any_source | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_customer_statement | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.incomplete_on_ground | 20/40 = 50.0 per 100 [35.2, 64.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.ended_early.declined | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.miss | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 38/40 = 95.0 per 100 [83.5, 98.6] |
| closed.strict_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.strict_confirmed | 2/40 = 5.0 per 100 [1.4, 16.5] |
| closed.lenient_caught | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_confirmed | 7/40 = 17.5 per 100 [8.7, 31.9] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground_any_source | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_customer_statement | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 8/80 = 10.0 per 100 [5.2, 18.5] |
| open.incomplete_on_ground | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.ended_early.declined | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.miss | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 73/80 = 91.2 per 100 [83.0, 95.7] |
| closed.strict_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.strict_confirmed | 7/80 = 8.8 per 100 [4.3, 17.0] |
| closed.lenient_caught | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_confirmed | 12/80 = 15.0 per 100 [8.8, 24.4] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.75,a=0.25

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground_any_source | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_customer_statement | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.ended_early.declined | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.miss | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| closed.lenient_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground_any_source | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_customer_statement | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.incomplete_on_ground | 20/40 = 50.0 per 100 [35.2, 64.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.ended_early.declined | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.miss | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 37/40 = 92.5 per 100 [80.1, 97.4] |
| closed.strict_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.strict_confirmed | 3/40 = 7.5 per 100 [2.6, 19.9] |
| closed.lenient_caught | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_confirmed | 7/40 = 17.5 per 100 [8.7, 31.9] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground_any_source | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_customer_statement | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 8/80 = 10.0 per 100 [5.2, 18.5] |
| open.incomplete_on_ground | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.ended_early.declined | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.miss | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 72/80 = 90.0 per 100 [81.5, 94.8] |
| closed.strict_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.strict_confirmed | 8/80 = 10.0 per 100 [5.2, 18.5] |
| closed.lenient_caught | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_confirmed | 12/80 = 15.0 per 100 [8.8, 24.4] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=1,a=0.25

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_ground_any_source | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_customer_statement | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.ended_early.declined | 8/40 = 20.0 per 100 [10.5, 34.8] |
| open.miss | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| closed.lenient_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_caught_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.lenient_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_ground_any_source | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_customer_statement | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.incomplete_on_ground | 20/40 = 50.0 per 100 [35.2, 64.8] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.ended_early.declined | 5/40 = 12.5 per 100 [5.5, 26.1] |
| open.miss | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.strict_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.strict_confirmed | 7/40 = 17.5 per 100 [8.7, 31.9] |
| closed.lenient_caught | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_caught_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| closed.lenient_confirmed | 7/40 = 17.5 per 100 [8.7, 31.9] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_ground_any_source | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_customer_statement | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 8/80 = 10.0 per 100 [5.2, 18.5] |
| open.incomplete_on_ground | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.ended_early.declined | 13/80 = 16.2 per 100 [9.7, 25.8] |
| open.miss | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.strict_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.strict_confirmed | 12/80 = 15.0 per 100 [8.8, 24.4] |
| closed.lenient_caught | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_caught_ground | 68/80 = 85.0 per 100 [75.6, 91.2] |
| closed.lenient_confirmed | 12/80 = 15.0 per 100 [8.8, 24.4] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.gap_flag_any_tier | 32/48 = 66.7 per 100 [52.5, 78.3] |
| open.gap_found_any_source | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 9/48 = 18.8 per 100 [10.2, 31.9] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 10/48 = 20.8 per 100 [11.7, 34.3] |
| open.ended_early.declined | 8/48 = 16.7 per 100 [8.7, 29.6] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 20/32 = 62.5 per 100 [45.3, 77.1] |
| open.understanding_gap | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.clear | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early | 4/32 = 12.5 per 100 [5.0, 28.1] |
| open.ended_early.declined | 3/32 = 9.4 per 100 [3.2, 24.2] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 28/32 = 87.5 per 100 [71.9, 95.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0,a=0.5

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 23/40 = 57.5 per 100 [42.2, 71.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.ended_early.declined | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| closed.lenient_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 6/40 = 15.0 per 100 [7.1, 29.1] |
| open.incomplete_on_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.ended_early.declined | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_confirmed | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground_any_source | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_customer_statement | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 9/80 = 11.2 per 100 [6.0, 20.0] |
| open.incomplete_on_ground | 50/80 = 62.5 per 100 [51.5, 72.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.ended_early.declined | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.miss | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 67/80 = 83.8 per 100 [74.2, 90.3] |
| closed.strict_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.strict_confirmed | 13/80 = 16.2 per 100 [9.7, 25.8] |
| closed.lenient_caught | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_confirmed | 25/80 = 31.2 per 100 [22.2, 42.1] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.25,a=0.5

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 23/40 = 57.5 per 100 [42.2, 71.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.ended_early.declined | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| closed.lenient_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 6/40 = 15.0 per 100 [7.1, 29.1] |
| open.incomplete_on_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.ended_early.declined | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 39/40 = 97.5 per 100 [87.1, 99.6] |
| closed.strict_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.strict_confirmed | 1/40 = 2.5 per 100 [0.4, 12.9] |
| closed.lenient_caught | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_confirmed | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground_any_source | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_customer_statement | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 9/80 = 11.2 per 100 [6.0, 20.0] |
| open.incomplete_on_ground | 50/80 = 62.5 per 100 [51.5, 72.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.ended_early.declined | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.miss | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 66/80 = 82.5 per 100 [72.7, 89.3] |
| closed.strict_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.strict_confirmed | 14/80 = 17.5 per 100 [10.7, 27.3] |
| closed.lenient_caught | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_confirmed | 25/80 = 31.2 per 100 [22.2, 42.1] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.5,a=0.5

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 23/40 = 57.5 per 100 [42.2, 71.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.ended_early.declined | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| closed.lenient_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 6/40 = 15.0 per 100 [7.1, 29.1] |
| open.incomplete_on_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.ended_early.declined | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 38/40 = 95.0 per 100 [83.5, 98.6] |
| closed.strict_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.strict_confirmed | 2/40 = 5.0 per 100 [1.4, 16.5] |
| closed.lenient_caught | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_confirmed | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground_any_source | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_customer_statement | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 9/80 = 11.2 per 100 [6.0, 20.0] |
| open.incomplete_on_ground | 50/80 = 62.5 per 100 [51.5, 72.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.ended_early.declined | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.miss | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 65/80 = 81.2 per 100 [71.3, 88.3] |
| closed.strict_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.strict_confirmed | 15/80 = 18.8 per 100 [11.7, 28.7] |
| closed.lenient_caught | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_confirmed | 25/80 = 31.2 per 100 [22.2, 42.1] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.75,a=0.5

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 23/40 = 57.5 per 100 [42.2, 71.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.ended_early.declined | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| closed.lenient_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 6/40 = 15.0 per 100 [7.1, 29.1] |
| open.incomplete_on_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.ended_early.declined | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 35/40 = 87.5 per 100 [73.9, 94.5] |
| closed.strict_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.strict_confirmed | 5/40 = 12.5 per 100 [5.5, 26.1] |
| closed.lenient_caught | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_confirmed | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground_any_source | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_customer_statement | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 9/80 = 11.2 per 100 [6.0, 20.0] |
| open.incomplete_on_ground | 50/80 = 62.5 per 100 [51.5, 72.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.ended_early.declined | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.miss | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 62/80 = 77.5 per 100 [67.2, 85.3] |
| closed.strict_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.strict_confirmed | 18/80 = 22.5 per 100 [14.7, 32.8] |
| closed.lenient_caught | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_confirmed | 25/80 = 31.2 per 100 [22.2, 42.1] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=1,a=0.5

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 3/40 = 7.5 per 100 [2.6, 19.9] |
| open.incomplete_on_ground | 23/40 = 57.5 per 100 [42.2, 71.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.ended_early.declined | 15/40 = 37.5 per 100 [24.2, 53.0] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.strict_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| closed.lenient_caught | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_caught_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| closed.lenient_confirmed | 13/40 = 32.5 per 100 [20.1, 48.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_ground_any_source | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_customer_statement | 22/40 = 55.0 per 100 [39.8, 69.3] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 6/40 = 15.0 per 100 [7.1, 29.1] |
| open.incomplete_on_ground | 27/40 = 67.5 per 100 [52.0, 79.9] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.ended_early.declined | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.miss | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.strict_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.strict_confirmed | 12/40 = 30.0 per 100 [18.1, 45.4] |
| closed.lenient_caught | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_caught_ground | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.lenient_confirmed | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_ground_any_source | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_customer_statement | 44/80 = 55.0 per 100 [44.1, 65.4] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 9/80 = 11.2 per 100 [6.0, 20.0] |
| open.incomplete_on_ground | 50/80 = 62.5 per 100 [51.5, 72.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.ended_early.declined | 27/80 = 33.8 per 100 [24.3, 44.6] |
| open.miss | 36/80 = 45.0 per 100 [34.6, 55.9] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.strict_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.strict_confirmed | 25/80 = 31.2 per 100 [22.2, 42.1] |
| closed.lenient_caught | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_caught_ground | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.lenient_confirmed | 25/80 = 31.2 per 100 [22.2, 42.1] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.gap_flag_any_tier | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.gap_found_any_source | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 26/48 = 54.2 per 100 [40.3, 67.4] |
| open.understanding_gap | 3/48 = 6.2 per 100 [2.1, 16.8] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.declined | 16/48 = 33.3 per 100 [21.7, 47.5] |
| open.ended_early.turn_limit | 2/48 = 4.2 per 100 [1.2, 14.0] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 23/32 = 71.9 per 100 [54.6, 84.4] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 9/32 = 28.1 per 100 [15.6, 45.4] |
| open.ended_early.declined | 8/32 = 25.0 per 100 [13.3, 42.1] |
| open.ended_early.turn_limit | 1/32 = 3.1 per 100 [0.6, 15.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0,a=0.75

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground_any_source | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_customer_statement | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.ended_early.declined | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.miss | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| closed.lenient_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_ground | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_ground_any_source | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_basis_customer_statement | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.ended_early.declined | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.miss | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_confirmed | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.any_degraded | 1/40 = 2.5 per 100 [0.4, 12.9] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_ground | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_ground_any_source | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_basis_customer_statement | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 28/80 = 35.0 per 100 [25.5, 45.9] |
| open.incomplete_on_ground | 66/80 = 82.5 per 100 [72.7, 89.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.ended_early.declined | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.miss | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 55/80 = 68.8 per 100 [57.9, 77.8] |
| closed.strict_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.strict_confirmed | 25/80 = 31.2 per 100 [22.2, 42.1] |
| closed.lenient_caught | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_confirmed | 54/80 = 67.5 per 100 [56.6, 76.8] |
| open.any_degraded | 1/80 = 1.2 per 100 [0.2, 6.7] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.25,a=0.75

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground_any_source | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_customer_statement | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.ended_early.declined | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.miss | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| closed.lenient_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_ground | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_ground_any_source | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_basis_customer_statement | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.ended_early.declined | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.miss | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 37/40 = 92.5 per 100 [80.1, 97.4] |
| closed.strict_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.strict_confirmed | 3/40 = 7.5 per 100 [2.6, 19.9] |
| closed.lenient_caught | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_confirmed | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.any_degraded | 1/40 = 2.5 per 100 [0.4, 12.9] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_ground | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_ground_any_source | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_basis_customer_statement | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 28/80 = 35.0 per 100 [25.5, 45.9] |
| open.incomplete_on_ground | 66/80 = 82.5 per 100 [72.7, 89.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.ended_early.declined | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.miss | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 52/80 = 65.0 per 100 [54.1, 74.5] |
| closed.strict_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.strict_confirmed | 28/80 = 35.0 per 100 [25.5, 45.9] |
| closed.lenient_caught | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_confirmed | 54/80 = 67.5 per 100 [56.6, 76.8] |
| open.any_degraded | 1/80 = 1.2 per 100 [0.2, 6.7] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.5,a=0.75

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground_any_source | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_customer_statement | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.ended_early.declined | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.miss | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| closed.lenient_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_ground | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_ground_any_source | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_basis_customer_statement | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.ended_early.declined | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.miss | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 34/40 = 85.0 per 100 [70.9, 92.9] |
| closed.strict_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.strict_confirmed | 6/40 = 15.0 per 100 [7.1, 29.1] |
| closed.lenient_caught | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_confirmed | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.any_degraded | 1/40 = 2.5 per 100 [0.4, 12.9] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_ground | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_ground_any_source | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_basis_customer_statement | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 28/80 = 35.0 per 100 [25.5, 45.9] |
| open.incomplete_on_ground | 66/80 = 82.5 per 100 [72.7, 89.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.ended_early.declined | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.miss | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 49/80 = 61.2 per 100 [50.3, 71.2] |
| closed.strict_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.strict_confirmed | 31/80 = 38.8 per 100 [28.8, 49.7] |
| closed.lenient_caught | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_confirmed | 54/80 = 67.5 per 100 [56.6, 76.8] |
| open.any_degraded | 1/80 = 1.2 per 100 [0.2, 6.7] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.75,a=0.75

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground_any_source | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_customer_statement | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.ended_early.declined | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.miss | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| closed.lenient_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_ground | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_ground_any_source | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_basis_customer_statement | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.ended_early.declined | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.miss | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 25/40 = 62.5 per 100 [47.0, 75.8] |
| closed.strict_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.strict_confirmed | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_caught | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_confirmed | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.any_degraded | 1/40 = 2.5 per 100 [0.4, 12.9] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_ground | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_ground_any_source | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_basis_customer_statement | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 28/80 = 35.0 per 100 [25.5, 45.9] |
| open.incomplete_on_ground | 66/80 = 82.5 per 100 [72.7, 89.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.ended_early.declined | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.miss | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 40/80 = 50.0 per 100 [39.3, 60.7] |
| closed.strict_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.strict_confirmed | 40/80 = 50.0 per 100 [39.3, 60.7] |
| closed.lenient_caught | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_confirmed | 54/80 = 67.5 per 100 [56.6, 76.8] |
| open.any_degraded | 1/80 = 1.2 per 100 [0.2, 6.7] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=1,a=0.75

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_ground_any_source | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_customer_statement | 11/40 = 27.5 per 100 [16.1, 42.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 12/40 = 30.0 per 100 [18.1, 45.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.ended_early.declined | 17/40 = 42.5 per 100 [28.5, 57.8] |
| open.miss | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.strict_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| closed.lenient_caught | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_caught_ground | 15/40 = 37.5 per 100 [24.2, 53.0] |
| closed.lenient_confirmed | 25/40 = 62.5 per 100 [47.0, 75.8] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_ground | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_ground_any_source | 9/40 = 22.5 per 100 [12.3, 37.5] |
| open.refer_basis_customer_statement | 10/40 = 25.0 per 100 [14.2, 40.2] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 33/40 = 82.5 per 100 [68.1, 91.3] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.ended_early.declined | 14/40 = 35.0 per 100 [22.1, 50.5] |
| open.miss | 30/40 = 75.0 per 100 [59.8, 85.8] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.strict_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.strict_confirmed | 29/40 = 72.5 per 100 [57.2, 83.9] |
| closed.lenient_caught | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_caught_ground | 11/40 = 27.5 per 100 [16.1, 42.8] |
| closed.lenient_confirmed | 29/40 = 72.5 per 100 [57.2, 83.9] |
| open.any_degraded | 1/40 = 2.5 per 100 [0.4, 12.9] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 1.

| measure | count |
|---|---|
| open.refer | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_ground | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_ground_any_source | 20/80 = 25.0 per 100 [16.8, 35.5] |
| open.refer_basis_customer_statement | 21/80 = 26.2 per 100 [17.9, 36.8] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 28/80 = 35.0 per 100 [25.5, 45.9] |
| open.incomplete_on_ground | 66/80 = 82.5 per 100 [72.7, 89.3] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.ended_early.declined | 31/80 = 38.8 per 100 [28.8, 49.7] |
| open.miss | 59/80 = 73.8 per 100 [63.2, 82.1] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.strict_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.strict_confirmed | 54/80 = 67.5 per 100 [56.6, 76.8] |
| closed.lenient_caught | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_caught_ground | 26/80 = 32.5 per 100 [23.2, 43.4] |
| closed.lenient_confirmed | 54/80 = 67.5 per 100 [56.6, 76.8] |
| open.any_degraded | 1/80 = 1.2 per 100 [0.2, 6.7] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 12/48 = 25.0 per 100 [14.9, 38.8] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 28/48 = 58.3 per 100 [44.3, 71.2] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 19/48 = 39.6 per 100 [27.0, 53.7] |
| open.ended_early.declined | 18/48 = 37.5 per 100 [25.2, 51.6] |
| open.ended_early.turn_limit | 1/48 = 2.1 per 100 [0.4, 10.9] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 21/32 = 65.6 per 100 [48.3, 79.6] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.ended_early.declined | 11/32 = 34.4 per 100 [20.4, 51.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0,a=1

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.ended_early.declined | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.miss | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 21/40 = 52.5 per 100 [37.5, 67.1] |
| open.incomplete_on_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.ended_early.declined | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.miss | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_ground_any_source | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_basis_customer_statement | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 37/80 = 46.2 per 100 [35.7, 57.1] |
| open.incomplete_on_ground | 74/80 = 92.5 per 100 [84.6, 96.5] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.ended_early.declined | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.miss | 79/80 = 98.8 per 100 [93.3, 99.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 40/80 = 50.0 per 100 [39.3, 60.7] |
| closed.strict_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_confirmed | 40/80 = 50.0 per 100 [39.3, 60.7] |
| closed.lenient_caught | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_confirmed | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.strict_confirmed | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.25,a=1

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.ended_early.declined | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.miss | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 21/40 = 52.5 per 100 [37.5, 67.1] |
| open.incomplete_on_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.ended_early.declined | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.miss | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 34/40 = 85.0 per 100 [70.9, 92.9] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 6/40 = 15.0 per 100 [7.1, 29.1] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_ground_any_source | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_basis_customer_statement | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 37/80 = 46.2 per 100 [35.7, 57.1] |
| open.incomplete_on_ground | 74/80 = 92.5 per 100 [84.6, 96.5] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.ended_early.declined | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.miss | 79/80 = 98.8 per 100 [93.3, 99.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 34/80 = 42.5 per 100 [32.3, 53.4] |
| closed.strict_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_confirmed | 46/80 = 57.5 per 100 [46.6, 67.7] |
| closed.lenient_caught | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_confirmed | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 41/48 = 85.4 per 100 [72.8, 92.8] |
| closed.strict_confirmed | 7/48 = 14.6 per 100 [7.2, 27.2] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.5,a=1

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.ended_early.declined | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.miss | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 21/40 = 52.5 per 100 [37.5, 67.1] |
| open.incomplete_on_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.ended_early.declined | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.miss | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 28/40 = 70.0 per 100 [54.6, 81.9] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 12/40 = 30.0 per 100 [18.1, 45.4] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_ground_any_source | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_basis_customer_statement | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 37/80 = 46.2 per 100 [35.7, 57.1] |
| open.incomplete_on_ground | 74/80 = 92.5 per 100 [84.6, 96.5] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.ended_early.declined | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.miss | 79/80 = 98.8 per 100 [93.3, 99.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 28/80 = 35.0 per 100 [25.5, 45.9] |
| closed.strict_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_confirmed | 52/80 = 65.0 per 100 [54.1, 74.5] |
| closed.lenient_caught | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_confirmed | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 32/48 = 66.7 per 100 [52.5, 78.3] |
| closed.strict_confirmed | 16/48 = 33.3 per 100 [21.7, 47.5] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=0.75,a=1

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.ended_early.declined | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.miss | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 21/40 = 52.5 per 100 [37.5, 67.1] |
| open.incomplete_on_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.ended_early.declined | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.miss | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 16/40 = 40.0 per 100 [26.3, 55.4] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 24/40 = 60.0 per 100 [44.6, 73.7] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_ground_any_source | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_basis_customer_statement | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 37/80 = 46.2 per 100 [35.7, 57.1] |
| open.incomplete_on_ground | 74/80 = 92.5 per 100 [84.6, 96.5] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.ended_early.declined | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.miss | 79/80 = 98.8 per 100 [93.3, 99.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 16/80 = 20.0 per 100 [12.7, 30.0] |
| closed.strict_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_confirmed | 64/80 = 80.0 per 100 [70.0, 87.3] |
| closed.lenient_caught | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_confirmed | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 21/48 = 43.8 per 100 [30.7, 57.7] |
| closed.strict_confirmed | 27/48 = 56.2 per 100 [42.3, 69.3] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## Cell r=1,a=1

### kind=informed (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

### kind=knowledge_gap (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### kind=misled (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 16/40 = 40.0 per 100 [26.3, 55.4] |
| open.incomplete_on_ground | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.ended_early.declined | 24/40 = 60.0 per 100 [44.6, 73.7] |
| open.miss | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### kind=misled_with_gaps (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_ground_any_source | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.refer_basis_customer_statement | 1/40 = 2.5 per 100 [0.4, 12.9] |
| open.refer_basis_record_only | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.incomplete | 21/40 = 52.5 per 100 [37.5, 67.1] |
| open.incomplete_on_ground | 35/40 = 87.5 per 100 [73.9, 94.5] |
| open.understanding_gap | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.clear | 0/40 = 0.0 per 100 [0.0, 8.8] |
| open.ended_early | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.ended_early.declined | 18/40 = 45.0 per 100 [30.7, 60.2] |
| open.miss | 39/40 = 97.5 per 100 [87.1, 99.6] |
| open.silent_miss | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.strict_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| closed.lenient_caught | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_caught_ground | 0/40 = 0.0 per 100 [0.0, 8.8] |
| closed.lenient_confirmed | 40/40 = 100.0 per 100 [91.2, 100.0] |
| open.any_degraded | 0/40 = 0.0 per 100 [0.0, 8.8] |

### class=problem (family problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_ground_any_source | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.refer_basis_customer_statement | 1/80 = 1.2 per 100 [0.2, 6.7] |
| open.refer_basis_record_only | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.incomplete | 37/80 = 46.2 per 100 [35.7, 57.1] |
| open.incomplete_on_ground | 74/80 = 92.5 per 100 [84.6, 96.5] |
| open.understanding_gap | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.clear | 0/80 = 0.0 per 100 [0.0, 4.6] |
| open.ended_early | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.ended_early.declined | 42/80 = 52.5 per 100 [41.7, 63.1] |
| open.miss | 79/80 = 98.8 per 100 [93.3, 99.8] |
| open.silent_miss | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.strict_confirmed | 80/80 = 100.0 per 100 [95.4, 100.0] |
| closed.lenient_caught | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_caught_ground | 0/80 = 0.0 per 100 [0.0, 4.6] |
| closed.lenient_confirmed | 80/80 = 100.0 per 100 [95.4, 100.0] |
| open.any_degraded | 0/80 = 0.0 per 100 [0.0, 4.6] |

### class=knowledge_gap_only (family knowledge_gap_only)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_flag_any_tier | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.gap_found_any_source | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.refer | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_customer_statement | 1/48 = 2.1 per 100 [0.4, 10.9] |
| open.refer_basis_record_only | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.incomplete | 24/48 = 50.0 per 100 [36.4, 63.6] |
| open.understanding_gap | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.clear | 0/48 = 0.0 per 100 [0.0, 7.4] |
| open.ended_early | 23/48 = 47.9 per 100 [34.5, 61.7] |
| open.ended_early.declined | 23/48 = 47.9 per 100 [34.5, 61.7] |
| closed.strict_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.strict_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| closed.lenient_gap_found | 0/48 = 0.0 per 100 [0.0, 7.4] |
| closed.lenient_confirmed | 48/48 = 100.0 per 100 [92.6, 100.0] |
| open.any_degraded | 0/48 = 0.0 per 100 [0.0, 7.4] |

### class=no_problem (family no_problem)

Excluded: entry_failed 0, no_result 0, missing_open 0, missing_closed 0. n excludes open calls with status entry_failed or no_result (counted on the line above). Degraded turns in counted calls: 0.

| measure | count |
|---|---|
| open.refer | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_customer_statement | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.refer_basis_record_only | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.incomplete | 18/32 = 56.2 per 100 [39.3, 71.8] |
| open.understanding_gap | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.clear | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.ended_early | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.ended_early.declined | 14/32 = 43.8 per 100 [28.2, 60.7] |
| open.not_clear | 32/32 = 100.0 per 100 [89.3, 100.0] |
| closed.strict_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| closed.lenient_caught | 0/32 = 0.0 per 100 [0.0, 10.7] |
| open.any_degraded | 0/32 = 0.0 per 100 [0.0, 10.7] |

## McNemar: primary

| cell | group | pair | b open only | c closed only | both | neither | p |
|---|---|---|---|---|---|---|---|
| r=0,a=0 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=0,a=0 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=0,a=0 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 80 | 0 | 1 |
| r=0.25,a=0 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=0.25,a=0 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=0.25,a=0 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 80 | 0 | 1 |
| r=0.5,a=0 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 16 | 3 | 29 | 0 | 0.00443 |
| r=0.5,a=0 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=0.5,a=0 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=0.5,a=0 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 80 | 0 | 1 |
| r=0.5,a=0 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 16 | 3 | 29 | 0 | 0.00443 |
| r=0.75,a=0 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 25 | 1 | 20 | 2 | 8.05e-07 |
| r=0.75,a=0 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=0.75,a=0 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=0.75,a=0 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 80 | 0 | 1 |
| r=0.75,a=0 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 25 | 1 | 20 | 2 | 8.05e-07 |
| r=1,a=0 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 45 | 0 | 0 | 3 | 5.68e-14 |
| r=1,a=0 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=1,a=0 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 40 | 0 | 1 |
| r=1,a=0 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 80 | 0 | 1 |
| r=1,a=0 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 45 | 0 | 0 | 3 | 5.68e-14 |

## McNemar: descriptive, not a test

| cell | group | pair | b open only | c closed only | both | neither | p |
|---|---|---|---|---|---|---|---|
| r=0,a=0 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 3 | 45 | 0 | 0.25 |
| r=0,a=0 | kind=knowledge_gap | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0,a=0 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0,a=0 | kind=misled | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0,a=0 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0,a=0 | kind=misled_with_gaps | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0,a=0 | class=problem | P2b:refer~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=0,a=0 | class=problem | P3:not_clear~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=0,a=0 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 3 | 45 | 0 | 0.25 |
| r=0,a=0 | class=knowledge_gap_only | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0.25,a=0 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 7 | 3 | 38 | 0 | 0.344 |
| r=0.25,a=0 | kind=knowledge_gap | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.25,a=0 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.25,a=0 | kind=misled | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.25,a=0 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.25,a=0 | kind=misled_with_gaps | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.25,a=0 | class=problem | P2b:refer~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=0.25,a=0 | class=problem | P3:not_clear~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=0.25,a=0 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 7 | 3 | 38 | 0 | 0.344 |
| r=0.25,a=0 | class=knowledge_gap_only | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.5,a=0 | kind=knowledge_gap | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.5,a=0 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.5,a=0 | kind=misled | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.5,a=0 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.5,a=0 | kind=misled_with_gaps | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.5,a=0 | class=problem | P2b:refer~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=0.5,a=0 | class=problem | P3:not_clear~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=0.5,a=0 | class=knowledge_gap_only | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.75,a=0 | kind=knowledge_gap | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=0.75,a=0 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.75,a=0 | kind=misled | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.75,a=0 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.75,a=0 | kind=misled_with_gaps | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0.75,a=0 | class=problem | P2b:refer~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=0.75,a=0 | class=problem | P3:not_clear~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=0.75,a=0 | class=knowledge_gap_only | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=1,a=0 | kind=knowledge_gap | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |
| r=1,a=0 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=1,a=0 | kind=misled | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=1,a=0 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=1,a=0 | kind=misled_with_gaps | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=1,a=0 | class=problem | P2b:refer~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=1,a=0 | class=problem | P3:not_clear~strict_caught | 0 | 0 | 80 | 0 | 1 |
| r=1,a=0 | class=knowledge_gap_only | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |
| r=0,a=0.25 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 39 | 9 | 0 | 3.64e-12 |
| r=0,a=0.25 | kind=knowledge_gap | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0,a=0.25 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 6 | 29 | 5 | 0.0312 |
| r=0,a=0.25 | kind=misled | P2b:refer~strict_caught | 0 | 6 | 29 | 5 | 0.0312 |
| r=0,a=0.25 | kind=misled | P3:not_clear~strict_caught | 5 | 0 | 35 | 0 | 0.0625 |
| r=0,a=0.25 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 4 | 29 | 6 | 0.375 |
| r=0,a=0.25 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 10 | 30 | 0 | 0.00195 |
| r=0,a=0.25 | kind=misled_with_gaps | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0,a=0.25 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 10 | 58 | 11 | 0.0117 |
| r=0,a=0.25 | class=problem | P2b:refer~strict_caught | 0 | 16 | 59 | 5 | 3.05e-05 |
| r=0,a=0.25 | class=problem | P3:not_clear~strict_caught | 5 | 0 | 75 | 0 | 0.0625 |
| r=0,a=0.25 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 39 | 9 | 0 | 3.64e-12 |
| r=0,a=0.25 | class=knowledge_gap_only | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0.25,a=0.25 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 2 | 34 | 7 | 5 | 1.94e-08 |
| r=0.25,a=0.25 | kind=knowledge_gap | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.25,a=0.25 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 6 | 29 | 5 | 0.0312 |
| r=0.25,a=0.25 | kind=misled | P2b:refer~strict_caught | 0 | 6 | 29 | 5 | 0.0312 |
| r=0.25,a=0.25 | kind=misled | P3:not_clear~strict_caught | 5 | 0 | 35 | 0 | 0.0625 |
| r=0.25,a=0.25 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 4 | 29 | 6 | 0.375 |
| r=0.25,a=0.25 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 9 | 30 | 1 | 0.00391 |
| r=0.25,a=0.25 | kind=misled_with_gaps | P3:not_clear~strict_caught | 1 | 0 | 39 | 0 | 1 |
| r=0.25,a=0.25 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 10 | 58 | 11 | 0.0117 |
| r=0.25,a=0.25 | class=problem | P2b:refer~strict_caught | 0 | 15 | 59 | 6 | 6.1e-05 |
| r=0.25,a=0.25 | class=problem | P3:not_clear~strict_caught | 6 | 0 | 74 | 0 | 0.0312 |
| r=0.25,a=0.25 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 2 | 34 | 7 | 5 | 1.94e-08 |
| r=0.25,a=0.25 | class=knowledge_gap_only | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.5,a=0.25 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 3 | 26 | 6 | 13 | 1.52e-05 |
| r=0.5,a=0.25 | kind=knowledge_gap | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.5,a=0.25 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 6 | 29 | 5 | 0.0312 |
| r=0.5,a=0.25 | kind=misled | P2b:refer~strict_caught | 0 | 6 | 29 | 5 | 0.0312 |
| r=0.5,a=0.25 | kind=misled | P3:not_clear~strict_caught | 5 | 0 | 35 | 0 | 0.0625 |
| r=0.5,a=0.25 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 4 | 29 | 6 | 0.375 |
| r=0.5,a=0.25 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 8 | 30 | 2 | 0.00781 |
| r=0.5,a=0.25 | kind=misled_with_gaps | P3:not_clear~strict_caught | 2 | 0 | 38 | 0 | 0.5 |
| r=0.5,a=0.25 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 10 | 58 | 11 | 0.0117 |
| r=0.5,a=0.25 | class=problem | P2b:refer~strict_caught | 0 | 14 | 59 | 7 | 0.000122 |
| r=0.5,a=0.25 | class=problem | P3:not_clear~strict_caught | 7 | 0 | 73 | 0 | 0.0156 |
| r=0.5,a=0.25 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 3 | 26 | 6 | 13 | 1.52e-05 |
| r=0.5,a=0.25 | class=knowledge_gap_only | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.75,a=0.25 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 3 | 15 | 6 | 24 | 0.00754 |
| r=0.75,a=0.25 | kind=knowledge_gap | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=0.75,a=0.25 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 6 | 29 | 5 | 0.0312 |
| r=0.75,a=0.25 | kind=misled | P2b:refer~strict_caught | 0 | 6 | 29 | 5 | 0.0312 |
| r=0.75,a=0.25 | kind=misled | P3:not_clear~strict_caught | 5 | 0 | 35 | 0 | 0.0625 |
| r=0.75,a=0.25 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 4 | 29 | 6 | 0.375 |
| r=0.75,a=0.25 | kind=misled_with_gaps | P2b:refer~strict_caught | 1 | 8 | 29 | 2 | 0.0391 |
| r=0.75,a=0.25 | kind=misled_with_gaps | P3:not_clear~strict_caught | 3 | 0 | 37 | 0 | 0.25 |
| r=0.75,a=0.25 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 10 | 58 | 11 | 0.0117 |
| r=0.75,a=0.25 | class=problem | P2b:refer~strict_caught | 1 | 14 | 58 | 7 | 0.000977 |
| r=0.75,a=0.25 | class=problem | P3:not_clear~strict_caught | 8 | 0 | 72 | 0 | 0.00781 |
| r=0.75,a=0.25 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 3 | 15 | 6 | 24 | 0.00754 |
| r=0.75,a=0.25 | class=knowledge_gap_only | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=1,a=0.25 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 9 | 0 | 0 | 39 | 0.00391 |
| r=1,a=0.25 | kind=knowledge_gap | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |
| r=1,a=0.25 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 6 | 29 | 5 | 0.0312 |
| r=1,a=0.25 | kind=misled | P2b:refer~strict_caught | 0 | 6 | 29 | 5 | 0.0312 |
| r=1,a=0.25 | kind=misled | P3:not_clear~strict_caught | 5 | 0 | 35 | 0 | 0.0625 |
| r=1,a=0.25 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 4 | 29 | 6 | 0.375 |
| r=1,a=0.25 | kind=misled_with_gaps | P2b:refer~strict_caught | 1 | 4 | 29 | 6 | 0.375 |
| r=1,a=0.25 | kind=misled_with_gaps | P3:not_clear~strict_caught | 7 | 0 | 33 | 0 | 0.0156 |
| r=1,a=0.25 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 10 | 58 | 11 | 0.0117 |
| r=1,a=0.25 | class=problem | P2b:refer~strict_caught | 1 | 10 | 58 | 11 | 0.0117 |
| r=1,a=0.25 | class=problem | P3:not_clear~strict_caught | 12 | 0 | 68 | 0 | 0.000488 |
| r=1,a=0.25 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 9 | 0 | 0 | 39 | 0.00391 |
| r=1,a=0.25 | class=knowledge_gap_only | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |
| r=0,a=0.5 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 45 | 3 | 0 | 5.68e-14 |
| r=0,a=0.5 | kind=knowledge_gap | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0,a=0.5 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 5 | 22 | 13 | 0.0625 |
| r=0,a=0.5 | kind=misled | P2b:refer~strict_caught | 0 | 5 | 22 | 13 | 0.0625 |
| r=0,a=0.5 | kind=misled | P3:not_clear~strict_caught | 13 | 0 | 27 | 0 | 0.000244 |
| r=0,a=0.5 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 7 | 21 | 11 | 0.0703 |
| r=0,a=0.5 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 18 | 22 | 0 | 7.63e-06 |
| r=0,a=0.5 | kind=misled_with_gaps | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0,a=0.5 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 12 | 43 | 24 | 0.00342 |
| r=0,a=0.5 | class=problem | P2b:refer~strict_caught | 0 | 23 | 44 | 13 | 2.38e-07 |
| r=0,a=0.5 | class=problem | P3:not_clear~strict_caught | 13 | 0 | 67 | 0 | 0.000244 |
| r=0,a=0.5 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 45 | 3 | 0 | 5.68e-14 |
| r=0,a=0.5 | class=knowledge_gap_only | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0.25,a=0.5 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 1 | 39 | 2 | 6 | 7.46e-11 |
| r=0.25,a=0.5 | kind=knowledge_gap | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.25,a=0.5 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 5 | 22 | 13 | 0.0625 |
| r=0.25,a=0.5 | kind=misled | P2b:refer~strict_caught | 0 | 5 | 22 | 13 | 0.0625 |
| r=0.25,a=0.5 | kind=misled | P3:not_clear~strict_caught | 13 | 0 | 27 | 0 | 0.000244 |
| r=0.25,a=0.5 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 7 | 21 | 11 | 0.0703 |
| r=0.25,a=0.5 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 17 | 22 | 1 | 1.53e-05 |
| r=0.25,a=0.5 | kind=misled_with_gaps | P3:not_clear~strict_caught | 1 | 0 | 39 | 0 | 1 |
| r=0.25,a=0.5 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 12 | 43 | 24 | 0.00342 |
| r=0.25,a=0.5 | class=problem | P2b:refer~strict_caught | 0 | 22 | 44 | 14 | 4.77e-07 |
| r=0.25,a=0.5 | class=problem | P3:not_clear~strict_caught | 14 | 0 | 66 | 0 | 0.000122 |
| r=0.25,a=0.5 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 1 | 39 | 2 | 6 | 7.46e-11 |
| r=0.25,a=0.5 | class=knowledge_gap_only | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.5,a=0.5 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 1 | 30 | 2 | 15 | 2.98e-08 |
| r=0.5,a=0.5 | kind=knowledge_gap | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.5,a=0.5 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 5 | 22 | 13 | 0.0625 |
| r=0.5,a=0.5 | kind=misled | P2b:refer~strict_caught | 0 | 5 | 22 | 13 | 0.0625 |
| r=0.5,a=0.5 | kind=misled | P3:not_clear~strict_caught | 13 | 0 | 27 | 0 | 0.000244 |
| r=0.5,a=0.5 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 7 | 21 | 11 | 0.0703 |
| r=0.5,a=0.5 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 16 | 22 | 2 | 3.05e-05 |
| r=0.5,a=0.5 | kind=misled_with_gaps | P3:not_clear~strict_caught | 2 | 0 | 38 | 0 | 0.5 |
| r=0.5,a=0.5 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 12 | 43 | 24 | 0.00342 |
| r=0.5,a=0.5 | class=problem | P2b:refer~strict_caught | 0 | 21 | 44 | 15 | 9.54e-07 |
| r=0.5,a=0.5 | class=problem | P3:not_clear~strict_caught | 15 | 0 | 65 | 0 | 6.1e-05 |
| r=0.5,a=0.5 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 1 | 30 | 2 | 15 | 2.98e-08 |
| r=0.5,a=0.5 | class=knowledge_gap_only | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.75,a=0.5 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 1 | 19 | 2 | 26 | 4.01e-05 |
| r=0.75,a=0.5 | kind=knowledge_gap | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=0.75,a=0.5 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 5 | 22 | 13 | 0.0625 |
| r=0.75,a=0.5 | kind=misled | P2b:refer~strict_caught | 0 | 5 | 22 | 13 | 0.0625 |
| r=0.75,a=0.5 | kind=misled | P3:not_clear~strict_caught | 13 | 0 | 27 | 0 | 0.000244 |
| r=0.75,a=0.5 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 7 | 21 | 11 | 0.0703 |
| r=0.75,a=0.5 | kind=misled_with_gaps | P2b:refer~strict_caught | 1 | 14 | 21 | 4 | 0.000977 |
| r=0.75,a=0.5 | kind=misled_with_gaps | P3:not_clear~strict_caught | 5 | 0 | 35 | 0 | 0.0625 |
| r=0.75,a=0.5 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 12 | 43 | 24 | 0.00342 |
| r=0.75,a=0.5 | class=problem | P2b:refer~strict_caught | 1 | 19 | 43 | 17 | 4.01e-05 |
| r=0.75,a=0.5 | class=problem | P3:not_clear~strict_caught | 18 | 0 | 62 | 0 | 7.63e-06 |
| r=0.75,a=0.5 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 1 | 19 | 2 | 26 | 4.01e-05 |
| r=0.75,a=0.5 | class=knowledge_gap_only | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=1,a=0.5 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 3 | 0 | 0 | 45 | 0.25 |
| r=1,a=0.5 | kind=knowledge_gap | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |
| r=1,a=0.5 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 5 | 22 | 13 | 0.0625 |
| r=1,a=0.5 | kind=misled | P2b:refer~strict_caught | 0 | 5 | 22 | 13 | 0.0625 |
| r=1,a=0.5 | kind=misled | P3:not_clear~strict_caught | 13 | 0 | 27 | 0 | 0.000244 |
| r=1,a=0.5 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 1 | 7 | 21 | 11 | 0.0703 |
| r=1,a=0.5 | kind=misled_with_gaps | P2b:refer~strict_caught | 1 | 7 | 21 | 11 | 0.0703 |
| r=1,a=0.5 | kind=misled_with_gaps | P3:not_clear~strict_caught | 12 | 0 | 28 | 0 | 0.000488 |
| r=1,a=0.5 | class=problem | P2a:refer_ground~strict_caught_ground | 1 | 12 | 43 | 24 | 0.00342 |
| r=1,a=0.5 | class=problem | P2b:refer~strict_caught | 1 | 12 | 43 | 24 | 0.00342 |
| r=1,a=0.5 | class=problem | P3:not_clear~strict_caught | 25 | 0 | 55 | 0 | 5.96e-08 |
| r=1,a=0.5 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 3 | 0 | 0 | 45 | 0.25 |
| r=1,a=0.5 | class=knowledge_gap_only | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |
| r=0,a=0.75 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 48 | 0 | 0 | 7.11e-15 |
| r=0,a=0.75 | kind=knowledge_gap | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0,a=0.75 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 4 | 11 | 25 | 0.125 |
| r=0,a=0.75 | kind=misled | P2b:refer~strict_caught | 0 | 4 | 11 | 25 | 0.125 |
| r=0,a=0.75 | kind=misled | P3:not_clear~strict_caught | 25 | 0 | 15 | 0 | 5.96e-08 |
| r=0,a=0.75 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 2 | 9 | 29 | 0.5 |
| r=0,a=0.75 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 30 | 10 | 0 | 1.86e-09 |
| r=0,a=0.75 | kind=misled_with_gaps | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0,a=0.75 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 6 | 20 | 54 | 0.0312 |
| r=0,a=0.75 | class=problem | P2b:refer~strict_caught | 0 | 34 | 21 | 25 | 1.16e-10 |
| r=0,a=0.75 | class=problem | P3:not_clear~strict_caught | 25 | 0 | 55 | 0 | 5.96e-08 |
| r=0,a=0.75 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 48 | 0 | 0 | 7.11e-15 |
| r=0,a=0.75 | class=knowledge_gap_only | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0.25,a=0.75 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 41 | 0 | 7 | 9.09e-13 |
| r=0.25,a=0.75 | kind=knowledge_gap | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.25,a=0.75 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 4 | 11 | 25 | 0.125 |
| r=0.25,a=0.75 | kind=misled | P2b:refer~strict_caught | 0 | 4 | 11 | 25 | 0.125 |
| r=0.25,a=0.75 | kind=misled | P3:not_clear~strict_caught | 25 | 0 | 15 | 0 | 5.96e-08 |
| r=0.25,a=0.75 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 2 | 9 | 29 | 0.5 |
| r=0.25,a=0.75 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 27 | 10 | 3 | 1.49e-08 |
| r=0.25,a=0.75 | kind=misled_with_gaps | P3:not_clear~strict_caught | 3 | 0 | 37 | 0 | 0.25 |
| r=0.25,a=0.75 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 6 | 20 | 54 | 0.0312 |
| r=0.25,a=0.75 | class=problem | P2b:refer~strict_caught | 0 | 31 | 21 | 28 | 9.31e-10 |
| r=0.25,a=0.75 | class=problem | P3:not_clear~strict_caught | 28 | 0 | 52 | 0 | 7.45e-09 |
| r=0.25,a=0.75 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 41 | 0 | 7 | 9.09e-13 |
| r=0.25,a=0.75 | class=knowledge_gap_only | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.5,a=0.75 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 32 | 0 | 16 | 4.66e-10 |
| r=0.5,a=0.75 | kind=knowledge_gap | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.5,a=0.75 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 4 | 11 | 25 | 0.125 |
| r=0.5,a=0.75 | kind=misled | P2b:refer~strict_caught | 0 | 4 | 11 | 25 | 0.125 |
| r=0.5,a=0.75 | kind=misled | P3:not_clear~strict_caught | 25 | 0 | 15 | 0 | 5.96e-08 |
| r=0.5,a=0.75 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 2 | 9 | 29 | 0.5 |
| r=0.5,a=0.75 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 24 | 10 | 6 | 1.19e-07 |
| r=0.5,a=0.75 | kind=misled_with_gaps | P3:not_clear~strict_caught | 6 | 0 | 34 | 0 | 0.0312 |
| r=0.5,a=0.75 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 6 | 20 | 54 | 0.0312 |
| r=0.5,a=0.75 | class=problem | P2b:refer~strict_caught | 0 | 28 | 21 | 31 | 7.45e-09 |
| r=0.5,a=0.75 | class=problem | P3:not_clear~strict_caught | 31 | 0 | 49 | 0 | 9.31e-10 |
| r=0.5,a=0.75 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 32 | 0 | 16 | 4.66e-10 |
| r=0.5,a=0.75 | class=knowledge_gap_only | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.75,a=0.75 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 21 | 0 | 27 | 9.54e-07 |
| r=0.75,a=0.75 | kind=knowledge_gap | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=0.75,a=0.75 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 4 | 11 | 25 | 0.125 |
| r=0.75,a=0.75 | kind=misled | P2b:refer~strict_caught | 0 | 4 | 11 | 25 | 0.125 |
| r=0.75,a=0.75 | kind=misled | P3:not_clear~strict_caught | 25 | 0 | 15 | 0 | 5.96e-08 |
| r=0.75,a=0.75 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 2 | 9 | 29 | 0.5 |
| r=0.75,a=0.75 | kind=misled_with_gaps | P2b:refer~strict_caught | 1 | 16 | 9 | 14 | 0.000275 |
| r=0.75,a=0.75 | kind=misled_with_gaps | P3:not_clear~strict_caught | 15 | 0 | 25 | 0 | 6.1e-05 |
| r=0.75,a=0.75 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 6 | 20 | 54 | 0.0312 |
| r=0.75,a=0.75 | class=problem | P2b:refer~strict_caught | 1 | 20 | 20 | 39 | 2.1e-05 |
| r=0.75,a=0.75 | class=problem | P3:not_clear~strict_caught | 40 | 0 | 40 | 0 | 1.82e-12 |
| r=0.75,a=0.75 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 21 | 0 | 27 | 9.54e-07 |
| r=0.75,a=0.75 | class=knowledge_gap_only | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=1,a=0.75 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 0 | 0 | 48 | 1 |
| r=1,a=0.75 | kind=knowledge_gap | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |
| r=1,a=0.75 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 4 | 11 | 25 | 0.125 |
| r=1,a=0.75 | kind=misled | P2b:refer~strict_caught | 0 | 4 | 11 | 25 | 0.125 |
| r=1,a=0.75 | kind=misled | P3:not_clear~strict_caught | 25 | 0 | 15 | 0 | 5.96e-08 |
| r=1,a=0.75 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 2 | 9 | 29 | 0.5 |
| r=1,a=0.75 | kind=misled_with_gaps | P2b:refer~strict_caught | 1 | 2 | 9 | 28 | 1 |
| r=1,a=0.75 | kind=misled_with_gaps | P3:not_clear~strict_caught | 29 | 0 | 11 | 0 | 3.73e-09 |
| r=1,a=0.75 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 6 | 20 | 54 | 0.0312 |
| r=1,a=0.75 | class=problem | P2b:refer~strict_caught | 1 | 6 | 20 | 53 | 0.125 |
| r=1,a=0.75 | class=problem | P3:not_clear~strict_caught | 54 | 0 | 26 | 0 | 1.11e-16 |
| r=1,a=0.75 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 0 | 0 | 48 | 1 |
| r=1,a=0.75 | class=knowledge_gap_only | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |
| r=0,a=1 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 48 | 0 | 0 | 7.11e-15 |
| r=0,a=1 | kind=knowledge_gap | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0,a=1 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=0,a=1 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 0 | 40 | 1 |
| r=0,a=1 | kind=misled | P3:not_clear~strict_caught | 40 | 0 | 0 | 0 | 1.82e-12 |
| r=0,a=1 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=0,a=1 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 39 | 1 | 0 | 3.64e-12 |
| r=0,a=1 | kind=misled_with_gaps | P3:not_clear~strict_caught | 0 | 0 | 40 | 0 | 1 |
| r=0,a=1 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 80 | 1 |
| r=0,a=1 | class=problem | P2b:refer~strict_caught | 0 | 39 | 1 | 40 | 3.64e-12 |
| r=0,a=1 | class=problem | P3:not_clear~strict_caught | 40 | 0 | 40 | 0 | 1.82e-12 |
| r=0,a=1 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 48 | 0 | 0 | 7.11e-15 |
| r=0,a=1 | class=knowledge_gap_only | P3:not_clear~strict_caught | 0 | 0 | 48 | 0 | 1 |
| r=0.25,a=1 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 41 | 0 | 7 | 9.09e-13 |
| r=0.25,a=1 | kind=knowledge_gap | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.25,a=1 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=0.25,a=1 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 0 | 40 | 1 |
| r=0.25,a=1 | kind=misled | P3:not_clear~strict_caught | 40 | 0 | 0 | 0 | 1.82e-12 |
| r=0.25,a=1 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=0.25,a=1 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 33 | 1 | 6 | 2.33e-10 |
| r=0.25,a=1 | kind=misled_with_gaps | P3:not_clear~strict_caught | 6 | 0 | 34 | 0 | 0.0312 |
| r=0.25,a=1 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 80 | 1 |
| r=0.25,a=1 | class=problem | P2b:refer~strict_caught | 0 | 33 | 1 | 46 | 2.33e-10 |
| r=0.25,a=1 | class=problem | P3:not_clear~strict_caught | 46 | 0 | 34 | 0 | 2.84e-14 |
| r=0.25,a=1 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 41 | 0 | 7 | 9.09e-13 |
| r=0.25,a=1 | class=knowledge_gap_only | P3:not_clear~strict_caught | 7 | 0 | 41 | 0 | 0.0156 |
| r=0.5,a=1 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 32 | 0 | 16 | 4.66e-10 |
| r=0.5,a=1 | kind=knowledge_gap | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.5,a=1 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=0.5,a=1 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 0 | 40 | 1 |
| r=0.5,a=1 | kind=misled | P3:not_clear~strict_caught | 40 | 0 | 0 | 0 | 1.82e-12 |
| r=0.5,a=1 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=0.5,a=1 | kind=misled_with_gaps | P2b:refer~strict_caught | 0 | 27 | 1 | 12 | 1.49e-08 |
| r=0.5,a=1 | kind=misled_with_gaps | P3:not_clear~strict_caught | 12 | 0 | 28 | 0 | 0.000488 |
| r=0.5,a=1 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 80 | 1 |
| r=0.5,a=1 | class=problem | P2b:refer~strict_caught | 0 | 27 | 1 | 52 | 1.49e-08 |
| r=0.5,a=1 | class=problem | P3:not_clear~strict_caught | 52 | 0 | 28 | 0 | 4.44e-16 |
| r=0.5,a=1 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 32 | 0 | 16 | 4.66e-10 |
| r=0.5,a=1 | class=knowledge_gap_only | P3:not_clear~strict_caught | 16 | 0 | 32 | 0 | 3.05e-05 |
| r=0.75,a=1 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 21 | 0 | 27 | 9.54e-07 |
| r=0.75,a=1 | kind=knowledge_gap | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=0.75,a=1 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=0.75,a=1 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 0 | 40 | 1 |
| r=0.75,a=1 | kind=misled | P3:not_clear~strict_caught | 40 | 0 | 0 | 0 | 1.82e-12 |
| r=0.75,a=1 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=0.75,a=1 | kind=misled_with_gaps | P2b:refer~strict_caught | 1 | 16 | 0 | 23 | 0.000275 |
| r=0.75,a=1 | kind=misled_with_gaps | P3:not_clear~strict_caught | 24 | 0 | 16 | 0 | 1.19e-07 |
| r=0.75,a=1 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 80 | 1 |
| r=0.75,a=1 | class=problem | P2b:refer~strict_caught | 1 | 16 | 0 | 63 | 0.000275 |
| r=0.75,a=1 | class=problem | P3:not_clear~strict_caught | 64 | 0 | 16 | 0 | 1.08e-19 |
| r=0.75,a=1 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 21 | 0 | 27 | 9.54e-07 |
| r=0.75,a=1 | class=knowledge_gap_only | P3:not_clear~strict_caught | 27 | 0 | 21 | 0 | 1.49e-08 |
| r=1,a=1 | kind=knowledge_gap | P1:gap_found~strict_gap_found | 0 | 0 | 0 | 48 | 1 |
| r=1,a=1 | kind=knowledge_gap | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |
| r=1,a=1 | kind=misled | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=1,a=1 | kind=misled | P2b:refer~strict_caught | 0 | 0 | 0 | 40 | 1 |
| r=1,a=1 | kind=misled | P3:not_clear~strict_caught | 40 | 0 | 0 | 0 | 1.82e-12 |
| r=1,a=1 | kind=misled_with_gaps | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 40 | 1 |
| r=1,a=1 | kind=misled_with_gaps | P2b:refer~strict_caught | 1 | 0 | 0 | 39 | 1 |
| r=1,a=1 | kind=misled_with_gaps | P3:not_clear~strict_caught | 40 | 0 | 0 | 0 | 1.82e-12 |
| r=1,a=1 | class=problem | P2a:refer_ground~strict_caught_ground | 0 | 0 | 0 | 80 | 1 |
| r=1,a=1 | class=problem | P2b:refer~strict_caught | 1 | 0 | 0 | 79 | 1 |
| r=1,a=1 | class=problem | P3:not_clear~strict_caught | 80 | 0 | 0 | 0 | 1.65e-24 |
| r=1,a=1 | class=knowledge_gap_only | P1:gap_found~strict_gap_found | 0 | 0 | 0 | 48 | 1 |
| r=1,a=1 | class=knowledge_gap_only | P3:not_clear~strict_caught | 48 | 0 | 0 | 0 | 7.11e-15 |

## Counts by writer model and language, a=0 (no tests)

### writer_model

- deepseek/deepseek-v4.1-flash | knowledge_gap_only: closed_r0.strict_caught 24, closed_r1.strict_caught 0, n 24, open.clear 0, open.ended_early 2, open.incomplete 0, open.refer 0, open.understanding_gap 22
- deepseek/deepseek-v4.1-flash | no_problem: closed_r0.strict_caught 0, closed_r1.strict_caught 0, n 16, open.clear 14, open.ended_early 1, open.incomplete 1, open.refer 0, open.understanding_gap 0
- deepseek/deepseek-v4.1-flash | problem: closed_r0.strict_caught 40, closed_r1.strict_caught 40, n 40, open.clear 0, open.ended_early 0, open.incomplete 0, open.refer 40, open.understanding_gap 0
- google/gemini-3.7-flash | knowledge_gap_only: closed_r0.strict_caught 24, closed_r1.strict_caught 0, n 24, open.clear 0, open.ended_early 0, open.incomplete 0, open.refer 1, open.understanding_gap 23
- google/gemini-3.7-flash | no_problem: closed_r0.strict_caught 0, closed_r1.strict_caught 0, n 16, open.clear 14, open.ended_early 0, open.incomplete 0, open.refer 0, open.understanding_gap 2
- google/gemini-3.7-flash | problem: closed_r0.strict_caught 40, closed_r1.strict_caught 40, n 40, open.clear 0, open.ended_early 0, open.incomplete 0, open.refer 40, open.understanding_gap 0

### language

- hi | knowledge_gap_only: closed_r0.strict_caught 24, closed_r1.strict_caught 0, n 24, open.clear 0, open.ended_early 2, open.incomplete 0, open.refer 1, open.understanding_gap 21
- hi | no_problem: closed_r0.strict_caught 0, closed_r1.strict_caught 0, n 16, open.clear 14, open.ended_early 0, open.incomplete 0, open.refer 0, open.understanding_gap 2
- hi | problem: closed_r0.strict_caught 40, closed_r1.strict_caught 40, n 40, open.clear 0, open.ended_early 0, open.incomplete 0, open.refer 40, open.understanding_gap 0
- hi-en | knowledge_gap_only: closed_r0.strict_caught 24, closed_r1.strict_caught 0, n 24, open.clear 0, open.ended_early 0, open.incomplete 0, open.refer 0, open.understanding_gap 24
- hi-en | no_problem: closed_r0.strict_caught 0, closed_r1.strict_caught 0, n 16, open.clear 14, open.ended_early 1, open.incomplete 1, open.refer 0, open.understanding_gap 0
- hi-en | problem: closed_r0.strict_caught 40, closed_r1.strict_caught 40, n 40, open.clear 0, open.ended_early 0, open.incomplete 0, open.refer 40, open.understanding_gap 0

## Counts by writer model and language, a=1 (no tests)

### writer_model

- deepseek/deepseek-v4.1-flash | knowledge_gap_only: closed_r0.strict_caught 24, closed_r1.strict_caught 0, n 24, open.clear 0, open.ended_early 5, open.incomplete 18, open.refer 1, open.understanding_gap 0
- deepseek/deepseek-v4.1-flash | no_problem: closed_r0.strict_caught 0, closed_r1.strict_caught 0, n 16, open.clear 0, open.ended_early 3, open.incomplete 13, open.refer 0, open.understanding_gap 0
- deepseek/deepseek-v4.1-flash | problem: closed_r0.strict_caught 20, closed_r1.strict_caught 0, n 40, open.clear 0, open.ended_early 8, open.incomplete 31, open.refer 1, open.understanding_gap 0
- google/gemini-3.7-flash | knowledge_gap_only: closed_r0.strict_caught 24, closed_r1.strict_caught 0, n 24, open.clear 0, open.ended_early 18, open.incomplete 6, open.refer 0, open.understanding_gap 0
- google/gemini-3.7-flash | no_problem: closed_r0.strict_caught 0, closed_r1.strict_caught 0, n 16, open.clear 0, open.ended_early 11, open.incomplete 5, open.refer 0, open.understanding_gap 0
- google/gemini-3.7-flash | problem: closed_r0.strict_caught 20, closed_r1.strict_caught 0, n 40, open.clear 0, open.ended_early 34, open.incomplete 6, open.refer 0, open.understanding_gap 0

### language

- hi | knowledge_gap_only: closed_r0.strict_caught 24, closed_r1.strict_caught 0, n 24, open.clear 0, open.ended_early 13, open.incomplete 11, open.refer 0, open.understanding_gap 0
- hi | no_problem: closed_r0.strict_caught 0, closed_r1.strict_caught 0, n 16, open.clear 0, open.ended_early 8, open.incomplete 8, open.refer 0, open.understanding_gap 0
- hi | problem: closed_r0.strict_caught 20, closed_r1.strict_caught 0, n 40, open.clear 0, open.ended_early 20, open.incomplete 19, open.refer 1, open.understanding_gap 0
- hi-en | knowledge_gap_only: closed_r0.strict_caught 24, closed_r1.strict_caught 0, n 24, open.clear 0, open.ended_early 10, open.incomplete 13, open.refer 1, open.understanding_gap 0
- hi-en | no_problem: closed_r0.strict_caught 0, closed_r1.strict_caught 0, n 16, open.clear 0, open.ended_early 6, open.incomplete 10, open.refer 0, open.understanding_gap 0
- hi-en | problem: closed_r0.strict_caught 20, closed_r1.strict_caught 0, n 40, open.clear 0, open.ended_early 22, open.incomplete 18, open.refer 0, open.understanding_gap 0
