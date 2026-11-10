# realvoice-v1: tables

Written by `uv run python eval/amounts_v2/analyze.py realvoice`. Parser: `samajh.amounts` at commit 59c12d9, exported outside the repository (files sha256 `ea36a203a54a85af`). Manifest sha256 `569274f8550feed17afcd28400b202d6a7d5e77b1e8eed3c40feebacb7ceab42`. Every reading is the parser's reading of that output; a refusal is no amount (ambiguous or none); a silent wrong amount is an amount that is not gold. Rates: count/n (percent, Wilson 95% interval).

Items in the manifest 125; clips with all four readings 248; items without a complete clip: rv-iv-027.


## Condition `native16k` (n = 124 clips)


### Outcomes per reading

| subset | reading | n | correct | refused | silent wrong |
| --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe | 124 | 121/124 (98%, 93-99) | 1/124 (1%, 0-4) | 2/124 (2%, 0-6) |
| all | v3.0 verbatim | 124 | 121/124 (98%, 93-99) | 1/124 (1%, 0-4) | 2/124 (2%, 0-6) |
| all | v2.5 transcribe | 124 | 115/124 (93%, 87-96) | 5/124 (4%, 2-9) | 4/124 (3%, 1-8) |
| all | v2.5 literal | 124 | 119/124 (96%, 91-98) | 3/124 (2%, 1-7) | 2/124 (2%, 0-6) |
| retail band | v3.0 transcribe | 86 | 84/86 (98%, 92-99) | 1/86 (1%, 0-6) | 1/86 (1%, 0-6) |
| retail band | v3.0 verbatim | 86 | 84/86 (98%, 92-99) | 1/86 (1%, 0-6) | 1/86 (1%, 0-6) |
| retail band | v2.5 transcribe | 86 | 80/86 (93%, 86-97) | 3/86 (3%, 1-10) | 3/86 (3%, 1-10) |
| retail band | v2.5 literal | 86 | 82/86 (95%, 89-98) | 3/86 (3%, 1-10) | 1/86 (1%, 0-6) |
| shape skipped | v3.0 transcribe | 4 | 3/4 (75%, 30-95) | 0/4 (0%, 0-49) | 1/4 (25%, 5-70) |
| shape skipped | v3.0 verbatim | 4 | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0/4 (0%, 0-49) |
| shape skipped | v2.5 transcribe | 4 | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0/4 (0%, 0-49) |
| shape skipped | v2.5 literal | 4 | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0/4 (0%, 0-49) |
| shape multi | v3.0 transcribe | 27 | 26/27 (96%, 82-99) | 1/27 (4%, 1-18) | 0/27 (0%, 0-12) |
| shape multi | v3.0 verbatim | 27 | 25/27 (93%, 77-98) | 1/27 (4%, 1-18) | 1/27 (4%, 1-18) |
| shape multi | v2.5 transcribe | 27 | 22/27 (81%, 63-92) | 3/27 (11%, 4-28) | 2/27 (7%, 2-23) |
| shape multi | v2.5 literal | 27 | 24/27 (89%, 72-96) | 2/27 (7%, 2-23) | 1/27 (4%, 1-18) |
| shape single | v3.0 transcribe | 93 | 92/93 (99%, 94-100) | 0/93 (0%, 0-4) | 1/93 (1%, 0-6) |
| shape single | v3.0 verbatim | 93 | 92/93 (99%, 94-100) | 0/93 (0%, 0-4) | 1/93 (1%, 0-6) |
| shape single | v2.5 transcribe | 93 | 89/93 (96%, 89-98) | 2/93 (2%, 1-8) | 2/93 (2%, 1-8) |
| shape single | v2.5 literal | 93 | 91/93 (98%, 92-99) | 1/93 (1%, 0-6) | 1/93 (1%, 0-6) |
| source indicvoices | v3.0 transcribe | 88 | 85/88 (97%, 90-99) | 1/88 (1%, 0-6) | 2/88 (2%, 1-8) |
| source indicvoices | v3.0 verbatim | 88 | 85/88 (97%, 90-99) | 1/88 (1%, 0-6) | 2/88 (2%, 1-8) |
| source indicvoices | v2.5 transcribe | 88 | 80/88 (91%, 83-95) | 4/88 (5%, 2-11) | 4/88 (5%, 2-11) |
| source indicvoices | v2.5 literal | 88 | 83/88 (94%, 87-98) | 3/88 (3%, 1-10) | 2/88 (2%, 1-8) |
| source kathbath | v3.0 transcribe | 36 | 36/36 (100%, 90-100) | 0/36 (0%, 0-10) | 0/36 (0%, 0-10) |
| source kathbath | v3.0 verbatim | 36 | 36/36 (100%, 90-100) | 0/36 (0%, 0-10) | 0/36 (0%, 0-10) |
| source kathbath | v2.5 transcribe | 36 | 35/36 (97%, 86-100) | 1/36 (3%, 0-14) | 0/36 (0%, 0-10) |
| source kathbath | v2.5 literal | 36 | 36/36 (100%, 90-100) | 0/36 (0%, 0-10) | 0/36 (0%, 0-10) |

