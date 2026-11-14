# W7 Part A: the amount finding against open models and a closed reference

Written by `uv run python eval/openbench/part_a.py` (offline). Prisma rows are P6's, read as `eval/amounts_v2/analyze.py` reads them; every text is parsed by `samajh.amounts` at 59c12d9 (`eval/amounts_v2/frozen_parser.py`). Outcomes: right, wrong (an amount that is not gold), no amount, ambiguous, missing (no row or an error row). Rates: count/n (percent, Wilson 95%). `gemini-3-flash` is a closed reference, not an open baseline. All amounts-v2 audio is TTS; real-voice tables hold ids and amounts only. `indicwhisper-hi` (AI4Bharat IndicWhisper, Vistaar Hindi Whisper-medium) is trained on Vistaar data, which includes Kathbath, so its figures on the Kathbath train clips among the 124 public clips are probably in-sample for it. Primary third reading for the product question: `indicwhisper-hi`. IndicConformer was not run (gated model).

Self-check against P6:

- amounts-v2 phone clips: 280 (P6 280) ok
- v3.0 T wrong on skipped: 40 (P6 40) ok
- skipped n: 68 (P6 68) ok
- v3.0 T wrong on controls: 0 (P6 0) ok
- controls n: 68 (P6 68) ok
- reference accepted (amounts-v2): 224 (P6 224) ok
- reference wrong accepted (amounts-v2): 0 (P6 0) ok
- realvoice phone clips: 124 (P6 124) ok
- reference accepted (realvoice): 113 (P6 113) ok
- reference wrong accepted (realvoice): 0 (P6 0) ok

Rows found per system: amounts-v2: whisper-large-v3 280, indicwhisper-hi 280, gemini-3-flash 280, gemini-3.1-pro-partial 68; realvoice: whisper-large-v3 124, indicwhisper-hi 124, gemini-3-flash 124, gemini-3.1-pro-partial 80

Real-voice clips with all Prisma readings: 124 items.

## amounts-v2, condition `phone` (n = 280 clips)

### (a) Outcomes per system
| subset | system | right | wrong | no amount | ambiguous | missing |
|---|---|---|---|---|---|---|
| skipped | v3.0 transcribe | 23/68 (34%, 24-46) | 40/68 (59%, 47-70) | 0 | 5 | 0 |
| skipped | v3.0 verbatim | 67/68 (99%, 92-100) | 1/68 (1%, 0-8) | 0 | 0 | 0 |
| skipped | v2.5 transcribe | 66/68 (97%, 90-99) | 0/68 (0%, 0-5) | 0 | 2 | 0 |
| skipped | v2.5 literal | 67/68 (99%, 92-100) | 1/68 (1%, 0-8) | 0 | 0 | 0 |
| skipped | whisper-large-v3 | 23/68 (34%, 24-46) | 33/68 (49%, 37-60) | 0 | 12 | 0 |
| skipped | indicwhisper-hi | 44/68 (65%, 53-75) | 15/68 (22%, 14-33) | 0 | 9 | 0 |
| skipped | gemini-3-flash (closed reference) | 60/68 (88%, 78-94) | 8/68 (12%, 6-22) | 0 | 0 | 0 |
| skipped | gemini-3.1-pro-partial (closed reference, partial: 68 clips, not used in schemes) | 0/68 (0%, 0-5) | 0/68 (0%, 0-5) | 0 | 0 | 68 |
| control | v3.0 transcribe | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0 | 0 | 0 |
| control | v3.0 verbatim | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0 | 0 | 0 |
| control | v2.5 transcribe | 66/68 (97%, 90-99) | 0/68 (0%, 0-5) | 0 | 2 | 0 |
| control | v2.5 literal | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0 | 0 | 0 |
| control | whisper-large-v3 | 43/68 (63%, 51-74) | 13/68 (19%, 12-30) | 0 | 12 | 0 |
| control | indicwhisper-hi | 42/68 (62%, 50-72) | 16/68 (24%, 15-35) | 0 | 10 | 0 |
| control | gemini-3-flash (closed reference) | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0 | 0 | 0 |
| control | gemini-3.1-pro-partial (closed reference, partial: 68 clips, not used in schemes) | 66/68 (97%, 90-99) | 0/68 (0%, 0-5) | 0 | 1 | 1 |
| all | v3.0 transcribe | 235/280 (84%, 79-88) | 40/280 (14%, 11-19) | 0 | 5 | 0 |
| all | v3.0 verbatim | 275/280 (98%, 96-99) | 1/280 (0%, 0-2) | 0 | 4 | 0 |
| all | v2.5 transcribe | 268/280 (96%, 93-98) | 0/280 (0%, 0-1) | 0 | 12 | 0 |
| all | v2.5 literal | 279/280 (100%, 98-100) | 1/280 (0%, 0-2) | 0 | 0 | 0 |
| all | whisper-large-v3 | 179/280 (64%, 58-69) | 50/280 (18%, 14-23) | 2 | 49 | 0 |
| all | indicwhisper-hi | 184/280 (66%, 60-71) | 49/280 (18%, 13-22) | 3 | 44 | 0 |
| all | gemini-3-flash (closed reference) | 271/280 (97%, 94-98) | 9/280 (3%, 2-6) | 0 | 0 | 0 |
| all | gemini-3.1-pro-partial (closed reference, partial: 68 clips, not used in schemes) | 67/280 (24%, 19-29) | 0/280 (0%, 0-1) | 0 | 1 | 212 |

