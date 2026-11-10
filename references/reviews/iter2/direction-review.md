# Samajh: independent direction review (2026-11-10, read-only)

**Verdict.** The evidence behind this entry is probably among the strongest in the field. What a judge will actually see is not there yet: no video, no human voice on the phone, and the Gnani finding does not appear on the screens a judge would look at. On the written evidence I expect it to be a contender in Jugaad Genius and a credible but crowded runner in Real Deal. If the 60-second video goes out showing only Timbre voices, it risks reading as "a very careful prototype nobody has spoken to". Two risks sit outside the build. Nobody knows the closing date or the engagement cutoff (USER-GUIDE.md:23, :177). Internships are filtered on engagement before any interview (RESEARCH.md:48). Most of tonight's gain comes from making the existing evidence visible and settling those two facts, not from more rigour.

**1. Award fit.** I disagree with the team's choice of Real Deal as primary (DESIGN.md:267, judge.md:121). Real Deal is judged on usefulness for a real-world problem, and the award's own examples are farmers, kirana shops and rural health workers (RESEARCH.md:36-44). Against roughly 100 social-impact entries, a lender's compliance callback that no person has used is a hard sell. Jugaad Genius ("most creative use of Gnani's models") is the category whose criterion is this entry's best verified asset: v3.0 and v2.5 read against each other as the confidence score Prisma does not return, the verbatim output used to isolate the fault, and Batch used for audio offsets. What each still needs:
- **Jugaad Genius:** the two readings must be visible in the product and the video. Today they are kept in the case file (`samajh/server/casefile.py:87-91`, `readings_agreed`), but `web/review/review.js` never renders them, and the phone shows them only in a turn-detail panel (`web/phone.js:604-608`).
- **Real Deal:** human callers (P4) and the borrower framing.

My recommendation: write the submission so the first two lines meet the Jugaad criterion and the next two meet Real Deal. Name Jugaad Genius as the target unless P4 lands with good results.

**2. Gnani fit.** Use of Gnani is deep, specific and measured: exact versions, behaviour where live differs from the docs, the per-account one-request limit, streaming rejecting a language list in 13 of 13 attempts, and a 2-credit reproduction script (`eval/amounts_v2/repro_number_formatting.py`). It is now in the call path, too (P1: two readings on figure turns, Batch offsets on the case page). What a Gnani engineer would find most convincing:
- the matched controls (40 of 68 against 0 of 68);
- the isolation: verbatim right on all 40 (verify-P6.md, Claims table).

What they would find least convincing:
- **Gnani TTS scored by Gnani STT.** The project killed idea 1B for exactly this circularity (IDEAS-HILLCLIMB.md:28). Only the 124 public clips answer it, and they are mostly from train splits.
- **"Why not just use v2.5 for figures?"** On the held-out phone set, v2.5 alone was wrong 0 times and accepted 268 of 280. The agreement rule accepted 224 of 280 (verify-P6.md, Claims table), so on synthetic data the second model adds re-asks and no measured accuracy. The case for agreement rests on the real clips: v2.5 alone was wrong on 4 of 124, agreement on 0 of 113 accepted (tables-realvoice.md:17). The submission must say this, or the rule looks over-engineered.

Framing: leading with "v3.0 writes wrong amounts" reads as an attack. Lead with a regression between versions: "v2.5 handles these; v3.0 `transcribe` regressed on skipped-group amounts; verbatim is right; here is a 2-credit reproduction; here is how we use both of your models together". Lead with the 26 unambiguous cases, not "teen lakh chalis" (verify-P6.md finding 2). Inferred: send the report to Gnani privately (Discord) before any public post. The finding then reads as a gift rather than a public call-out.

**3. Buyer fit.** A compliance head at an NBFC would see a product in the case page. It puts record against quote, gives audio offsets and the paragraph each finding may engage, uses neutral decision labels, and says nothing is a finding (p3b-artifacts/phone-case-1280-light.png). Inferred first objection: "You are manufacturing recorded evidence that we mis-sold, which triggers 85Z refunds. Why would I create that, and how many cases land on my team per 100 calls?" The repo half-answers it:
- the 85Y half-yearly report is mandatory, so findings exist anyway (DESIGN.md §2);
- a flag is never a finding (claims-ledger X2);
- the reviewer load is shown only on a simulated book with an assumed customer mix (the ops demo I ran: refer 7 of 64, `understanding_gap` 33 of 64).

Nothing answers cost per completed call or reach on real customers. Cost per call is cheap to state (item 7 below).

**4. Against the field.** Real edge:
- a vendor-specific fault measured against matched controls, isolated, mitigated in the product and independently reproduced;
- a deterministic comparison with the record, with grounded quotes;
- the 85Y report artifact.