### Paired tests

- silent wrong v3.0 transcribe only 1, v2.5 transcribe only 3; exact McNemar p = 0.62
- silent wrong v2.5 transcribe only 2, v2.5 literal only 0; exact McNemar p = 0.5
- Context: the naive digits rule on v3.0 transcribe text: silent wrong 6/124 (5%, 2-10)

### Mechanism: where the digits are wrong, what the words of the same clip say

| subset | digits wrong; words from | digits wrong | words right | words same wrong | words other wrong | words refused |
| --- | --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe wrong; v3.0 verbatim | 2 | 1/2 (50%, 9-91) | 0 | 1 | 0 |
| all | v2.5 transcribe wrong; v2.5 literal | 4 | 0/4 (0%, 0-49) | 2 | 0 | 2 |
| retail band | v3.0 transcribe wrong; v3.0 verbatim | 1 | 1/1 (100%, 21-100) | 0 | 0 | 0 |
| retail band | v2.5 transcribe wrong; v2.5 literal | 3 | 0/3 (0%, 0-56) | 1 | 0 | 2 |
| shape skipped | v3.0 transcribe wrong; v3.0 verbatim | 1 | 1/1 (100%, 21-100) | 0 | 0 | 0 |
| shape skipped | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |

### Acceptance schemes