### (b) Skipped vs matched control, exact McNemar on `wrong` over the pairs
| system | pairs | wrong on skipped only | wrong on control only | exact p |
|---|---|---|---|---|
| v3.0 transcribe | 68 | 40 | 0 | 1.8e-12 |
| v3.0 verbatim | 68 | 1 | 0 | 1 |
| v2.5 transcribe | 68 | 0 | 0 | 1 |
| v2.5 literal | 68 | 1 | 0 | 1 |
| whisper-large-v3 | 68 | 24 | 4 | 0.00018 |
| indicwhisper-hi | 68 | 9 | 10 | 1 |
| gemini-3-flash (closed reference) | 68 | 8 | 0 | 0.0078 |

### (c) Each other system vs Prisma `transcribe`, exact McNemar on `right`
| subset | system | vs | n | system only right | Prisma only right | exact p |
|---|---|---|---|---|---|---|
| skipped | whisper-large-v3 | v3.0 transcribe | 68 | 11 | 11 | 1 |
| skipped | whisper-large-v3 | v2.5 transcribe | 68 | 1 | 44 | 2.6e-12 |
| skipped | indicwhisper-hi | v3.0 transcribe | 68 | 27 | 6 | 0.00032 |
| skipped | indicwhisper-hi | v2.5 transcribe | 68 | 2 | 24 | 1e-05 |
| skipped | gemini-3-flash (closed reference) | v3.0 transcribe | 68 | 38 | 1 | 1.5e-10 |
| skipped | gemini-3-flash (closed reference) | v2.5 transcribe | 68 | 1 | 7 | 0.07 |

### (d) Acceptance schemes (a third reading)
| subset | scheme | n | accepted | wrong accepted | re-asks |
|---|---|---|---|---|---|
| skipped | 1 reference: v3.0 T = v2.5 T | 68 | 22 | 0 | 46 |
| skipped | 2 unanimous: v3.0 T = v2.5 T = whisper-large-v3 | 68 | 11 | 0 | 57 |
| skipped | 3 majority of v3.0 T, v2.5 T, whisper-large-v3 | 68 | 44 | 10 | 24 |
| skipped | 4 swap: whisper-large-v3 = v2.5 T | 68 | 22 | 0 | 46 |
| skipped | 1 reference: v3.0 T = v2.5 T | 68 | 22 | 0 | 46 |
| skipped | 2 unanimous: v3.0 T = v2.5 T = indicwhisper-hi | 68 | 16 | 0 | 52 |
| skipped | 3 majority of v3.0 T, v2.5 T, indicwhisper-hi | 68 | 49 | 0 | 19 |
| skipped | 4 swap: indicwhisper-hi = v2.5 T | 68 | 42 | 0 | 26 |
| skipped | 1 reference: v3.0 T = v2.5 T | 68 | 22 | 0 | 46 |
| skipped | 2 unanimous: v3.0 T = v2.5 T = gemini-3-flash (closed reference) | 68 | 21 | 0 | 47 |
| skipped | 3 majority of v3.0 T, v2.5 T, gemini-3-flash (closed reference) | 68 | 66 | 5 | 2 |
| skipped | 4 swap: gemini-3-flash (closed reference) = v2.5 T | 68 | 59 | 0 | 9 |
| all | 1 reference: v3.0 T = v2.5 T | 280 | 224 | 0 | 56 |
| all | 2 unanimous: v3.0 T = v2.5 T = whisper-large-v3 | 280 | 159 | 0 | 121 |
| all | 3 majority of v3.0 T, v2.5 T, whisper-large-v3 | 280 | 254 | 10 | 26 |
| all | 4 swap: whisper-large-v3 = v2.5 T | 280 | 170 | 0 | 110 |
| all | 1 reference: v3.0 T = v2.5 T | 280 | 224 | 0 | 56 |
| all | 2 unanimous: v3.0 T = v2.5 T = indicwhisper-hi | 280 | 155 | 0 | 125 |
| all | 3 majority of v3.0 T, v2.5 T, indicwhisper-hi | 280 | 252 | 0 | 28 |
| all | 4 swap: indicwhisper-hi = v2.5 T | 280 | 181 | 0 | 99 |
| all | 1 reference: v3.0 T = v2.5 T | 280 | 224 | 0 | 56 |
| all | 2 unanimous: v3.0 T = v2.5 T = gemini-3-flash (closed reference) | 280 | 222 | 0 | 58 |
| all | 3 majority of v3.0 T, v2.5 T, gemini-3-flash (closed reference) | 280 | 278 | 5 | 2 |
| all | 4 swap: gemini-3-flash (closed reference) = v2.5 T | 280 | 260 | 0 | 20 |

