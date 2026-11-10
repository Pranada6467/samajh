# amounts-v2: tables

Written by `uv run python eval/amounts_v2/analyze.py tts`. Parser: `samajh.amounts` at commit 59c12d9, exported outside the repository (files sha256 `ea36a203a54a85af`). Manifest sha256 `1beea924ba961370950d09c9cfbbdb28dd35e8878861b8b2d388f6acbcd11fe1`. Every reading is the parser's reading of that output; a refusal is no amount (ambiguous or none); a silent wrong amount is an amount that is not gold. Rates: count/n (percent, Wilson 95% interval).

Items in the manifest 280; clips with all four readings 560; items without a complete clip: none.


## Condition `clean16k` (n = 280 clips)


### Outcomes per reading

| subset | reading | n | correct | refused | silent wrong |
| --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe | 280 | 233/280 (83%, 78-87) | 8/280 (3%, 1-6) | 39/280 (14%, 10-18) |
| all | v3.0 verbatim | 280 | 275/280 (98%, 96-99) | 4/280 (1%, 1-4) | 1/280 (0%, 0-2) |
| all | v2.5 transcribe | 280 | 266/280 (95%, 92-97) | 14/280 (5%, 3-8) | 0/280 (0%, 0-1) |
| all | v2.5 literal | 280 | 279/280 (100%, 98-100) | 0/280 (0%, 0-1) | 1/280 (0%, 0-2) |
| retail band | v3.0 transcribe | 209 | 179/209 (86%, 80-90) | 7/209 (3%, 2-7) | 23/209 (11%, 7-16) |
| retail band | v3.0 verbatim | 209 | 205/209 (98%, 95-99) | 3/209 (1%, 0-4) | 1/209 (0%, 0-3) |
| retail band | v2.5 transcribe | 209 | 198/209 (95%, 91-97) | 11/209 (5%, 3-9) | 0/209 (0%, 0-2) |
| retail band | v2.5 literal | 209 | 208/209 (100%, 97-100) | 0/209 (0%, 0-2) | 1/209 (0%, 0-3) |
| skipped | v3.0 transcribe | 68 | 21/68 (31%, 21-43) | 8/68 (12%, 6-22) | 39/68 (57%, 46-68) |
| skipped | v3.0 verbatim | 68 | 67/68 (99%, 92-100) | 0/68 (0%, 0-5) | 1/68 (1%, 0-8) |
| skipped | v2.5 transcribe | 68 | 65/68 (96%, 88-98) | 3/68 (4%, 2-12) | 0/68 (0%, 0-5) |
| skipped | v2.5 literal | 68 | 67/68 (99%, 92-100) | 0/68 (0%, 0-5) | 1/68 (1%, 0-8) |
| control | v3.0 transcribe | 68 | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0/68 (0%, 0-5) |
| control | v3.0 verbatim | 68 | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0/68 (0%, 0-5) |
| control | v2.5 transcribe | 68 | 65/68 (96%, 88-98) | 3/68 (4%, 2-12) | 0/68 (0%, 0-5) |
| control | v2.5 literal | 68 | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0/68 (0%, 0-5) |
| general | v3.0 transcribe | 96 | 96/96 (100%, 96-100) | 0/96 (0%, 0-4) | 0/96 (0%, 0-4) |
| general | v3.0 verbatim | 96 | 96/96 (100%, 96-100) | 0/96 (0%, 0-4) | 0/96 (0%, 0-4) |
| general | v2.5 transcribe | 96 | 91/96 (95%, 88-98) | 5/96 (5%, 2-12) | 0/96 (0%, 0-4) |
| general | v2.5 literal | 96 | 96/96 (100%, 96-100) | 0/96 (0%, 0-4) | 0/96 (0%, 0-4) |
| fraction | v3.0 transcribe | 32 | 32/32 (100%, 89-100) | 0/32 (0%, 0-11) | 0/32 (0%, 0-11) |
| fraction | v3.0 verbatim | 32 | 28/32 (88%, 72-95) | 4/32 (12%, 5-28) | 0/32 (0%, 0-11) |
| fraction | v2.5 transcribe | 32 | 29/32 (91%, 76-97) | 3/32 (9%, 3-24) | 0/32 (0%, 0-11) |
| fraction | v2.5 literal | 32 | 32/32 (100%, 89-100) | 0/32 (0%, 0-11) | 0/32 (0%, 0-11) |
| large | v3.0 transcribe | 16 | 16/16 (100%, 81-100) | 0/16 (0%, 0-19) | 0/16 (0%, 0-19) |
| large | v3.0 verbatim | 16 | 16/16 (100%, 81-100) | 0/16 (0%, 0-19) | 0/16 (0%, 0-19) |
| large | v2.5 transcribe | 16 | 16/16 (100%, 81-100) | 0/16 (0%, 0-19) | 0/16 (0%, 0-19) |
| large | v2.5 literal | 16 | 16/16 (100%, 81-100) | 0/16 (0%, 0-19) | 0/16 (0%, 0-19) |
| language hi | v3.0 transcribe | 140 | 120/140 (86%, 79-91) | 5/140 (4%, 2-8) | 15/140 (11%, 7-17) |
| language hi | v3.0 verbatim | 140 | 139/140 (99%, 96-100) | 0/140 (0%, 0-3) | 1/140 (1%, 0-4) |
| language hi | v2.5 transcribe | 140 | 139/140 (99%, 96-100) | 1/140 (1%, 0-4) | 0/140 (0%, 0-3) |
| language hi | v2.5 literal | 140 | 139/140 (99%, 96-100) | 0/140 (0%, 0-3) | 1/140 (1%, 0-4) |
| language hi-en | v3.0 transcribe | 140 | 113/140 (81%, 73-86) | 3/140 (2%, 1-6) | 24/140 (17%, 12-24) |
| language hi-en | v3.0 verbatim | 140 | 136/140 (97%, 93-99) | 4/140 (3%, 1-7) | 0/140 (0%, 0-3) |
| language hi-en | v2.5 transcribe | 140 | 127/140 (91%, 85-94) | 13/140 (9%, 6-15) | 0/140 (0%, 0-3) |
| language hi-en | v2.5 literal | 140 | 140/140 (100%, 97-100) | 0/140 (0%, 0-3) | 0/140 (0%, 0-3) |