| subset | scheme (accept when equal) | requests | accepted (coverage) | accepted wrong | P(correct \| accepted) |
| --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe alone | 1 | 123/124 (99%, 96-100) | 2 | 121/123 (98%, 94-100) |
| all | v2.5 transcribe alone | 1 | 119/124 (96%, 91-98) | 4 | 115/119 (97%, 92-99) |
| all | v2.5 literal alone | 1 | 121/124 (98%, 93-99) | 2 | 119/121 (98%, 94-100) |
| all | v2.5 transcribe = v2.5 literal (one request) | 1 | 117/124 (94%, 89-97) | 2 | 115/117 (98%, 94-100) |
| all | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 114/124 (92%, 86-96) | 0 | 114/114 (100%, 97-100) |
| all | v3.0 transcribe = v2.5 literal | 2 | 118/124 (95%, 90-98) | 0 | 118/118 (100%, 97-100) |
| all | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 114/124 (92%, 86-96) | 0 | 114/114 (100%, 97-100) |
| all | v3.0 transcribe = v3.0 verbatim | 2 | 120/124 (97%, 92-99) | 0 | 120/120 (100%, 97-100) |
| all | v3.0 verbatim = v2.5 literal | 2 | 120/124 (97%, 92-99) | 1 | 119/120 (99%, 95-100) |
| retail band | v3.0 transcribe alone | 1 | 85/86 (99%, 94-100) | 1 | 84/85 (99%, 94-100) |
| retail band | v2.5 transcribe alone | 1 | 83/86 (97%, 90-99) | 3 | 80/83 (96%, 90-99) |
| retail band | v2.5 literal alone | 1 | 83/86 (97%, 90-99) | 1 | 82/83 (99%, 93-100) |
| retail band | v2.5 transcribe = v2.5 literal (one request) | 1 | 81/86 (94%, 87-97) | 1 | 80/81 (99%, 93-100) |
| retail band | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 79/86 (92%, 84-96) | 0 | 79/79 (100%, 95-100) |
| retail band | v3.0 transcribe = v2.5 literal | 2 | 81/86 (94%, 87-97) | 0 | 81/81 (100%, 95-100) |
| retail band | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 79/86 (92%, 84-96) | 0 | 79/79 (100%, 95-100) |
| retail band | v3.0 transcribe = v3.0 verbatim | 2 | 83/86 (97%, 90-99) | 0 | 83/83 (100%, 96-100) |
| retail band | v3.0 verbatim = v2.5 literal | 2 | 83/86 (97%, 90-99) | 1 | 82/83 (99%, 93-100) |
| shape skipped | v3.0 transcribe alone | 1 | 4/4 (100%, 51-100) | 1 | 3/4 (75%, 30-95) |
| shape skipped | v2.5 transcribe alone | 1 | 4/4 (100%, 51-100) | 0 | 4/4 (100%, 51-100) |
| shape skipped | v2.5 literal alone | 1 | 4/4 (100%, 51-100) | 0 | 4/4 (100%, 51-100) |
| shape skipped | v2.5 transcribe = v2.5 literal (one request) | 1 | 4/4 (100%, 51-100) | 0 | 4/4 (100%, 51-100) |
| shape skipped | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 3/4 (75%, 30-95) | 0 | 3/3 (100%, 44-100) |
| shape skipped | v3.0 transcribe = v2.5 literal | 2 | 3/4 (75%, 30-95) | 0 | 3/3 (100%, 44-100) |
| shape skipped | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 3/4 (75%, 30-95) | 0 | 3/3 (100%, 44-100) |
| shape skipped | v3.0 transcribe = v3.0 verbatim | 2 | 3/4 (75%, 30-95) | 0 | 3/3 (100%, 44-100) |
| shape skipped | v3.0 verbatim = v2.5 literal | 2 | 4/4 (100%, 51-100) | 0 | 4/4 (100%, 51-100) |

### Clips a two-reading scheme does not accept

| pair | not accepted | two amounts | one refused | both refused | first right | second right | neither right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v3.0 transcribe vs v2.5 transcribe | 10 | 5 | 4 | 1 | 7 | 1 | 2 |
| v2.5 transcribe vs v2.5 literal | 7 | 0 | 6 | 1 | 0 | 4 | 3 |
| v3.0 transcribe vs v2.5 literal | 6 | 3 | 2 | 1 | 3 | 1 | 2 |

### Clips where any reading is not gold

| item | stratum | shape/source | gold | v3.0 transcribe | v3.0 verbatim | v2.5 transcribe | v2.5 literal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rv-iv-012 | multi | indicvoices | 1900 | refused | refused | refused | refused |
| rv-iv-018 | skipped | indicvoices | 5006 | **5600** | ok | ok | ok |
| rv-iv-029 | single | indicvoices | 500 | ok | ok | **100** | refused |
| rv-iv-032 | single | indicvoices | 50 | ok | ok | refused | ok |
| rv-iv-051 | multi | indicvoices | 350 | ok | ok | refused | ok |
| rv-iv-059 | single | indicvoices | 8 | **100** | **500** | **800** | **800** |
| rv-iv-061 | multi | indicvoices | 2200 | ok | ok | **100** | refused |
| rv-iv-070 | multi | indicvoices | 3600 | ok | **36** | **36** | **36** |
| rv-iv-082 | single | indicvoices | 6000 | ok | ok | refused | ok |
| rv-kb-003 | multi | kathbath | 3500 | ok | ok | refused | ok |

## Condition `phone` (n = 124 clips)