### (e) Every wrong amount from an open system or the closed reference
| system | item | gold | amount given | text |
|---|---|---|---|---|
| whisper-large-v3 | amt2-hi-control-003 | 408000 | 400000 | मुझे लगता है कवर 4,00,000 रुपए का है |
| whisper-large-v3 | amt2-hi-control-005 | 101000 | 1000 | कुल एक लाग एक हजार का बीमा हुआ है |
| whisper-large-v3 | amt2-hi-control-007 | 205000 | 200000 | उन्होंने बताया था कि प्रीमियम 2,00,000 होगा। |
| whisper-large-v3 | amt2-hi-control-009 | 905000 | 900000 | हाथ में 9,00,000 आए। |
| whisper-large-v3 | amt2-hi-control-011 | 407000 | 4007000 | पॉलिसी के लिए 4,007,000 रुपए दिये थे। |
| whisper-large-v3 | amt2-hi-control-012 | 202000 | 2002000 | लोन की रकम में से 2,002,000 रुपए बीमा के लिए कट गए। |
| whisper-large-v3 | amt2-hi-control-014 | 107000 | 1007000 | प्रेमियम की रकम 1,007,000 थी |
| whisper-large-v3 | amt2-hi-control-016 | 208000 | 200000 | उन्होंने बताया था कि प्रेमियम 2,00,000 होगा। |
| whisper-large-v3 | amt2-hi-control-017 | 1805000 | 1800000 | बैंक वालों ने 18,00,000 रुपए सीधे काट लिये। |
| whisper-large-v3 | amt2-hi-en-control-011 | 202000 | 200000 | अकाउंट में 2,00,000 आए। |
| whisper-large-v3 | amt2-hi-en-control-015 | 205000 | 200000 | अकाउंट में 2,00,000 आए |
| whisper-large-v3 | amt2-hi-en-control-030 | 43000000 | 430000 | प्रेमियम की अमाउंट 4,30,000 थी |
| whisper-large-v3 | amt2-hi-en-control-031 | 150700000 | 700000 | जहां तक याद है, 15 क्रोड 7 लाख रुपीज लगे थे। |
| whisper-large-v3 | amt2-hi-en-general-046 | 105500 | 155000 | जहां तक याद है, 1,55,000 रुपीज लगे थे। |
| whisper-large-v3 | amt2-hi-en-large-004 | 1504000 | 15004000 | उन्होंने बोला था कि प्रेमियम 15,004,000 रुपीज होगा। |
| whisper-large-v3 | amt2-hi-en-skipped-001 | 400011 | 411000 | टोटल 4,11,000 का इंशौरेंस हुआ है। |
| whisper-large-v3 | amt2-hi-en-skipped-002 | 200086 | 286000 | इंस्टॉल्मेंट 2,86,000 रुपीज की बनती है |
| whisper-large-v3 | amt2-hi-en-skipped-003 | 200014 | 214000 | बैंक वालों ने 2,14,000 रुपीज सीधे डिडक्ट कर लिये। |
| whisper-large-v3 | amt2-hi-en-skipped-005 | 100049 | 149000 | टोटल 1,49,000 का इंशुर्ज हुआ है |
| whisper-large-v3 | amt2-hi-en-skipped-007 | 100016 | 116000 | मुझे लगता है कवर 1,16,000 रुपीज का है |
| whisper-large-v3 | amt2-hi-en-skipped-008 | 1200080 | 1280000 | बैंक वालों ने 12,80,000 रुपीज सीधे डिडफ्ट कर लिये। |
| whisper-large-v3 | amt2-hi-en-skipped-010 | 100400 | 1400000 | जहां तक याद है, 1,400,000 रुपीज लगे थे. |
| whisper-large-v3 | amt2-hi-en-skipped-011 | 200200 | 2200000 | अकाउंट में 2,200,000 आए। |
| whisper-large-v3 | amt2-hi-en-skipped-012 | 400900 | 4900000 | उन्होंने बोला था कि प्रीमियम 4,900,000 रुपीस होगा। |
| whisper-large-v3 | amt2-hi-en-skipped-013 | 100300 | 1300000 | बैंक वालों ने 1,300,000 रुपी सीधे डिडक्ट कर लिये। |
| whisper-large-v3 | amt2-hi-en-skipped-014 | 300500 | 3500000 | उन्होंने बोला था कि प्रीमियम 3,500,000 रुपीज होगा। |
| whisper-large-v3 | amt2-hi-en-skipped-015 | 200500 | 2500000 | अकाउंट में 2,500,000 आए। |
| whisper-large-v3 | amt2-hi-en-skipped-016 | 300800 | 3800000 | मुझे लगता है कवर 3,800,000 रुपीज का है |
| whisper-large-v3 | amt2-hi-en-skipped-017 | 6000900 | 60900000 | मुझे लगता है कवर 60,900,000 का है |
| whisper-large-v3 | amt2-hi-en-skipped-018 | 900300 | 9300000 | रिसीट पर 9,300,000 रुपीज लिखा है। |
| whisper-large-v3 | amt2-hi-en-skipped-025 | 79006 | 79060 | प्रेमियम की amount 79,060 थी |
| whisper-large-v3 | amt2-hi-en-skipped-029 | 20070000 | 70000 | इंस्टॉल्मेंट 2 क्रोज 70,000 रुपीस की बनती है |
| whisper-large-v3 | amt2-hi-en-skipped-030 | 40030000 | 430000 | प्रेमियम की अमाउंट 4,30,000 थी |
| whisper-large-v3 | amt2-hi-en-skipped-031 | 150007000 | 7000 | जहां तक याद है, 15 करोर 7,000 रुपीज लगे थे। |
| whisper-large-v3 | amt2-hi-en-skipped-032 | 50012000 | 12000 | जहां तक याद है, 5 करोर 12,000 रुपीज लगे थे। |
| whisper-large-v3 | amt2-hi-fraction-003 | 225000 | 200000 | मुझे लगता है कवर समा 2 लाख रुपे का है |
| whisper-large-v3 | amt2-hi-large-004 | 4567000 | 4566000 | उन्होंने बताया था कि प्रेमियम 45,66,000 होगा। |
| whisper-large-v3 | amt2-hi-skipped-001 | 300040 | 340000 | उन्होंने बताया था कि प्रीमियम 3,40,000 रुपए होगा। |
| whisper-large-v3 | amt2-hi-skipped-004 | 200022 | 222000 | मुझे लगता है कवर 2,22,000 रुपए का है |
| whisper-large-v3 | amt2-hi-skipped-006 | 300095 | 395000 | मुझे लगता है कवर 3,95,000 रुपए का है |
| whisper-large-v3 | amt2-hi-skipped-008 | 3000009 | 3009000 | रसीद पर 30,09,000 रुपे लिखा है |
| whisper-large-v3 | amt2-hi-skipped-010 | 200400 | 2400000 | कुल 2,400,000 का बीमा हुआ है |
| whisper-large-v3 | amt2-hi-skipped-011 | 400700 | 4700000 | पॉलिसी के लिए 4,700,000 रुपए दिये थे |
| whisper-large-v3 | amt2-hi-skipped-012 | 200200 | 2200000 | लोन की रकम में से 2,200,000 रुपए बीमा के लिए कट गए। |
| whisper-large-v3 | amt2-hi-skipped-013 | 400900 | 4900000 | लोन की रकम में से 4,900,000 रुपे बीमा के लिए कट गए। |
| whisper-large-v3 | amt2-hi-skipped-014 | 100700 | 1700000 | प्रेमियम की रकम 1,700,000 थी |
| whisper-large-v3 | amt2-hi-skipped-015 | 100900 | 100000 | जहां तक याद है एक लाख नौसो रुपे लगे थे |
| whisper-large-v3 | amt2-hi-skipped-016 | 200800 | 2800000 | उन्होंने बताया था कि प्रीमियम 2,800,000 रुपे होगा। |
| whisper-large-v3 | amt2-hi-skipped-017 | 1800500 | 18500000 | बैंक वालों ने 18,500,000 रुपए सीधे काट लिये। |
| whisper-large-v3 | amt2-hi-skipped-018 | 800600 | 8600000 | प्रीमियम की रकम 8,600,000 थी |
| indicwhisper-hi | amt2-hi-en-control-001 | 411000 | 400011 | टोटल फोर लाख इलेवन थाउसन का इंश्योरेंस हुआ है |
| indicwhisper-hi | amt2-hi-en-control-003 | 214000 | 254400 | बैंक वालों ने दो लाख चौवन हज़ार चार सौ रुपये सीधे डिड़क्क कर लिए |
| indicwhisper-hi | amt2-hi-en-control-005 | 149000 | 104900 | टोटल एक लाख चार हज़ार नौ सौ का इंश्योरेंस हुआ है |
| indicwhisper-hi | amt2-hi-en-control-008 | 1280000 | 1218000 | बैंक वालों ने ट्वेल्व लाख अट्ठारह हज़ार रुपये सीधे डिडेक्ट कर लिए |
| indicwhisper-hi | amt2-hi-en-control-009 | 920000 | 900020 | लोन अमाउंट में से नाइन लाख ट्वेंटी थाउंज़ेन रुपयी इंश्योरेंस के लिए कट गए |
| indicwhisper-hi | amt2-hi-en-control-010 | 104000 | 114000 | जहाँ तक याद है वन लाख चौदह हज़ार रुपये लगे थे |
| indicwhisper-hi | amt2-hi-en-control-011 | 202000 | 200002 | अकाउंट में टू लैक टू थाउसेंट आए |
| indicwhisper-hi | amt2-hi-en-control-018 | 903000 | 900003 | ग्रहफीत पर नाइन लाख थ्री थाउसन रुपयेस लिखा है |
| indicwhisper-hi | amt2-hi-en-control-019 | 17500 | 17075 | रिपीट पर सत्रह हज़ार पचहत्तर रुपये लिखा है |
| indicwhisper-hi | amt2-hi-en-control-020 | 99100 | 100 | रिसीट पर नाइनटी नाइन थाउसन वन हंड्रेड रुपीस लिखा है |
| indicwhisper-hi | amt2-hi-en-control-021 | 17200 | 17722 | टोटल सत्रह हज़ार सात सौ बाईस का इंश्योरेंस हुआ है |
| indicwhisper-hi | amt2-hi-en-control-022 | 14600 | 600 | लोन अमाउंट में से फोर्टीन थाउसेंट सिक्स हंड्रेड रुपये इन्श्योरेंस के लिए कट गए |
| indicwhisper-hi | amt2-hi-en-control-023 | 30300 | 300 | एजेंट ने थर्टी थाउंजन थ्री हंड्रेड बोला था |
| indicwhisper-hi | amt2-hi-en-control-024 | 5700 | 700 | इन्स्टॉलमेंट फ़ाइव थाउज़न सेवन हंड्रेड रुपयीस की बनती है |
| indicwhisper-hi | amt2-hi-en-control-028 | 44900 | 4499 | लोन अमाउंट में से चार हज़ार चार सौ निन्यानवे रुपए इंश्योरेंस के लिए कट गए |
| indicwhisper-hi | amt2-hi-en-control-032 | 51200000 | 52400000 | जहाँ तक याद है पाँच करोड़ चौबिस लाख रुपये लगे थे |
| indicwhisper-hi | amt2-hi-en-fraction-006 | 125000 | 12500000 | उन्होंने बोला था कि प्रीमियम एक सौ पच्चीस लाख रुपए होगा |
| indicwhisper-hi | amt2-hi-en-general-005 | 55000 | 85500 | अकाउंट में पचासी हज़ार पाँच सौ आए |
| indicwhisper-hi | amt2-hi-en-general-006 | 89000 | 18089 | रिफ़ीड पर अट्ठारह हज़ार नवासी रुपये लिखा है |
| indicwhisper-hi | amt2-hi-en-general-013 | 50800 | 50808 | टोटल पचास हज़ार आठ सौ आठ का इंश्योरेंस हुआ है |
| indicwhisper-hi | amt2-hi-en-general-016 | 60800 | 60788 | बैंक वालों ने साठ हज़ार सात सौ अट्ठासी रुपये सीधे डिडेक्ट कर लिए |
| indicwhisper-hi | amt2-hi-en-general-018 | 8900 | 900 | प्रीमियम की अमाउंट आठ हाउंजेंट नौ सौ थी |
| indicwhisper-hi | amt2-hi-en-general-024 | 2900 | 900 | टोटल टू थाउसंट नाइन हंड्रेड का इंश्योरेंस हुआ है |
| indicwhisper-hi | amt2-hi-en-general-025 | 90195 | 90985 | इनस्टोरमेंट नब्बे हज़ार नौ सौ पचासी रुपये की बनती है |
| indicwhisper-hi | amt2-hi-en-general-026 | 4349 | 4439 | उन्होंने बोला था कि प्रीमियम चार हज़ार चार सौ उनतालीस रुपए होगा |
| indicwhisper-hi | amt2-hi-en-general-030 | 70867 | 7777 | लोन अमाउंट में से सात हज़ार सात सौ सतहत्तर रुपये इंश्योरेंस के लिए कट गए |
| indicwhisper-hi | amt2-hi-en-general-031 | 99345 | 300 | प्रीमियम की अमाउंट नाइनटीनाइन थाउसन थ्री हंड्रेड फ़ोर्टीफ़ाइव थी |
| indicwhisper-hi | amt2-hi-en-general-033 | 314000 | 354000 | रिपीट पर तीन लाख चौवन हज़ार रुपये लिखा है |
| indicwhisper-hi | amt2-hi-en-general-034 | 303000 | 300003 | पॉलिसी के लिए थ्री लाख थ्री थाउसन रुपयी स्पे किए थे |
| indicwhisper-hi | amt2-hi-en-general-041 | 835 | 35835 | उन्होंने बोला था कि प्रीमियम पैंतीस हज़ार आठ सौ पैंतीस रुपए होगा |
| indicwhisper-hi | amt2-hi-en-general-047 | 499800 | 419800 | लोन अमाउंट में से चार लाख उन्नीस हज़ार आठ सौ रुपए इंश्योरेंस के लिए कट गए |
| indicwhisper-hi | amt2-hi-en-general-048 | 306500 | 360515 | इन्स्टॉलमेंट थ्री लाख साठ हज़ार पाँच सौ पंद्रह रुपये की बनती है |
| indicwhisper-hi | amt2-hi-en-large-003 | 1550000 | 1500050 | जहाँ तक याद है फ़िफ्टीन लाख फ़िफ्टी थाउजन रुपयी लगे थे |
| indicwhisper-hi | amt2-hi-en-large-004 | 1504000 | 1500004 | उन्होंने बोला था कि प्रीमियम फ़िफ़्टीन लाख फ़ोर थाउसेंट रुपएस होगा |
| indicwhisper-hi | amt2-hi-en-skipped-002 | 200086 | 286 | इंस्टॉलमेंट 286 रुपये की बनती है  इसका क्या मतलब है |
| indicwhisper-hi | amt2-hi-en-skipped-003 | 200014 | 200054 | बैंक वालों ने दो लाख चौवन रुपये सीधे डिडक्ट कर लिए |
| indicwhisper-hi | amt2-hi-en-skipped-005 | 100049 | 100039 | तो पूरा प्रयोग करने के बाद एक लाख उनतालीस का इंश्योरेंस हुआ है |
| indicwhisper-hi | amt2-hi-en-skipped-006 | 200079 | 200097 | पॉलिसी के लिए दो लाख सत्तानवे रुपये पे किए थे |
| indicwhisper-hi | amt2-hi-en-skipped-008 | 1200080 | 1200088 | बैंक वालों ने ट्वेल्व लाख अठासी रुपये सीधे डिडेक्ट कर लिए |
| indicwhisper-hi | amt2-hi-en-skipped-012 | 400900 | 409900 | उन्होंने बोला था कि प्रीमियम चार लाख नौ हज़ार नौ सौ रुपये होगा |
| indicwhisper-hi | amt2-hi-en-skipped-013 | 100300 | 100330 | बैंक वालों ने वन लाख तीन सौ तीस रुपये सीधे डिडेक्ट कर लिए |
| indicwhisper-hi | amt2-hi-en-skipped-018 | 900300 | 900003 | रिसीट पर नाइन लाख थ्री हंड्रा ड्रुपीस लिखा है |
| indicwhisper-hi | amt2-hi-en-skipped-019 | 17086 | 17066 | रिपीट पर सत्रह हज़ार छियासठ रुपये लिखा है |
| indicwhisper-hi | amt2-hi-en-skipped-022 | 14060 | 54060 | लोन अमाउंट में से फर्ँ चौवन हज़ार साठ रुपये इंश्योरेंस के लिए कट गए |
| indicwhisper-hi | amt2-hi-en-skipped-025 | 79006 | 7967 | प्रीमियम की अमाउंट सात हज़ार नौ सौ सरसठ   थी |
| indicwhisper-hi | amt2-hi-en-skipped-026 | 38008 | 3888 | पॉलिसी के लिए तीन हज़ार आठ सौ अठासी रुपये स्पे किये थे |
| indicwhisper-hi | amt2-hi-en-skipped-030 | 40030000 | 40003000 | प्रीमियम की अमाउंट चार करोड़ तीन हज़ार थी |
| indicwhisper-hi | amt2-hi-en-skipped-033 | 80007000 | 80007007 | एजेंट ने आठ करोड़ सात हज़ार सात बोला था |
| indicwhisper-hi | amt2-hi-skipped-005 | 100001 | 100000 | कुल एक लाख एक का बीमा हुआ है |
| gemini-3-flash (closed reference) | amt2-hi-en-skipped-007 | 100016 | 116000 | मुझे लगता है कवर one lakh sixteen thousand का है |
| gemini-3-flash (closed reference) | amt2-hi-en-skipped-008 | 1200080 | 1280000 | बैंक वालों ने twelve lakh eighty thousand rupees सीधे deduct कर लिए। |
| gemini-3-flash (closed reference) | amt2-hi-en-skipped-009 | 900020 | 920 | Loan amount में से nine hundred twenty rupees insurance के लिए कट गए। |
| gemini-3-flash (closed reference) | amt2-hi-en-skipped-017 | 6000900 | 60900 | मुझे लगता है cover sixty thousand nine hundred rupees का है |
| gemini-3-flash (closed reference) | amt2-hi-general-020 | 62200 | 60200 | मुझे लगता है कवर साठ हजार दो सौ रुपये का है |
| gemini-3-flash (closed reference) | amt2-hi-skipped-001 | 300040 | 340000 | उन्होंने बताया था कि प्रीमियम तीन लाख चालीस हजार रुपये होगा। |
| gemini-3-flash (closed reference) | amt2-hi-skipped-002 | 100014 | 114000 | रसीद पर one lakh fourteen thousand रुपये लिखा है। |
| gemini-3-flash (closed reference) | amt2-hi-skipped-005 | 100001 | 100000 | कुल एक लाख एक का बीमा हुआ है। |
| gemini-3-flash (closed reference) | amt2-hi-skipped-006 | 300095 | 395000 | मुझे लगता है कवर three lakh ninety-five thousand रुपए का है |