### Paired tests

- silent wrong v3.0 transcribe only 39, v2.5 transcribe only 0; exact McNemar p = 3.6e-12
- silent wrong v2.5 transcribe only 0, v2.5 literal only 1; exact McNemar p = 1
- v3.0 transcribe: 68 pairs; silent wrong on the skipped item only 39, on the control only 0, on both 0; exact McNemar p = 3.6e-12
- v2.5 transcribe: 68 pairs; silent wrong on the skipped item only 0, on the control only 0, on both 0; exact McNemar p = 1
- Context: the naive digits rule on v3.0 transcribe text: silent wrong 48/280 (17%, 13-22)

### Mechanism: where the digits are wrong, what the words of the same clip say

| subset | digits wrong; words from | digits wrong | words right | words same wrong | words other wrong | words refused |
| --- | --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe wrong; v3.0 verbatim | 39 | 39/39 (100%, 91-100) | 0 | 0 | 0 |
| all | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |
| retail band | v3.0 transcribe wrong; v3.0 verbatim | 23 | 23/23 (100%, 86-100) | 0 | 0 | 0 |
| retail band | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |
| skipped | v3.0 transcribe wrong; v3.0 verbatim | 39 | 39/39 (100%, 91-100) | 0 | 0 | 0 |
| skipped | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |
| control | v3.0 transcribe wrong; v3.0 verbatim | 0 | 0/0 | 0 | 0 | 0 |
| control | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |

### Acceptance schemes

| subset | scheme (accept when equal) | requests | accepted (coverage) | accepted wrong | P(correct \| accepted) |
| --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe alone | 1 | 272/280 (97%, 94-99) | 39 | 233/272 (86%, 81-89) |
| all | v2.5 transcribe alone | 1 | 266/280 (95%, 92-97) | 0 | 266/266 (100%, 99-100) |
| all | v2.5 literal alone | 1 | 280/280 (100%, 99-100) | 1 | 279/280 (100%, 98-100) |
| all | v2.5 transcribe = v2.5 literal (one request) | 1 | 265/280 (95%, 91-97) | 0 | 265/265 (100%, 99-100) |
| all | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 222/280 (79%, 74-84) | 0 | 222/222 (100%, 98-100) |
| all | v3.0 transcribe = v2.5 literal | 2 | 232/280 (83%, 78-87) | 0 | 232/232 (100%, 98-100) |
| all | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 221/280 (79%, 74-83) | 0 | 221/221 (100%, 98-100) |
| all | v3.0 transcribe = v3.0 verbatim | 2 | 228/280 (81%, 76-86) | 0 | 228/228 (100%, 98-100) |
| all | v3.0 verbatim = v2.5 literal | 2 | 276/280 (99%, 96-99) | 1 | 275/276 (100%, 98-100) |
| retail band | v3.0 transcribe alone | 1 | 202/209 (97%, 93-98) | 23 | 179/202 (89%, 83-92) |
| retail band | v2.5 transcribe alone | 1 | 198/209 (95%, 91-97) | 0 | 198/198 (100%, 98-100) |
| retail band | v2.5 literal alone | 1 | 209/209 (100%, 98-100) | 1 | 208/209 (100%, 97-100) |
| retail band | v2.5 transcribe = v2.5 literal (one request) | 1 | 197/209 (94%, 90-97) | 0 | 197/197 (100%, 98-100) |
| retail band | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 170/209 (81%, 76-86) | 0 | 170/170 (100%, 98-100) |
| retail band | v3.0 transcribe = v2.5 literal | 2 | 178/209 (85%, 80-89) | 0 | 178/178 (100%, 98-100) |
| retail band | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 169/209 (81%, 75-86) | 0 | 169/169 (100%, 98-100) |
| retail band | v3.0 transcribe = v3.0 verbatim | 2 | 175/209 (84%, 78-88) | 0 | 175/175 (100%, 98-100) |
| retail band | v3.0 verbatim = v2.5 literal | 2 | 206/209 (99%, 96-100) | 1 | 205/206 (100%, 97-100) |
| skipped | v3.0 transcribe alone | 1 | 60/68 (88%, 78-94) | 39 | 21/60 (35%, 24-48) |
| skipped | v2.5 transcribe alone | 1 | 65/68 (96%, 88-98) | 0 | 65/65 (100%, 94-100) |
| skipped | v2.5 literal alone | 1 | 68/68 (100%, 95-100) | 1 | 67/68 (99%, 92-100) |
| skipped | v2.5 transcribe = v2.5 literal (one request) | 1 | 64/68 (94%, 86-98) | 0 | 64/64 (100%, 94-100) |
| skipped | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 21/68 (31%, 21-43) | 0 | 21/21 (100%, 85-100) |
| skipped | v3.0 transcribe = v2.5 literal | 2 | 20/68 (29%, 20-41) | 0 | 20/20 (100%, 84-100) |
| skipped | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 20/68 (29%, 20-41) | 0 | 20/20 (100%, 84-100) |
| skipped | v3.0 transcribe = v3.0 verbatim | 2 | 20/68 (29%, 20-41) | 0 | 20/20 (100%, 84-100) |
| skipped | v3.0 verbatim = v2.5 literal | 2 | 68/68 (100%, 95-100) | 1 | 67/68 (99%, 92-100) |
| control | v3.0 transcribe alone | 1 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |
| control | v2.5 transcribe alone | 1 | 65/68 (96%, 88-98) | 0 | 65/65 (100%, 94-100) |
| control | v2.5 literal alone | 1 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |
| control | v2.5 transcribe = v2.5 literal (one request) | 1 | 65/68 (96%, 88-98) | 0 | 65/65 (100%, 94-100) |
| control | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 65/68 (96%, 88-98) | 0 | 65/65 (100%, 94-100) |
| control | v3.0 transcribe = v2.5 literal | 2 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |
| control | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 65/68 (96%, 88-98) | 0 | 65/65 (100%, 94-100) |
| control | v3.0 transcribe = v3.0 verbatim | 2 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |
| control | v3.0 verbatim = v2.5 literal | 2 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |

