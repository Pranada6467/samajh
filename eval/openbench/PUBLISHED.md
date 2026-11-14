# Published FLEURS Hindi WER figures (read 2026-11-14 from primary sources by a research agent)

Each figure is the source's own number under the source's own normalisation; none is computed here. No source
except SraVaani states the FLEURS split.

| Model | Published WER % | Source | Normalisation the source states |
|---|---|---|---|
| Whisper large-v2 | 21.5 | Whisper paper (arXiv 2212.04356), Appendix D.2.4, Table 13 "WER (%) on Fleurs", Hindi column | Appendix C: drop bracketed text, every character of Unicode category M, S or P to a space, lower-case, collapse spaces (category M includes Devanagari vowel signs) |
| Whisper large-v3 | 17.0 | github.com/openai/whisper README, `language-breakdown.svg`, FLEURS panel, Hindi bar label | reference = FLEURS `transcription` column (pre-normalised), per the v3 announcement (openai/whisper discussion 1762); scorer normaliser not stated |
| Whisper large-v3 | 28.87 | Voxtral report (arXiv 2507.13264), Appendix A.1, Table 4 | not stated |
| IndicWhisper | 15.0, 11.4 or 10.5 | Vistaar (Interspeech 2023 PDF Table 4: 15.0; same PDF Table 3: 11.4; arXiv 2305.15386v2 Table 4: 10.5) | not stated; the sources contradict each other |
| IndicConformer-600M | not found on FLEURS | model card (only an unverified Vaani figure, 13.2), IndicVoices paper, AI4Bharat GitHub | — |
| Gemini 2.5 Flash | 6.76 | Voxtral report, Table 4 | not stated |
| Gemini 3 Flash | 8.7 | SraVaani 1.0 (arXiv 2608.08235) §6.4 | lower-case and punctuation removal, jiwer |
| Gemini 3 Pro, 3.1 Pro | not found on FLEURS Hindi | — | — |

Not FLEURS, for context only: Voice of India (arXiv 2604.19151, Interspeech 2026), unscripted telephone speech,
orthography-informed WER, Hindi: Sarvam Audio 5.0, Gemini 3 Pro 6.0, IndicConformer 8.2, Gemini 3 Flash 8.3.

The same model (Whisper large-v3) is published at 17.0 and at 28.87 on the same test: normalisation and
inference setup alone move FLEURS Hindi WER by more than ten points.
