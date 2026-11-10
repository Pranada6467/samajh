# A difference between Prisma v3.0 and v2.5 `transcribe` on amounts that skip a place-value group

For Gnani's engineers. We build on Prisma and Timbre and measured one difference between two of your models that you may want to know about, with a two-credit reproduction. Full tables: `eval/amounts_v2/REPORT.md`.

## What we saw

On a held-out synthetic set built to stress amounts that skip a place-value group, Prisma v3.0 `transcribe` wrote a different amount for 40 of 68 such amounts (59%, 95% CI 47-70) on simulated 8 kHz phone audio, and for 0 of 68 matched controls (same carrier, voice and leading group). Its `verbatim` output of the same audio had the right number words in all 40, and v2.5 `transcribe` wrote none wrong. The audio is Timbre TTS (Hindi and Hinglish, 13 voices). The 68 are 24% of the set by design, so this is a difference on one kind of amount, not a rate.

## 26 of the 40 are wrong under any reading

From our run, on the simulated phone copy of each clip:

| `verbatim`, same clip | v3.0 `transcribe` | v2.5 `transcribe` |
|---|---|---|
| …वन लाख थ्री हंड्रेड रुपीज़… (one lakh three hundred) | …1,300 rupees… | ₹1,00,300 |
| …पाँच करोड़ छब्बीस हज़ार आए। | …5,26,000 आए। | 5,00,26,000 |
| …दो हज़ार बारह रुपये… | …2,000 रुपये… | ₹2,012 |

The controls with the group present were right on all 68 pairs ("दो हज़ार तीन सौ" gave 2,300). One pair collides: "four lakh nine hundred" and its control "four lakh nine thousand" both came back as 4,09,000. By shape on phone audio, wrong: lakh and units 16 of 18, lakh and hundreds 8 of 18, thousand and units 4 of 20, crore and thousands 12 of 12. Not every such amount fails (23 of the 68 were right), and the outcome (right, refused or wrong) differs between our clean 16 kHz and phone copy of a clip on 9 of the 68.

## 14 more are an open question about colloquial Hindi

Fourteen of the 40 are an "X lakh Y" phrase with Y under 100, written as X lakh Y thousand: "तीन लाख चालीस" as 3,40,000, "two lakh fourteen" as 2,14,000 (v2.5 wrote 3,00,040 and 2,00,014). "Teen lakh chalis" is commonly said for 3.4 lakh (our judgement; a native speaker should confirm). If that is your intended reading, these 14 are defensible, so we report them apart from the 26. Is it intended?

## Isolation

The `verbatim` output of the same audio had the right number words in all 40 (91-100%). We cannot see inside your pipeline and do not know the cause. The `transcribe` text is not always the `verbatim` text with numbers converted (on single clips it added a "rupees" nobody said, merged "पाँच आए" into "पाए", and dropped a word), which hints at a separate decode, but we only know the `verbatim` words were right. No keyterms, topic or bias list was sent.

## Reproduce (about 2 estimated credits)

`eval/amounts_v2/repro_number_formatting.py`: one file, standard library only; set `GNANI_API_KEY` and run it. It voices 10 sentences with Timbre (8 skipped-group amounts no listener reads differently, and 2 controls; "X lakh Y" phrases are left out) and sends each clip to `POST /stt/v3` as `prisma-v3.0` `transcribe`, `prisma-v3.0` `verbatim` and `prisma-v2.5` `transcribe`, then prints the spoken amount, each transcript and ok or WRONG for the digits. That is 10 TTS clips and 30 STT requests, one at a time, about 2.1 credits by our estimates (0.002 per TTS character, 0.010 per STT second; not read from a dashboard, each possibly 20% off or more). In our stored run of these sentences all 8 skipped-group sentences were wrong and both controls right, in both audio conditions. We have not run the script live, so a fresh run may differ.

## What we do in the product

Samajh, a post-sale callback, takes two readings when a customer says a figure (v3.0 and v2.5 `transcribe`) and accepts the amount only if they agree. On a figure turn the dialogue holds the turn when they differ and reads back v2.5's figure to the customer, who confirms or corrects it. On the 280 synthetic clips agreement accepted 224 with no wrong amount, and on 124 public Hindi recordings 113 with none. On the synthetic set v2.5 alone also wrote none wrong, so there agreement adds only re-asks; on the recordings v2.5 alone wrote 4 wrong of 119 accepted, a small set and not a measured gain. v3.0 reads every customer turn; on those 124 recordings it refused 1 where v2.5 refused 5.

## What we did not establish

- The cause, or whether it is formatting or recognition.
- Any rate in real use (6 of 1,358 public utterances skip a group).
- Anything about real callers or phone lines. The clips are TTS plus 124 public recordings, of which 4 skip a group (v3.0 wrong on 1: too few for a rate); 107 of the 124 are from train splits you may have trained on.
- Other languages, streaming or `codemix`: not tested.