### Clips a two-reading scheme does not accept

| pair | not accepted | two amounts | one refused | both refused | first right | second right | neither right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v3.0 transcribe vs v2.5 transcribe | 58 | 37 | 20 | 1 | 11 | 44 | 3 |
| v2.5 transcribe vs v2.5 literal | 15 | 1 | 14 | 0 | 1 | 14 | 0 |
| v3.0 transcribe vs v2.5 literal | 48 | 40 | 8 | 0 | 1 | 47 | 0 |

### Clips where any reading is not gold

| item | stratum | shape/source | gold | v3.0 transcribe | v3.0 verbatim | v2.5 transcribe | v2.5 literal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| amt2-hi-en-control-011 | control | lakh_hundreds | 202000 | ok | ok | refused | ok |
| amt2-hi-en-control-018 | control | lakh_hundreds | 903000 | ok | ok | refused | ok |
| amt2-hi-en-control-020 | control | thousand_units | 99100 | ok | ok | refused | ok |
| amt2-hi-en-fraction-001 | fraction | and_a_half | 150000 | ok | refused | ok | ok |
| amt2-hi-en-fraction-004 | fraction | and_a_half | 15000000 | ok | refused | ok | ok |
| amt2-hi-en-fraction-008 | fraction | point | 12500000 | ok | ok | refused | ok |
| amt2-hi-en-fraction-009 | fraction | dedh | 1500 | ok | refused | ok | ok |
| amt2-hi-en-fraction-013 | fraction | saadhe | 9500 | ok | ok | refused | ok |
| amt2-hi-en-fraction-014 | fraction | saadhe | 8500 | ok | refused | refused | ok |
| amt2-hi-en-general-015 | general | thousand_hundred | 90100 | ok | ok | refused | ok |
| amt2-hi-en-general-025 | general | thousand_hundred_rest | 90195 | ok | ok | refused | ok |
| amt2-hi-en-general-027 | general | thousand_hundred_rest | 13290 | ok | ok | refused | ok |
| amt2-hi-en-general-031 | general | thousand_hundred_rest | 99345 | ok | ok | refused | ok |
| amt2-hi-en-general-047 | general | lakh_thousand_hundred | 499800 | ok | ok | refused | ok |
| amt2-hi-en-skipped-001 | skipped | lakh_units | 400011 | **411000** | ok | ok | ok |
| amt2-hi-en-skipped-002 | skipped | lakh_units | 200086 | **286000** | ok | ok | ok |
| amt2-hi-en-skipped-003 | skipped | lakh_units | 200014 | **214000** | ok | ok | ok |
| amt2-hi-en-skipped-004 | skipped | lakh_units | 100006 | **106000** | ok | ok | ok |
| amt2-hi-en-skipped-005 | skipped | lakh_units | 100049 | **149000** | ok | ok | ok |
| amt2-hi-en-skipped-006 | skipped | lakh_units | 200079 | **279000** | ok | ok | ok |
| amt2-hi-en-skipped-007 | skipped | lakh_units | 100016 | **116000** | ok | ok | ok |
| amt2-hi-en-skipped-008 | skipped | lakh_units | 1200080 | **1280000** | ok | ok | ok |
| amt2-hi-en-skipped-009 | skipped | lakh_units | 900020 | **920000** | ok | ok | ok |
| amt2-hi-en-skipped-012 | skipped | lakh_hundreds | 400900 | **409000** | ok | ok | ok |
| amt2-hi-en-skipped-013 | skipped | lakh_hundreds | 100300 | **1300** | ok | ok | ok |
| amt2-hi-en-skipped-014 | skipped | lakh_hundreds | 300500 | **3500** | ok | ok | ok |
| amt2-hi-en-skipped-015 | skipped | lakh_hundreds | 200500 | **205000** | ok | ok | ok |
| amt2-hi-en-skipped-016 | skipped | lakh_hundreds | 300800 | **308000** | ok | ok | ok |
| amt2-hi-en-skipped-017 | skipped | lakh_hundreds | 6000900 | refused | ok | ok | ok |
| amt2-hi-en-skipped-018 | skipped | lakh_hundreds | 900300 | **903000** | ok | ok | ok |
| amt2-hi-en-skipped-020 | skipped | thousand_units | 99073 | refused | ok | refused | ok |
| amt2-hi-en-skipped-022 | skipped | thousand_units | 14060 | **14600** | ok | ok | ok |
| amt2-hi-en-skipped-023 | skipped | thousand_units | 30003 | **30000** | ok | ok | ok |
| amt2-hi-en-skipped-025 | skipped | thousand_units | 79006 | refused | ok | ok | ok |
| amt2-hi-en-skipped-027 | skipped | thousand_units | 45008 | **45800** | ok | ok | ok |
| amt2-hi-en-skipped-029 | skipped | crore_thousands | 20070000 | **270000** | ok | ok | ok |
| amt2-hi-en-skipped-030 | skipped | crore_thousands | 40030000 | **430000** | ok | refused | ok |
| amt2-hi-en-skipped-031 | skipped | crore_thousands | 150007000 | **1507000** | ok | ok | ok |
| amt2-hi-en-skipped-032 | skipped | crore_thousands | 50012000 | **512000** | ok | ok | ok |
| amt2-hi-en-skipped-033 | skipped | crore_thousands | 80007000 | **807000** | ok | ok | ok |
| amt2-hi-en-skipped-034 | skipped | crore_thousands | 80009000 | **809000** | ok | ok | ok |
| amt2-hi-skipped-001 | skipped | lakh_units | 300040 | **340000** | ok | ok | ok |
| amt2-hi-skipped-002 | skipped | lakh_units | 100014 | **114000** | ok | ok | ok |
| amt2-hi-skipped-003 | skipped | lakh_units | 400008 | **408000** | ok | ok | ok |
| amt2-hi-skipped-004 | skipped | lakh_units | 200022 | **222000** | ok | ok | ok |
| amt2-hi-skipped-005 | skipped | lakh_units | 100001 | ok | **100000** | ok | **100000** |
| amt2-hi-skipped-006 | skipped | lakh_units | 300095 | **395000** | ok | refused | ok |
| amt2-hi-skipped-007 | skipped | lakh_units | 200005 | **200000** | ok | ok | ok |
| amt2-hi-skipped-009 | skipped | lakh_units | 900005 | **900000** | ok | ok | ok |
| amt2-hi-skipped-011 | skipped | lakh_hundreds | 400700 | refused | ok | ok | ok |
| amt2-hi-skipped-016 | skipped | lakh_hundreds | 200800 | **2800** | ok | ok | ok |
| amt2-hi-skipped-019 | skipped | thousand_units | 56082 | refused | ok | ok | ok |
| amt2-hi-skipped-022 | skipped | thousand_units | 12081 | refused | ok | ok | ok |
| amt2-hi-skipped-023 | skipped | thousand_units | 13093 | refused | ok | ok | ok |
| amt2-hi-skipped-027 | skipped | thousand_units | 8006 | refused | ok | ok | ok |
| amt2-hi-skipped-028 | skipped | thousand_units | 2012 | **2000** | ok | ok | ok |
| amt2-hi-skipped-029 | skipped | crore_thousands | 50026000 | **526000** | ok | ok | ok |
| amt2-hi-skipped-030 | skipped | crore_thousands | 10002000 | **102000** | ok | ok | ok |
| amt2-hi-skipped-031 | skipped | crore_thousands | 20034000 | **234000** | ok | ok | ok |
| amt2-hi-skipped-032 | skipped | crore_thousands | 70011000 | **711000** | ok | ok | ok |
| amt2-hi-skipped-033 | skipped | crore_thousands | 10066000 | **166000** | ok | ok | ok |
| amt2-hi-skipped-034 | skipped | crore_thousands | 10068000 | **168000** | ok | ok | ok |