## amounts-v2, condition `clean16k` (n = 280 clips)

### (a) Outcomes per system
| subset | system | right | wrong | no amount | ambiguous | missing |
|---|---|---|---|---|---|---|
| skipped | v3.0 transcribe | 21/68 (31%, 21-43) | 39/68 (57%, 46-68) | 0 | 8 | 0 |
| skipped | v3.0 verbatim | 67/68 (99%, 92-100) | 1/68 (1%, 0-8) | 0 | 0 | 0 |
| skipped | v2.5 transcribe | 65/68 (96%, 88-98) | 0/68 (0%, 0-5) | 0 | 3 | 0 |
| skipped | v2.5 literal | 67/68 (99%, 92-100) | 1/68 (1%, 0-8) | 0 | 0 | 0 |
| control | v3.0 transcribe | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0 | 0 | 0 |
| control | v3.0 verbatim | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0 | 0 | 0 |
| control | v2.5 transcribe | 65/68 (96%, 88-98) | 0/68 (0%, 0-5) | 0 | 3 | 0 |
| control | v2.5 literal | 68/68 (100%, 95-100) | 0/68 (0%, 0-5) | 0 | 0 | 0 |
| all | v3.0 transcribe | 233/280 (83%, 78-87) | 39/280 (14%, 10-18) | 0 | 8 | 0 |
| all | v3.0 verbatim | 275/280 (98%, 96-99) | 1/280 (0%, 0-2) | 0 | 4 | 0 |
| all | v2.5 transcribe | 266/280 (95%, 92-97) | 0/280 (0%, 0-1) | 0 | 14 | 0 |
| all | v2.5 literal | 279/280 (100%, 98-100) | 1/280 (0%, 0-2) | 0 | 0 | 0 |