### Outcomes per reading

| subset | reading | n | correct | refused | silent wrong |
| --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe | 124 | 120/124 (97%, 92-99) | 1/124 (1%, 0-4) | 3/124 (2%, 1-7) |
| all | v3.0 verbatim | 124 | 121/124 (98%, 93-99) | 1/124 (1%, 0-4) | 2/124 (2%, 0-6) |
| all | v2.5 transcribe | 124 | 115/124 (93%, 87-96) | 5/124 (4%, 2-9) | 4/124 (3%, 1-8) |
| all | v2.5 literal | 124 | 119/124 (96%, 91-98) | 3/124 (2%, 1-7) | 2/124 (2%, 0-6) |
| retail band | v3.0 transcribe | 86 | 83/86 (97%, 90-99) | 1/86 (1%, 0-6) | 2/86 (2%, 1-8) |
| retail band | v3.0 verbatim | 86 | 84/86 (98%, 92-99) | 1/86 (1%, 0-6) | 1/86 (1%, 0-6) |
| retail band | v2.5 transcribe | 86 | 80/86 (93%, 86-97) | 3/86 (3%, 1-10) | 3/86 (3%, 1-10) |
| retail band | v2.5 literal | 86 | 82/86 (95%, 89-98) | 3/86 (3%, 1-10) | 1/86 (1%, 0-6) |
| shape skipped | v3.0 transcribe | 4 | 3/4 (75%, 30-95) | 0/4 (0%, 0-49) | 1/4 (25%, 5-70) |
| shape skipped | v3.0 verbatim | 4 | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0/4 (0%, 0-49) |
| shape skipped | v2.5 transcribe | 4 | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0/4 (0%, 0-49) |
| shape skipped | v2.5 literal | 4 | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0/4 (0%, 0-49) |
| shape multi | v3.0 transcribe | 27 | 26/27 (96%, 82-99) | 1/27 (4%, 1-18) | 0/27 (0%, 0-12) |
| shape multi | v3.0 verbatim | 27 | 26/27 (96%, 82-99) | 1/27 (4%, 1-18) | 0/27 (0%, 0-12) |
| shape multi | v2.5 transcribe | 27 | 22/27 (81%, 63-92) | 3/27 (11%, 4-28) | 2/27 (7%, 2-23) |
| shape multi | v2.5 literal | 27 | 24/27 (89%, 72-96) | 2/27 (7%, 2-23) | 1/27 (4%, 1-18) |
| shape single | v3.0 transcribe | 93 | 91/93 (98%, 92-99) | 0/93 (0%, 0-4) | 2/93 (2%, 1-8) |
| shape single | v3.0 verbatim | 93 | 91/93 (98%, 92-99) | 0/93 (0%, 0-4) | 2/93 (2%, 1-8) |
| shape single | v2.5 transcribe | 93 | 89/93 (96%, 89-98) | 2/93 (2%, 1-8) | 2/93 (2%, 1-8) |
| shape single | v2.5 literal | 93 | 91/93 (98%, 92-99) | 1/93 (1%, 0-6) | 1/93 (1%, 0-6) |
| source indicvoices | v3.0 transcribe | 88 | 84/88 (95%, 89-98) | 1/88 (1%, 0-6) | 3/88 (3%, 1-10) |
| source indicvoices | v3.0 verbatim | 88 | 85/88 (97%, 90-99) | 1/88 (1%, 0-6) | 2/88 (2%, 1-8) |
| source indicvoices | v2.5 transcribe | 88 | 80/88 (91%, 83-95) | 4/88 (5%, 2-11) | 4/88 (5%, 2-11) |
| source indicvoices | v2.5 literal | 88 | 83/88 (94%, 87-98) | 3/88 (3%, 1-10) | 2/88 (2%, 1-8) |
| source kathbath | v3.0 transcribe | 36 | 36/36 (100%, 90-100) | 0/36 (0%, 0-10) | 0/36 (0%, 0-10) |
| source kathbath | v3.0 verbatim | 36 | 36/36 (100%, 90-100) | 0/36 (0%, 0-10) | 0/36 (0%, 0-10) |
| source kathbath | v2.5 transcribe | 36 | 35/36 (97%, 86-100) | 1/36 (3%, 0-14) | 0/36 (0%, 0-10) |
| source kathbath | v2.5 literal | 36 | 36/36 (100%, 90-100) | 0/36 (0%, 0-10) | 0/36 (0%, 0-10) |