## Condition `phone` (n = 280 clips)


### Outcomes per reading

| subset | reading | n | correct | refused | silent wrong |
| --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe | 280 | 235/280 (84%, 79-88) | 5/280 (2%, 1-4) | 40/280 (14%, 11-19) |
| all | v3.0 verbatim | 280 | 275/280 (98%, 96-99) | 4/280 (1%, 1-4) | 1/280 (0%, 0-2) |
| all | v2.5 transcribe | 280 | 268/280 (96%, 93-98) | 12/280 (4%, 2-7) | 0/280 (0%, 0-1) |
| all | v2.5 literal | 280 | 279/280 (100%, 98-100) | 0/280 (0%, 0-1) | 1/280 (0%, 0-2) |
| retail band | v3.0 transcribe | 209 | 182/209 (87%, 82-91) | 4/209 (2%, 1-5) | 23/209 (11%, 7-16) |
| retail band | v3.0 verbatim | 209 | 205/209 (98%, 95-99) | 3/209 (1%, 0-4) | 1/209 (0%, 0-3) |
| retail band | v2.5 transcribe | 209 | 198/209 (95%, 91-97) | 11/209 (5%, 3-9) | 0/209 (0%, 0-2) |
| retail band | v2.5 literal | 209 | 208/209 (100%, 97-100) | 0/209 (0%, 0-2) | 1/209 (0%, 0-3) |
| skipped | v3.0 transcribe | 68 | 23/68 (34%, 24-46) | 5/68 (7%, 3-16) | 40/68 (59%, 47-70) |
| skipped | v3.0 verbatim | 68 | 67/68 (99%, 92-100) | 0/68 (0%, 0-5) | 1/68 (1%, 0-8) |
| skipped | v2.5 transcribe | 68 | 66/68 (97%, 90-99) | 2/68 (3%, 1-10) | 0/68 (0%, 0-5) |
| skipped | v2.5 literal | 68 | 67/68 (99%, 92-100) | 0/68 (0%, 0-5) | 1/68 (1%, 0-8) |
| control | v3.0 transcribe | 68 | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0/68 (0%, 0-5) |
| control | v3.0 verbatim | 68 | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0/68 (0%, 0-5) |
| control | v2.5 transcribe | 68 | 66/68 (97%, 90-99) | 2/68 (3%, 1-10) | 0/68 (0%, 0-5) |
| control | v2.5 literal | 68 | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0/68 (0%, 0-5) |
| general | v3.0 transcribe | 96 | 96/96 (100%, 96-100) | 0/96 (0%, 0-4) | 0/96 (0%, 0-4) |
| general | v3.0 verbatim | 96 | 96/96 (100%, 96-100) | 0/96 (0%, 0-4) | 0/96 (0%, 0-4) |
| general | v2.5 transcribe | 96 | 91/96 (95%, 88-98) | 5/96 (5%, 2-12) | 0/96 (0%, 0-4) |
| general | v2.5 literal | 96 | 96/96 (100%, 96-100) | 0/96 (0%, 0-4) | 0/96 (0%, 0-4) |
| fraction | v3.0 transcribe | 32 | 32/32 (100%, 89-100) | 0/32 (0%, 0-11) | 0/32 (0%, 0-11) |
| fraction | v3.0 verbatim | 32 | 28/32 (88%, 72-95) | 4/32 (12%, 5-28) | 0/32 (0%, 0-11) |
| fraction | v2.5 transcribe | 32 | 29/32 (91%, 76-97) | 3/32 (9%, 3-24) | 0/32 (0%, 0-11) |
| fraction | v2.5 literal | 32 | 32/32 (100%, 89-100) | 0/32 (0%, 0-11) | 0/32 (0%, 0-11) |
| large | v3.0 transcribe | 16 | 16/16 (100%, 81-100) | 0/16 (0%, 0-19) | 0/16 (0%, 0-19) |
| large | v3.0 verbatim | 16 | 16/16 (100%, 81-100) | 0/16 (0%, 0-19) | 0/16 (0%, 0-19) |
| large | v2.5 transcribe | 16 | 16/16 (100%, 81-100) | 0/16 (0%, 0-19) | 0/16 (0%, 0-19) |
| large | v2.5 literal | 16 | 16/16 (100%, 81-100) | 0/16 (0%, 0-19) | 0/16 (0%, 0-19) |
| language hi | v3.0 transcribe | 140 | 121/140 (86%, 80-91) | 3/140 (2%, 1-6) | 16/140 (11%, 7-18) |
| language hi | v3.0 verbatim | 140 | 139/140 (99%, 96-100) | 0/140 (0%, 0-3) | 1/140 (1%, 0-4) |
| language hi | v2.5 transcribe | 140 | 139/140 (99%, 96-100) | 1/140 (1%, 0-4) | 0/140 (0%, 0-3) |
| language hi | v2.5 literal | 140 | 139/140 (99%, 96-100) | 0/140 (0%, 0-3) | 1/140 (1%, 0-4) |
| language hi-en | v3.0 transcribe | 140 | 114/140 (81%, 74-87) | 2/140 (1%, 0-5) | 24/140 (17%, 12-24) |
| language hi-en | v3.0 verbatim | 140 | 136/140 (97%, 93-99) | 4/140 (3%, 1-7) | 0/140 (0%, 0-3) |
| language hi-en | v2.5 transcribe | 140 | 129/140 (92%, 86-96) | 11/140 (8%, 4-14) | 0/140 (0%, 0-3) |
| language hi-en | v2.5 literal | 140 | 140/140 (100%, 97-100) | 0/140 (0%, 0-3) | 0/140 (0%, 0-3) |