### (b) Skipped vs matched control, exact McNemar on `wrong` over the pairs
| system | pairs | wrong on skipped only | wrong on control only | exact p |
|---|---|---|---|---|
| v3.0 transcribe | 68 | 39 | 0 | 3.6e-12 |
| v3.0 verbatim | 68 | 1 | 0 | 1 |
| v2.5 transcribe | 68 | 0 | 0 | 1 |
| v2.5 literal | 68 | 1 | 0 | 1 |

### (c) Each other system vs Prisma `transcribe`, exact McNemar on `right`
No other system has rows here.

### (d) Acceptance schemes (a third reading)
| subset | scheme | n | accepted | wrong accepted | re-asks |
|---|---|---|---|---|---|
| skipped | 1 reference: v3.0 T = v2.5 T | 68 | 21 | 0 | 47 |
| all | 1 reference: v3.0 T = v2.5 T | 280 | 222 | 0 | 58 |

### (e) Every wrong amount from an open system or the closed reference
None.

## realvoice, condition `phone` (n = 124 clips)

### (a) Outcomes per system
| subset | system | right | wrong | no amount | ambiguous | missing |
|---|---|---|---|---|---|---|
| all | v3.0 transcribe | 120/124 (97%, 92-99) | 3/124 (2%, 1-7) | 0 | 1 | 0 |
| all | v3.0 verbatim | 121/124 (98%, 93-99) | 2/124 (2%, 0-6) | 0 | 1 | 0 |
| all | v2.5 transcribe | 115/124 (93%, 87-96) | 4/124 (3%, 1-8) | 3 | 2 | 0 |
| all | v2.5 literal | 119/124 (96%, 91-98) | 2/124 (2%, 0-6) | 0 | 3 | 0 |
| all | whisper-large-v3 | 85/124 (69%, 60-76) | 6/124 (5%, 2-10) | 11 | 22 | 0 |
| all | indicwhisper-hi | 111/124 (90%, 83-94) | 1/124 (1%, 0-4) | 4 | 8 | 0 |
| all | gemini-3-flash (closed reference) | 117/124 (94%, 89-97) | 6/124 (5%, 2-10) | 0 | 1 | 0 |
| all | gemini-3.1-pro-partial (closed reference, partial: 79 clips, not used in schemes) | 72/124 (58%, 49-66) | 3/124 (2%, 1-7) | 0 | 4 | 45 |
| skipped | v3.0 transcribe | 3/4 (75%, 30-95) | 1/4 (25%, 5-70) | 0 | 0 | 0 |
| skipped | v3.0 verbatim | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0 | 0 | 0 |
| skipped | v2.5 transcribe | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0 | 0 | 0 |
| skipped | v2.5 literal | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0 | 0 | 0 |
| skipped | whisper-large-v3 | 2/4 (50%, 15-85) | 0/4 (0%, 0-49) | 0 | 2 | 0 |
| skipped | indicwhisper-hi | 3/4 (75%, 30-95) | 0/4 (0%, 0-49) | 0 | 1 | 0 |
| skipped | gemini-3-flash (closed reference) | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0 | 0 | 0 |
| skipped | gemini-3.1-pro-partial (closed reference, partial: 79 clips, not used in schemes) | 3/4 (75%, 30-95) | 0/4 (0%, 0-49) | 0 | 1 | 0 |