### Paired tests

- silent wrong v3.0 transcribe only 2, v2.5 transcribe only 3; exact McNemar p = 1
- silent wrong v2.5 transcribe only 2, v2.5 literal only 0; exact McNemar p = 0.5
- Context: the naive digits rule on v3.0 transcribe text: silent wrong 7/124 (6%, 3-11)

### Mechanism: where the digits are wrong, what the words of the same clip say

| subset | digits wrong; words from | digits wrong | words right | words same wrong | words other wrong | words refused |
| --- | --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe wrong; v3.0 verbatim | 3 | 1/3 (33%, 6-79) | 2 | 0 | 0 |
| all | v2.5 transcribe wrong; v2.5 literal | 4 | 0/4 (0%, 0-49) | 2 | 0 | 2 |
| retail band | v3.0 transcribe wrong; v3.0 verbatim | 2 | 1/2 (50%, 9-91) | 1 | 0 | 0 |
| retail band | v2.5 transcribe wrong; v2.5 literal | 3 | 0/3 (0%, 0-56) | 1 | 0 | 2 |
| shape skipped | v3.0 transcribe wrong; v3.0 verbatim | 1 | 1/1 (100%, 21-100) | 0 | 0 | 0 |
| shape skipped | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |

### Acceptance schemes

| subset | scheme (accept when equal) | requests | accepted (coverage) | accepted wrong | P(correct \| accepted) |
| --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe alone | 1 | 123/124 (99%, 96-100) | 3 | 120/123 (98%, 93-99) |
| all | v2.5 transcribe alone | 1 | 119/124 (96%, 91-98) | 4 | 115/119 (97%, 92-99) |
| all | v2.5 literal alone | 1 | 121/124 (98%, 93-99) | 2 | 119/121 (98%, 94-100) |
| all | v2.5 transcribe = v2.5 literal (one request) | 1 | 117/124 (94%, 89-97) | 2 | 115/117 (98%, 94-100) |
| all | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 113/124 (91%, 85-95) | 0 | 113/113 (100%, 97-100) |
| all | v3.0 transcribe = v2.5 literal | 2 | 117/124 (94%, 89-97) | 0 | 117/117 (100%, 97-100) |
| all | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 113/124 (91%, 85-95) | 0 | 113/113 (100%, 97-100) |
| all | v3.0 transcribe = v3.0 verbatim | 2 | 122/124 (98%, 94-100) | 2 | 120/122 (98%, 94-100) |
| all | v3.0 verbatim = v2.5 literal | 2 | 118/124 (95%, 90-98) | 0 | 118/118 (100%, 97-100) |
| retail band | v3.0 transcribe alone | 1 | 85/86 (99%, 94-100) | 2 | 83/85 (98%, 92-99) |
| retail band | v2.5 transcribe alone | 1 | 83/86 (97%, 90-99) | 3 | 80/83 (96%, 90-99) |
| retail band | v2.5 literal alone | 1 | 83/86 (97%, 90-99) | 1 | 82/83 (99%, 93-100) |
| retail band | v2.5 transcribe = v2.5 literal (one request) | 1 | 81/86 (94%, 87-97) | 1 | 80/81 (99%, 93-100) |
| retail band | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 78/86 (91%, 83-95) | 0 | 78/78 (100%, 95-100) |
| retail band | v3.0 transcribe = v2.5 literal | 2 | 80/86 (93%, 86-97) | 0 | 80/80 (100%, 95-100) |
| retail band | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 78/86 (91%, 83-95) | 0 | 78/78 (100%, 95-100) |
| retail band | v3.0 transcribe = v3.0 verbatim | 2 | 84/86 (98%, 92-99) | 1 | 83/84 (99%, 94-100) |
| retail band | v3.0 verbatim = v2.5 literal | 2 | 81/86 (94%, 87-97) | 0 | 81/81 (100%, 95-100) |
| shape skipped | v3.0 transcribe alone | 1 | 4/4 (100%, 51-100) | 1 | 3/4 (75%, 30-95) |
| shape skipped | v2.5 transcribe alone | 1 | 4/4 (100%, 51-100) | 0 | 4/4 (100%, 51-100) |
| shape skipped | v2.5 literal alone | 1 | 4/4 (100%, 51-100) | 0 | 4/4 (100%, 51-100) |
| shape skipped | v2.5 transcribe = v2.5 literal (one request) | 1 | 4/4 (100%, 51-100) | 0 | 4/4 (100%, 51-100) |
| shape skipped | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 3/4 (75%, 30-95) | 0 | 3/3 (100%, 44-100) |
| shape skipped | v3.0 transcribe = v2.5 literal | 2 | 3/4 (75%, 30-95) | 0 | 3/3 (100%, 44-100) |
| shape skipped | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 3/4 (75%, 30-95) | 0 | 3/3 (100%, 44-100) |
| shape skipped | v3.0 transcribe = v3.0 verbatim | 2 | 3/4 (75%, 30-95) | 0 | 3/3 (100%, 44-100) |
| shape skipped | v3.0 verbatim = v2.5 literal | 2 | 4/4 (100%, 51-100) | 0 | 4/4 (100%, 51-100) |