Merely equal:
- *Measuring Prisma.* Rythu Vaani, SHOR and kirana-bol benchmark it too (RESEARCH.md:153; challenge-entries json).
- *RBI framing.* Maryada already cites RBI conduct rules.
- *Ordinary features.* A browser phone with mocked telephony (most entries), a Hinglish loop, and LLM extraction.
- *Understanding checks.* SquadStack, Edesy and Ringg already market them (claims-ledger S3).

Behind: no real phone line (Polyglot uses SIP; RevClaim uses Twilio and LiveKit), no barge-in, and microphone latency measured only on yes/no turns (n = 4).

**5. Overbuilt and underbuilt.** Overbuilt, meaning more rigour than any judge will see:
- 4,443 tests;
- a 440-span claims ledger;
- the Wilson and McNemar statistics;
- the 17-outcome reach funnel;
- an 8,700-px half-yearly report page with per-branch interval tables;
- frozen-set hashes;
- Tamil and Kannada code.

Keep all of it as backing, and put none of it on screen. Thin where a judge looks:
- no video;
- the name is still a "working name" (DESIGN.md:1; decision 3);
- the README's first screen is a status table of caveats;
- the Gnani signal is missing from the reviewer page;
- nobody has heard the bot's voice;
- the prepared demo calls stop with `script_drift` until re-voiced (README, "Run the phone").

From the offline call I played (hi-en), two glitches:
- the Hinglish read-back says "fifty two thousand rupees" in English;
- a customer who repeats "52,000 दिए थे" at the read-back is asked again instead of being taken as confirming.

**6a. Tonight: eight changes of under an hour each, ranked**
1. **Read the closing date, the submission steps and the engagement cutoff** off gnani.ai/internship (the user, 10 minutes). No risk, and everything else depends on it.
2. **Render both readings on amount quotes**, on the case page and the phone's case card: "Prisma v3.0 ₹52,000 · v2.5 ₹52,000 · agreed → read back, confirmed". Files: `web/review/review.js`, `web/phone.js`, and `samajh/ops/views.py` if the view lacks the field. Low risk, but it touches the P1 and P3b lanes, so coordinate with those owners.
3. **One prepared demo call with a disagreement.** The customer says a retail skipped-group premium such as "दो हज़ार बारह" (v3.0 wrote 2,000 on the held-out set). v3.0 and v2.5 disagree, the bot re-asks, then reads back. Use `samajh.server.prepare` plus replay, about 5-10 estimated credits. Medium risk: it needs the single Gnani slot free, and v3.0 may read this clip correctly. Then pick a clip the cache already shows as wrong.
4. **Make the first screen of the README judge-first:** one sentence, the case-page screenshot, three numbers in verify-P6 wording, the exact models, two run commands. Caveats go below. Low risk.
5. **Put the Gnani report in the repo** (`references/pilots/gnani-number-formatting-report.md`, awaiting the user's go-ahead). Retitle it as a v3.0-vs-v2.5 regression, lead with the 26 unambiguous cases, and add the "why not v2.5 alone" paragraph from §2. Low risk.
6. **Fix the name** (DESIGN.md §15 item 3) so the video and the title can be made. 5 minutes.
7. **State the cost per completed call:** Gnani credits from the P1 hero session's ledger rows plus $0.0017 of LLM per transcript (DESIGN.md §7). Mark the credits as estimates. Add it to the README and the brief. Low risk.
8. **Add the two read-back glitches from §5 to the user's wording review** (P2-lines-for-review.md) as notes, not code edits, while P2 awaits verification. No risk.

**6b. Next days (at most five)**
1. **P4 first.** Run 20 improvised Hinglish and Hindi calls, each with a natural amount turn, at least a few of them skipped-group. This could give the first real-voice instance of the fault inside the product, and set the end-of-speech thresholds.
2. **A smaller P5 if time is short.** About 60 voiced persona calls with the matched closed arm, reported per 100 by kind of customer. Credits allow it.
3. **The 60-second video** to the judge's plan (DESIGN.md §10), with the user's own voice and the disagreement moment from item 3. Show the report page's top table only.
4. **The written submission:** exact models (Prisma v3.0 and v2.5 via `/stt/v3` REST, Prisma Batch, Timbre v3.0), the adjacent vendors named with what Samajh adds, each member's contribution, and a final run of `check_quotes.py` plus a recheck of RBI amendments.
5. **Post early on both LinkedIn and X** and nominate one link per platform. Only engagement before the cutoff counts towards internships. Send Gnani the reproduction privately first.

**Not read:** RESEARCH.md §§6-11 in detail, the P1/P2/P3a reports and contracts, DESIGN.md §11, §13 in part and §15 in part, the full claims ledger rows (Part 2), any other entrant's repository (I used only the catalogue, dated up to 6 Nov), and any code beyond grep and the two offline commands. "Inferred" marks judgements about judges and buyers.