### (c) Each other system vs Prisma `transcribe`, exact McNemar on `right`
| subset | system | vs | n | system only right | Prisma only right | exact p |
|---|---|---|---|---|---|---|
| all | whisper-large-v3 | v3.0 transcribe | 124 | 1 | 36 | 5.5e-10 |
| all | whisper-large-v3 | v2.5 transcribe | 124 | 4 | 34 | 6e-07 |
| all | indicwhisper-hi | v3.0 transcribe | 124 | 0 | 9 | 0.0039 |
| all | indicwhisper-hi | v2.5 transcribe | 124 | 6 | 10 | 0.45 |
| all | gemini-3-flash (closed reference) | v3.0 transcribe | 124 | 1 | 4 | 0.38 |
| all | gemini-3-flash (closed reference) | v2.5 transcribe | 124 | 6 | 4 | 0.75 |
| skipped | whisper-large-v3 | v3.0 transcribe | 4 | 0 | 1 | 1 |
| skipped | whisper-large-v3 | v2.5 transcribe | 4 | 0 | 2 | 0.5 |
| skipped | indicwhisper-hi | v3.0 transcribe | 4 | 0 | 0 | 1 |
| skipped | indicwhisper-hi | v2.5 transcribe | 4 | 0 | 1 | 1 |
| skipped | gemini-3-flash (closed reference) | v3.0 transcribe | 4 | 1 | 0 | 1 |
| skipped | gemini-3-flash (closed reference) | v2.5 transcribe | 4 | 0 | 0 | 1 |