### Clips a two-reading scheme does not accept

| pair | not accepted | two amounts | one refused | both refused | first right | second right | neither right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v3.0 transcribe vs v2.5 transcribe | 11 | 6 | 4 | 1 | 7 | 2 | 2 |
| v2.5 transcribe vs v2.5 literal | 7 | 0 | 6 | 1 | 0 | 4 | 3 |
| v3.0 transcribe vs v2.5 literal | 7 | 4 | 2 | 1 | 3 | 2 | 2 |

### Clips where any reading is not gold

| item | stratum | shape/source | gold | v3.0 transcribe | v3.0 verbatim | v2.5 transcribe | v2.5 literal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rv-iv-006 | single | indicvoices | 60000 | **4000** | **4000** | ok | ok |
| rv-iv-012 | multi | indicvoices | 1900 | refused | refused | refused | refused |
| rv-iv-018 | skipped | indicvoices | 5006 | **5600** | ok | ok | ok |
| rv-iv-029 | single | indicvoices | 500 | ok | ok | **100** | refused |
| rv-iv-032 | single | indicvoices | 50 | ok | ok | refused | ok |
| rv-iv-051 | multi | indicvoices | 350 | ok | ok | refused | ok |
| rv-iv-059 | single | indicvoices | 8 | **100** | **100** | **800** | **800** |
| rv-iv-061 | multi | indicvoices | 2200 | ok | ok | **100** | refused |
| rv-iv-070 | multi | indicvoices | 3600 | ok | ok | **36** | **36** |
| rv-iv-082 | single | indicvoices | 6000 | ok | ok | refused | ok |
| rv-kb-003 | multi | kathbath | 3500 | ok | ok | refused | ok |

## Requests: latency and estimated cost

| request | rows | live calls | median s | p90 s | est. credits | audio s |
| --- | --- | --- | --- | --- | --- | --- |
| v3.0 transcribe item | 248 | 248 | 0.41 | 0.67 | 17.80 | 1780 |
| v3.0 verbatim item | 248 | 248 | 0.41 | 0.73 | 17.80 | 1780 |
| v2.5 transcribe item | 248 | 248 | 0.39 | 0.65 | 17.80 | 1780 |

Latency is wall time per live request through the client lock (cache hits left out). Credits are the client's estimate (0.010 per audio second for both models), not a dashboard reading.