### Paired tests

- silent wrong v3.0 transcribe only 40, v2.5 transcribe only 0; exact McNemar p = 1.8e-12
- silent wrong v2.5 transcribe only 0, v2.5 literal only 1; exact McNemar p = 1
- v3.0 transcribe: 68 pairs; silent wrong on the skipped item only 40, on the control only 0, on both 0; exact McNemar p = 1.8e-12
- v2.5 transcribe: 68 pairs; silent wrong on the skipped item only 0, on the control only 0, on both 0; exact McNemar p = 1
- Context: the naive digits rule on v3.0 transcribe text: silent wrong 45/280 (16%, 12-21)

### Mechanism: where the digits are wrong, what the words of the same clip say

| subset | digits wrong; words from | digits wrong | words right | words same wrong | words other wrong | words refused |
| --- | --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe wrong; v3.0 verbatim | 40 | 40/40 (100%, 91-100) | 0 | 0 | 0 |
| all | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |
| retail band | v3.0 transcribe wrong; v3.0 verbatim | 23 | 23/23 (100%, 86-100) | 0 | 0 | 0 |
| retail band | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |
| skipped | v3.0 transcribe wrong; v3.0 verbatim | 40 | 40/40 (100%, 91-100) | 0 | 0 | 0 |
| skipped | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |
| control | v3.0 transcribe wrong; v3.0 verbatim | 0 | 0/0 | 0 | 0 | 0 |
| control | v2.5 transcribe wrong; v2.5 literal | 0 | 0/0 | 0 | 0 | 0 |