### (d) Acceptance schemes (a third reading)
| subset | scheme | n | accepted | wrong accepted | re-asks |
|---|---|---|---|---|---|
| all | 1 reference: v3.0 T = v2.5 T | 124 | 113 | 0 | 11 |
| all | 2 unanimous: v3.0 T = v2.5 T = whisper-large-v3 | 124 | 81 | 0 | 43 |
| all | 3 majority of v3.0 T, v2.5 T, whisper-large-v3 | 124 | 117 | 1 | 7 |
| all | 4 swap: whisper-large-v3 = v2.5 T | 124 | 82 | 1 | 42 |
| all | 1 reference: v3.0 T = v2.5 T | 124 | 113 | 0 | 11 |
| all | 2 unanimous: v3.0 T = v2.5 T = indicwhisper-hi | 124 | 105 | 0 | 19 |
| all | 3 majority of v3.0 T, v2.5 T, indicwhisper-hi | 124 | 120 | 1 | 4 |
| all | 4 swap: indicwhisper-hi = v2.5 T | 124 | 106 | 1 | 18 |
| all | 1 reference: v3.0 T = v2.5 T | 124 | 113 | 0 | 11 |
| all | 2 unanimous: v3.0 T = v2.5 T = gemini-3-flash (closed reference) | 124 | 110 | 0 | 14 |
| all | 3 majority of v3.0 T, v2.5 T, gemini-3-flash (closed reference) | 124 | 123 | 3 | 1 |
| all | 4 swap: gemini-3-flash (closed reference) = v2.5 T | 124 | 113 | 2 | 11 |
| skipped | 1 reference: v3.0 T = v2.5 T | 4 | 3 | 0 | 1 |
| skipped | 2 unanimous: v3.0 T = v2.5 T = whisper-large-v3 | 4 | 2 | 0 | 2 |
| skipped | 3 majority of v3.0 T, v2.5 T, whisper-large-v3 | 4 | 3 | 0 | 1 |
| skipped | 4 swap: whisper-large-v3 = v2.5 T | 4 | 2 | 0 | 2 |
| skipped | 1 reference: v3.0 T = v2.5 T | 4 | 3 | 0 | 1 |
| skipped | 2 unanimous: v3.0 T = v2.5 T = indicwhisper-hi | 4 | 3 | 0 | 1 |
| skipped | 3 majority of v3.0 T, v2.5 T, indicwhisper-hi | 4 | 3 | 0 | 1 |
| skipped | 4 swap: indicwhisper-hi = v2.5 T | 4 | 3 | 0 | 1 |
| skipped | 1 reference: v3.0 T = v2.5 T | 4 | 3 | 0 | 1 |
| skipped | 2 unanimous: v3.0 T = v2.5 T = gemini-3-flash (closed reference) | 4 | 3 | 0 | 1 |
| skipped | 3 majority of v3.0 T, v2.5 T, gemini-3-flash (closed reference) | 4 | 4 | 0 | 0 |
| skipped | 4 swap: gemini-3-flash (closed reference) = v2.5 T | 4 | 4 | 0 | 0 |

