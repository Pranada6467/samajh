# Public real-voice datasets for evaluation

> Gathered during the dropped Pukaar idea, but **idea-independent**: reusable for any project's STT evaluation.

Checked 2026-11-10. Decision: public, consent-based, openly licensed datasets are used **for evaluation only** — never shown in the demo video, never committed to the repo (ship download scripts). Cite license + consent statement in the write-up.

## Shortlist
| Dataset | Use | License / access | Consent |
|---|---|---|---|
| [IndicVoices](https://huggingface.co/datasets/ai4bharat/IndicVoices) (AI4Bharat) | Hindi `valid` split, **solo phone-app recordings only** (skip 8 kHz phone-line role-plays). Spontaneous, natural Hinglish, noisy real places. ~150 clips < 10 s | CC-BY-4.0, HF gated | Explicit, paid (paper §10) |
| [Kathbath](https://huggingface.co/datasets/ai4bharat/Kathbath) noisy test (AI4Bharat) | Hindi Noisy-Test-Unknown: real noisy phone recordings, unseen speakers. ~100 clips | CC-BY-4.0 / CC0 (card conflict), HF gated | In-app consent, paid |
| [MUSAN](https://www.openslr.org/17/) + [DEMAND](https://zenodo.org/records/1227121) (STRAFFIC, TBUS) | Mix street/bus noise into clean clips at 0/5/10 dB SNR; plus 8 kHz G.711 copies | CC-BY-4.0; DEMAND CC-BY(-SA) | n/a |
| [MUCS 2021 sub-task 2](https://www.openslr.org/104/) | Optional: Hindi-English code-switching stress test. ~50 clips | CC-BY-SA-4.0, open | Not stated |

Trick to get closer to the use case: search IndicVoices / [Vaani](https://huggingface.co/datasets/ARTPARK-IISc/Vaani) transcripts for trigger words ("peeche", "bachao", "police", "madad", "bus stop") and score keyword recall on that real-voice subset.

## Never use
Gram Vaani (real phone recordings), IndicVoices 8 kHz phone-line conversations, any call-centre or emergency-call corpus (CEMO, SAFE-T), YouTube-scraped audio, ESC-50 (CC-BY-NC).

## Gaps
No public Indian distress/emergency speech. No openly licensed Hindi whispered speech (IISc Wspire: license unconfirmed). Hindi emotional-speech sets are acted, small, request-only. → State plainly: not tested on real distressed or whispered voices.

## Rule wording (gnani.ai/internship, challenge blog)
"Use synthetic data only." "Don't put anyone's real phone numbers, account numbers, Aadhaar, PAN or recorded calls into your project or demo." "Write sample scripts, record yourself or your teammate with consent, and generate fake identifiers." "Voice data is personal data under India's DPDP Act." Third-party datasets aren't mentioned — this use is a judgement call, kept to an offline evaluation appendix.