### Acceptance schemes

| subset | scheme (accept when equal) | requests | accepted (coverage) | accepted wrong | P(correct \| accepted) |
| --- | --- | --- | --- | --- | --- |
| all | v3.0 transcribe alone | 1 | 275/280 (98%, 96-99) | 40 | 235/275 (85%, 81-89) |
| all | v2.5 transcribe alone | 1 | 268/280 (96%, 93-98) | 0 | 268/268 (100%, 99-100) |
| all | v2.5 literal alone | 1 | 280/280 (100%, 99-100) | 1 | 279/280 (100%, 98-100) |
| all | v2.5 transcribe = v2.5 literal (one request) | 1 | 267/280 (95%, 92-97) | 0 | 267/267 (100%, 99-100) |
| all | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 224/280 (80%, 75-84) | 0 | 224/224 (100%, 98-100) |
| all | v3.0 transcribe = v2.5 literal | 2 | 234/280 (84%, 79-87) | 0 | 234/234 (100%, 98-100) |
| all | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 223/280 (80%, 75-84) | 0 | 223/223 (100%, 98-100) |
| all | v3.0 transcribe = v3.0 verbatim | 2 | 230/280 (82%, 77-86) | 0 | 230/230 (100%, 98-100) |
| all | v3.0 verbatim = v2.5 literal | 2 | 276/280 (99%, 96-99) | 1 | 275/276 (100%, 98-100) |
| retail band | v3.0 transcribe alone | 1 | 205/209 (98%, 95-99) | 23 | 182/205 (89%, 84-92) |
| retail band | v2.5 transcribe alone | 1 | 198/209 (95%, 91-97) | 0 | 198/198 (100%, 98-100) |
| retail band | v2.5 literal alone | 1 | 209/209 (100%, 98-100) | 1 | 208/209 (100%, 97-100) |
| retail band | v2.5 transcribe = v2.5 literal (one request) | 1 | 197/209 (94%, 90-97) | 0 | 197/197 (100%, 98-100) |
| retail band | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 172/209 (82%, 77-87) | 0 | 172/172 (100%, 98-100) |
| retail band | v3.0 transcribe = v2.5 literal | 2 | 181/209 (87%, 81-91) | 0 | 181/181 (100%, 98-100) |
| retail band | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 171/209 (82%, 76-86) | 0 | 171/171 (100%, 98-100) |
| retail band | v3.0 transcribe = v3.0 verbatim | 2 | 178/209 (85%, 80-89) | 0 | 178/178 (100%, 98-100) |
| retail band | v3.0 verbatim = v2.5 literal | 2 | 206/209 (99%, 96-100) | 1 | 205/206 (100%, 97-100) |
| skipped | v3.0 transcribe alone | 1 | 63/68 (93%, 84-97) | 40 | 23/63 (37%, 26-49) |
| skipped | v2.5 transcribe alone | 1 | 66/68 (97%, 90-99) | 0 | 66/66 (100%, 94-100) |
| skipped | v2.5 literal alone | 1 | 68/68 (100%, 95-100) | 1 | 67/68 (99%, 92-100) |
| skipped | v2.5 transcribe = v2.5 literal (one request) | 1 | 65/68 (96%, 88-98) | 0 | 65/65 (100%, 94-100) |
| skipped | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 22/68 (32%, 22-44) | 0 | 22/22 (100%, 85-100) |
| skipped | v3.0 transcribe = v2.5 literal | 2 | 22/68 (32%, 22-44) | 0 | 22/22 (100%, 85-100) |
| skipped | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 21/68 (31%, 21-43) | 0 | 21/21 (100%, 85-100) |
| skipped | v3.0 transcribe = v3.0 verbatim | 2 | 22/68 (32%, 22-44) | 0 | 22/22 (100%, 85-100) |
| skipped | v3.0 verbatim = v2.5 literal | 2 | 68/68 (100%, 95-100) | 1 | 67/68 (99%, 92-100) |
| control | v3.0 transcribe alone | 1 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |
| control | v2.5 transcribe alone | 1 | 66/68 (97%, 90-99) | 0 | 66/66 (100%, 94-100) |
| control | v2.5 literal alone | 1 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |
| control | v2.5 transcribe = v2.5 literal (one request) | 1 | 66/68 (97%, 90-99) | 0 | 66/66 (100%, 94-100) |
| control | v3.0 transcribe = v2.5 transcribe (reference) | 2 | 66/68 (97%, 90-99) | 0 | 66/66 (100%, 94-100) |
| control | v3.0 transcribe = v2.5 literal | 2 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |
| control | v3.0 transcribe = v2.5 transcribe = v2.5 literal | 2 | 66/68 (97%, 90-99) | 0 | 66/66 (100%, 94-100) |
| control | v3.0 transcribe = v3.0 verbatim | 2 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |
| control | v3.0 verbatim = v2.5 literal | 2 | 68/68 (100%, 95-100) | 0 | 68/68 (100%, 95-100) |