### (e) Every wrong amount from an open system or the closed reference
| system | item | gold | amount given |
|---|---|---|---|
| whisper-large-v3 | rv-iv-023 | 1650 | 1657 |
| whisper-large-v3 | rv-iv-031 | 1037000 | 1000000 |
| whisper-large-v3 | rv-iv-051 | 350 | 300 |
| whisper-large-v3 | rv-iv-062 | 719 | 799 |
| whisper-large-v3 | rv-iv-070 | 3600 | 36 |
| whisper-large-v3 | rv-kb-009 | 40400000 | 40000004 |
| indicwhisper-hi | rv-iv-059 | 8 | 800 |
| gemini-3-flash (closed reference) | rv-iv-006 | 60000 | 4000 |
| gemini-3-flash (closed reference) | rv-iv-023 | 1650 | 1850 |
| gemini-3-flash (closed reference) | rv-iv-024 | 2100 | 21 |
| gemini-3-flash (closed reference) | rv-iv-042 | 8000 | 5000 |
| gemini-3-flash (closed reference) | rv-iv-059 | 8 | 800 |
| gemini-3-flash (closed reference) | rv-iv-070 | 3600 | 36 |

## realvoice, condition `native16k` (n = 124 clips)

### (a) Outcomes per system
| subset | system | right | wrong | no amount | ambiguous | missing |
|---|---|---|---|---|---|---|
| all | v3.0 transcribe | 121/124 (98%, 93-99) | 2/124 (2%, 0-6) | 0 | 1 | 0 |
| all | v3.0 verbatim | 121/124 (98%, 93-99) | 2/124 (2%, 0-6) | 0 | 1 | 0 |
| all | v2.5 transcribe | 115/124 (93%, 87-96) | 4/124 (3%, 1-8) | 3 | 2 | 0 |
| all | v2.5 literal | 119/124 (96%, 91-98) | 2/124 (2%, 0-6) | 0 | 3 | 0 |
| skipped | v3.0 transcribe | 3/4 (75%, 30-95) | 1/4 (25%, 5-70) | 0 | 0 | 0 |
| skipped | v3.0 verbatim | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0 | 0 | 0 |
| skipped | v2.5 transcribe | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0 | 0 | 0 |
| skipped | v2.5 literal | 4/4 (100%, 51-100) | 0/4 (0%, 0-49) | 0 | 0 | 0 |

### (c) Each other system vs Prisma `transcribe`, exact McNemar on `right`
No other system has rows here.

### (d) Acceptance schemes (a third reading)
| subset | scheme | n | accepted | wrong accepted | re-asks |
|---|---|---|---|---|---|
| all | 1 reference: v3.0 T = v2.5 T | 124 | 114 | 0 | 10 |
| skipped | 1 reference: v3.0 T = v2.5 T | 4 | 3 | 0 | 1 |

### (e) Every wrong amount from an open system or the closed reference
None.