### Clips a two-reading scheme does not accept

| pair | not accepted | two amounts | one refused | both refused | first right | second right | neither right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v3.0 transcribe vs v2.5 transcribe | 56 | 39 | 17 | 0 | 11 | 44 | 1 |
| v2.5 transcribe vs v2.5 literal | 13 | 1 | 12 | 0 | 1 | 12 | 0 |
| v3.0 transcribe vs v2.5 literal | 46 | 41 | 5 | 0 | 1 | 45 | 0 |

### Clips where any reading is not gold

| item | stratum | shape/source | gold | v3.0 transcribe | v3.0 verbatim | v2.5 transcribe | v2.5 literal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| amt2-hi-en-control-011 | control | lakh_hundreds | 202000 | ok | ok | refused | ok |
| amt2-hi-en-control-020 | control | thousand_units | 99100 | ok | ok | refused | ok |
| amt2-hi-en-fraction-001 | fraction | and_a_half | 150000 | ok | refused | ok | ok |
| amt2-hi-en-fraction-002 | fraction | and_a_half | 450000 | ok | refused | ok | ok |
| amt2-hi-en-fraction-004 | fraction | and_a_half | 15000000 | ok | refused | ok | ok |
| amt2-hi-en-fraction-008 | fraction | point | 12500000 | ok | ok | refused | ok |
| amt2-hi-en-fraction-013 | fraction | saadhe | 9500 | ok | ok | refused | ok |
| amt2-hi-en-fraction-014 | fraction | saadhe | 8500 | ok | refused | refused | ok |
| amt2-hi-en-general-004 | general | thousand | 98000 | ok | ok | refused | ok |
| amt2-hi-en-general-025 | general | thousand_hundred_rest | 90195 | ok | ok | refused | ok |
| amt2-hi-en-general-027 | general | thousand_hundred_rest | 13290 | ok | ok | refused | ok |
| amt2-hi-en-general-031 | general | thousand_hundred_rest | 99345 | ok | ok | refused | ok |
| amt2-hi-en-general-047 | general | lakh_thousand_hundred | 499800 | ok | ok | refused | ok |
| amt2-hi-en-skipped-001 | skipped | lakh_units | 400011 | **411000** | ok | ok | ok |
| amt2-hi-en-skipped-002 | skipped | lakh_units | 200086 | **286000** | ok | ok | ok |
| amt2-hi-en-skipped-003 | skipped | lakh_units | 200014 | **214000** | ok | ok | ok |
| amt2-hi-en-skipped-004 | skipped | lakh_units | 100006 | **106000** | ok | ok | ok |
| amt2-hi-en-skipped-005 | skipped | lakh_units | 100049 | **149000** | ok | ok | ok |
| amt2-hi-en-skipped-006 | skipped | lakh_units | 200079 | **279000** | ok | ok | ok |
| amt2-hi-en-skipped-007 | skipped | lakh_units | 100016 | **116000** | ok | ok | ok |
| amt2-hi-en-skipped-008 | skipped | lakh_units | 1200080 | **1280000** | ok | ok | ok |
| amt2-hi-en-skipped-009 | skipped | lakh_units | 900020 | **920000** | ok | ok | ok |
| amt2-hi-en-skipped-010 | skipped | lakh_hundreds | 100400 | **1400** | ok | ok | ok |
| amt2-hi-en-skipped-012 | skipped | lakh_hundreds | 400900 | **409000** | ok | ok | ok |
| amt2-hi-en-skipped-013 | skipped | lakh_hundreds | 100300 | **1300** | ok | ok | ok |
| amt2-hi-en-skipped-014 | skipped | lakh_hundreds | 300500 | **3500** | ok | ok | ok |
| amt2-hi-en-skipped-016 | skipped | lakh_hundreds | 300800 | **308000** | ok | ok | ok |
| amt2-hi-en-skipped-017 | skipped | lakh_hundreds | 6000900 | refused | ok | ok | ok |
| amt2-hi-en-skipped-018 | skipped | lakh_hundreds | 900300 | **903000** | ok | ok | ok |
| amt2-hi-en-skipped-020 | skipped | thousand_units | 99073 | ok | ok | refused | ok |
| amt2-hi-en-skipped-022 | skipped | thousand_units | 14060 | **14600** | ok | ok | ok |
| amt2-hi-en-skipped-023 | skipped | thousand_units | 30003 | **30000** | ok | ok | ok |
| amt2-hi-en-skipped-025 | skipped | thousand_units | 79006 | refused | ok | ok | ok |
| amt2-hi-en-skipped-027 | skipped | thousand_units | 45008 | **45800** | ok | ok | ok |
| amt2-hi-en-skipped-029 | skipped | crore_thousands | 20070000 | **270000** | ok | ok | ok |
| amt2-hi-en-skipped-030 | skipped | crore_thousands | 40030000 | **430000** | ok | ok | ok |
| amt2-hi-en-skipped-031 | skipped | crore_thousands | 150007000 | **1507000** | ok | ok | ok |
| amt2-hi-en-skipped-032 | skipped | crore_thousands | 50012000 | **512000** | ok | ok | ok |
| amt2-hi-en-skipped-033 | skipped | crore_thousands | 80007000 | **807000** | ok | ok | ok |
| amt2-hi-en-skipped-034 | skipped | crore_thousands | 80009000 | **809000** | ok | ok | ok |
| amt2-hi-skipped-001 | skipped | lakh_units | 300040 | **340000** | ok | ok | ok |
| amt2-hi-skipped-002 | skipped | lakh_units | 100014 | **114000** | ok | ok | ok |
| amt2-hi-skipped-003 | skipped | lakh_units | 400008 | **408000** | ok | ok | ok |
| amt2-hi-skipped-004 | skipped | lakh_units | 200022 | **222000** | ok | ok | ok |
| amt2-hi-skipped-005 | skipped | lakh_units | 100001 | ok | **100000** | ok | **100000** |
| amt2-hi-skipped-006 | skipped | lakh_units | 300095 | **395000** | ok | refused | ok |
| amt2-hi-skipped-008 | skipped | lakh_units | 3000009 | **3000000** | ok | ok | ok |
| amt2-hi-skipped-009 | skipped | lakh_units | 900005 | **900000** | ok | ok | ok |
| amt2-hi-skipped-011 | skipped | lakh_hundreds | 400700 | **407000** | ok | ok | ok |
| amt2-hi-skipped-013 | skipped | lakh_hundreds | 400900 | **4900** | ok | ok | ok |
| amt2-hi-skipped-019 | skipped | thousand_units | 56082 | refused | ok | ok | ok |
| amt2-hi-skipped-022 | skipped | thousand_units | 12081 | refused | ok | ok | ok |
| amt2-hi-skipped-027 | skipped | thousand_units | 8006 | refused | ok | ok | ok |
| amt2-hi-skipped-028 | skipped | thousand_units | 2012 | **2000** | ok | ok | ok |
| amt2-hi-skipped-029 | skipped | crore_thousands | 50026000 | **526000** | ok | ok | ok |
| amt2-hi-skipped-030 | skipped | crore_thousands | 10002000 | **102000** | ok | ok | ok |
| amt2-hi-skipped-031 | skipped | crore_thousands | 20034000 | **234000** | ok | ok | ok |
| amt2-hi-skipped-032 | skipped | crore_thousands | 70011000 | **711000** | ok | ok | ok |
| amt2-hi-skipped-033 | skipped | crore_thousands | 10066000 | **166000** | ok | ok | ok |
| amt2-hi-skipped-034 | skipped | crore_thousands | 10068000 | **168000** | ok | ok | ok |

## Requests: latency and estimated cost

| request | rows | live calls | median s | p90 s | est. credits | audio s |
| --- | --- | --- | --- | --- | --- | --- |
| v3.0 transcribe item | 560 | 560 | 0.27 | 0.42 | 18.48 | 1848 |
| v3.0 verbatim item | 560 | 560 | 0.27 | 0.41 | 18.48 | 1848 |
| v2.5 transcribe item | 560 | 560 | 0.26 | 0.40 | 18.48 | 1848 |

Latency is wall time per live request through the client lock (cache hits left out). Credits are the client's estimate (0.010 per audio second for both models), not a dashboard reading.

