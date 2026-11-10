# Idea hill-climb (5 rounds)

> **Note (2026-11-10).** The claims check in `references/claims/` supersedes parts of this file. Where this file differs from `references/claims/claims-ledger.md` or `references/claims/design-corrections.md`, those win. The lines affected are: the old instrument title in the 4A summary (Round 4), "No vendor offers 85Y callbacks" (Round 4 evidence), "recorded 'yes' and still lost" (Round 5 verdict), "₹2 lakh premium deducted from a CC loan" and the AHD-L-021-1617-0367 template (Round 5 gold templates). `DESIGN.md` v2 applies the corrections.

Each round: ~5 ideas across different voice-AI product types → one research agent per idea verifies claims (primary sources) → one persistent independent critic scores all ideas on the rubric and rules PURSUE / MUTATE / KILL → next round mutates or combines the top ideas and adds 1–2 new, unrelated ideas.

## Rubric (100)
| Criterion | Pts |
|---|---|
| Gnani / Indian voice-AI market fit (BFSI, lenders, telecom, insurance, contact centres; plugs into Gnani products) | 20 |
| Verified novelty (vs ~130 challenge entries, Gnani, Indian and global vendors) | 20 |
| Evidence of real demand (primary sources, a payer) | 15 |
| Feasibility for a 1–2 person build (concurrency 1, 5,000 credits, synthetic data only, no Agent Builder) | 15 |
| Measurability (gold standard, metric, honest failure cases) | 10 |
| Demo strength (one memorable moment) | 10 |
| Headroom / not too narrow | 10 |

Already explored: Pukaar (women's-safety follow-through, `references/dropped/pukaar-design.md`), Kasauti (RBI compliance red-team, `DESIGN-kasauti.md` — overlaps Maryada), the spoken-numbers/FASTag layer (dropped).

---

## Round 1 — scored by the critic

| Idea | Fit | Nov | Dem | Feas | Meas | Demo | Head | Total | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1A Flight recorder (why calls fail → replayable tests) | 15 | 9 | 9 | 9 | 5 | 6 | 9 | **62** | MUTATE |
| 1E Pronunciation QA (round-trip TTS→STT) | 9 | 10 | 4 | 11 | 2 | 5 | 6 | 47 | KILL — speech recognition masks mispronunciations (missed 46/110), so the core metric doesn't hold |
| 1B Synthetic call-data factory | 8 | 5 | 7 | 11 | 4 | 3 | 6 | 44 | KILL — Shaip/Defined.ai sell it; Gnani STT scoring Gnani TTS is circular |
| 1C Field-collections voice log | 11 | 4 | 3 | 10 | 7 | 4 | 4 | 43 | KILL — a 6-option form beats voice; Credgenics/Mobicule already do it |
| Pukaar (baseline) | 4 | 12 | 4 | 5 | 3 | 9 | 6 | 43 | stays dropped |
| 1D Voice banking for voice loss | 3 | 4 | 6 | 9 | 3 | 9 | 4 | 38 | KILL — ElevenLabs Impact Program offers it free, in 12 Indian languages |

Key competitor evidence: Roark, Hamming, Coval, Bluejay and Cekura already turn failed calls into tests; SuperBryn (Bengaluru) sells "why your voice agents fail"; Sarvam flags per-turn language changes but debugging is manual; Gnani Agent Analytics gives no failure reasons.

**Lessons:** (1) demand clusters in tools for agent builders and in BFSI compliance; (2) novelty must come from failure modes specific to India, not from the product category; (3) circular evaluation (scoring your own synthetic data with the same pipeline) keeps breaking the measurements — every idea needs an independent gold standard; (4) "why voice?" kills workflow ideas that a form handles.

**1A mutation:** an Indic voice-agent failure finder. Deterministic detectors flag a missed language switch, entity read-back mismatches, talk-over, dead air, "phir se boliye" loops and an ignored request for a human. Each failure is replayed with a cloned voice. Fix the circularity: honest agent configs (v2.5 vs v3.0, weak vs strong prompt) are run against self-recorded and real-voice callers, and failures are labelled blind by a person.

## Round 2 — scored by the critic

| Idea | Fit | Nov | Dem | Feas | Meas | Demo | Head | Total | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 2B Vernacular insurance pre-issuance verification call (teach-back vs policy schedule) | 19 | 9 | 13 | 12 | 8 | 8 | 7 | **76** | PURSUE |
| 2E MSME credit-interview (PD) copilot (deterministic consistency vs GST/bank/FOIR) | 17 | 10 | 11 | 10 | 9 | 8 | 8 | **73** | PURSUE |
| 2A Indic voice-agent failure finder | 15 | 9 | 7 | 8 | 4 | 6 | 7 | 56 | MUTATE — fold its detectors into 2B/2E as a self-audit |
| 2C Clone-attack test kit | 9 | 3 | 7 | 10 | 7 | 8 | 5 | 49 | KILL — the gnani-antispoof entry covers it; attacking Armour365 looks bad to Gnani |
| 2D Customer promise ledger | 6 | 2 | 9 | 10 | 6 | 7 | 6 | 46 | KILL — the Mock-On entry already built it |

Key evidence: IRDAI's Canara HSBC order (10 Sep 2026, ₹1 cr) calls the pre-issuance call "a critical regulatory safeguard"; a draft IRDAI paper lists 12 mis-selling practices; unfair-practice complaints rose from 23,335 to 26,667 (FY24→FY25). AuthBridge, Ringg, Artivatic and Signzy sell PIVC automation; Saakshi already showed Hindi/English teach-back during the sale. VideoCX, Lentra and Perfios sell AI PD (English/Hindi); no vendor claims a deterministic consistency engine.

**Lesson:** both leaders share one skeleton: *spoken claims → schema → deterministic diff against a document of record → timestamped mismatch*. The document supplies the gold standard, which fixes the circularity problem. Ideas that test voice systems keep hitting thin moats and circular evaluation.

**Leaderboard:** 2B 76 · 2E 73 · 1A 62.

## Round 2, batch 2F–2J — scored by the critic

| Idea | Fit | Nov | Dem | Feas | Meas | Demo | Head | Total | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 2F Dark-pattern auditor for AI sales calls | 16 | 11 | 7 | 12 | 6 | 8 | 8 | **68** | MUTATE into 2B — CCPA guidelines don't legally reach calls (cl. 2(1)(e): "user interface… on any platform"); rebuild as a check that consent was valid under RBI's conduct rules (effective 1 Jan 2027), keeping the pattern names as categories only |
| 2H Synthetic-voice labelling (IT Rules G.S.R. 120(E)) | 10 | 12 | 6 | 13 | 9 | 4 | 4 | 58 | KILL as a product; add to 2B (spoken AI disclosure + AudioSeal watermark, survival measured after G.711) |
| 2J Code-mixed call search | 11 | 9 | 3 | 12 | 8 | 4 | 4 | 51 | KILL — Prisma v3.0 transliterate/codemix removes most of the problem |
| 2G Nurse handover + ADR capture | 3 | 8 | 7 | 9 | 6 | 7 | 5 | 45 | KILL — Manipal generates handover from EMR data; Grapes BSA Pro sells nurse voice notes |
| 2I Gig-worker grievance desk | 2 | 6 | 7 | 9 | 6 | 7 | 5 | 42 | KILL — no buyer; the Act is under challenge in the High Court |

Round 3 interpreter idea (3C): KILL — Bank of Baroda's bob SAMVAD is deployed; `saathi` already verifies numbers after translation; `apni-awaaz` already clones voices.

Corrections to RESEARCH.md found along the way: the "no Indian nurse-facing voice tool" claim is false (BSA Pro); the Kerala handover study covers obstetric units observed in 2015; RB-IOS 2021 was replaced by the Integrated Ombudsman Scheme 2026 (from 1 Jul 2026); IPGRS takes phone complaints on 1902; Vigil (§5) is unverified.

**Leaderboard:** 2B 76 · 2E 73 · 2F 68 (merging into 2B) · 1A 62 · 2H 58 (add-on to 2B).

**Combination going to round 4:** a consent-and-understanding verification call for bank-sold third-party products. Teach-back is diffed against the policy schedule, explicit consent is recorded separately for each product (per the RBI rule; a bundled yes fails), and an optional scan of the sales call flags pressure. The bot plays the AI disclosure and carries a watermark.

## Round 3 — scored by the critic

| Idea | Fit | Nov | Dem | Feas | Meas | Demo | Head | Total | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 3A Insurance PIVC, sharpened | 18 | 10 | 11 | 12 | 8 | 9 | 7 | **75** | PURSUE, mutated — pre-call eligibility checks + script built from the schedule, plus a post-call auditor that diffs what *both* the caller and the customer said against the schedule (works on human, bot, or video-call audio) |
| 3B MSME interview copilot, sharpened | 16 | 9 | 7 | 10 | 6 | 8 | 8 | 64 | MUTATE — drop PD as the front end; its spoken-number work becomes the shared measured core |
| 3C Entity-locked BFSI interpreter | 10 | 2 | 7 | 9 | 7 | 8 | 5 | 48 | KILL |

Key evidence: PIVC is only "encouraged" (IRDAI/Life/Misc/CIR/116/05/2020 (12 May 2020), superseded by the Master Circular of 5 September 2024, para 31.1 item 27). Perfios, Signzy, AuthBridge and Artivatic do video or script-match PIVC; none claims a schedule-grounded diff. The Canara HSBC failure was **on the caller's side**: the caller said the annuity goes to the proposer (01:57) when the daughter was the annuitant; the proposer was 88 vs entry age 30–80; the phone number belonged to neither party. Canara used Artivatic. 270.22 lakh new individual policies in FY25. MSME delinquency is at a 5-year low of 1.8%. No benchmark exists for spoken lakh/crore/fraction amounts.

**Shared core:** a spoken-Indian-amounts benchmark (lakh/crore, dedh/sawa/saadhe/dhai, code-mixed amounts, Tamil/Kannada digits; v2.5 vs v3.0; self-recorded + Timbre at 8 kHz). It serves the product rather than being the product, and the gold labels come from construction.

**Head-to-head rule:** 3A wins unless round 4 finds *both* that the RBI clause doesn't cover bank-sold insurance *and* that a vendor already diffs PIVC calls against the schedule.

**Leaderboard:** 3A (+consent) 75 · 2F 68 (merged) · 3B 64 · 1A 62 · 2H 58 (add-on).

## Round 4 — scored by the critic

| Idea | Fit | Nov | Dem | Feas | Meas | Demo | Head | Total | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 4A RBI 85Y post-sale understanding callback for bank-sold third-party products | 19 | 14 | 12 | 12 | 8 | 9 | 9 | **83** | PURSUE (lead) |
| 4B Insurance PIVC auditor (schedule diff) | 18 | 10 | 11 | 11 | 7 | 9 | 7 | 73 | HOLD (fallback / headroom slide) |
| 4C Health-claim deduction explainer (mutated restart) | 11 | 13 | 9 | 10 | 9 | 7 | 7 | 66 | KILL — no payer, and the input is a document |

**4A in one line:** a callback run by a unit that doesn't sell, within 30 days of the sale (RBI RBC Second Amendment Directions 2026, para 85Y, in force 1 Jan 2027). It verifies the per-product consent already on record (85G); checks understanding with teach-back diffed against the product record; flags compulsory bundling (85V), a premium financed from the loan without consent (85W), and incomplete or misleading information (4(20A)); and outputs the refund case (85Z) plus input to the half-yearly report. It does not claim to capture consent, and leaves out 85X (UI-only). Hero case: a credit-life premium financed from the loan.

Key evidence: RBI/2026-27/115 (15 Jun 2026); parallel directions for NBFCs. No vendor offers 85Y callbacks or per-product consent checks. NuSummit, Krisp and GreyLabs are close to the PIVC auditor. Full list of IRDAI's 12 mis-selling practices found (consultation paper Box 5, pp. 61–62; ~8 detectable in a call). Prisma: v2.5 number formatting is hi/en only and not on Batch; v3.0 `format=transcribe` defaults to digits only for hi/en; Tamil/Kannada digits and fractions are undocumented. **[Superseded 2026-11-10: measured live, `format=transcribe` gives digits for Tamil and Kannada on both models (and v2.5 returns `output.literal`, the wording before formatting); some fraction forms were measured too. See `references/pilots/api-probe-iter1.md` §2.]**

**Final leaderboard:** 4A 83 · 3A/4B 73–75 · 2F 68 (absorbed into 4A) · 4C 66 · 3B 64.

**Round 5 (final):** verify 4A (85Y primary text + NBFC equivalent; vendors since June 2026; how banks plan to comply; why voice beats SMS; how common the hero case is; Ombudsman case studies as gold scenarios); verify the 4B fallback; a 2–3-week scope and credit plan. **Gate:** a 20-utterance amounts pilot on v2.5/v3.0 (needs the API key).

## Round 5 (final) — verdict

**BUILD 4A: the RBI 85Y post-sale understanding callback — 84/100** (Fit 20 · Nov 14 · Dem 11 · Feas 11 · Meas 9 · Demo 9 · Head 10). 4B: KILL (NuSummit already compares calls with policy terms; the 2020 PIVC circular appears repealed by the 2024 Master Circular).

**Verified basis.** 85Y (RBI/2026-27/115, commercial banks): "establish a mechanism to seek feedback from customers, within a period of 30 days from the sale of any financial product / service to ensure that customers have understood the features… and also the risks…"; call-backs or surveys by a non-sales unit, random sampling, plus a half-yearly report. Covers own and third-party products. Equivalents: NBFC 101Y (RBI/2026-27/123), SFB 85Y, PB 42Y, LAB 17Y, UCB 65Y, rural co-op 79Y, RRB 136Y, AIFI 32Y; HFCs via 157A. In force 1 Jan 2027. The added layer is mapped to 85G (consent), 85V (bundling), 85W (funded from the loan), 4(20A) (mis-selling) and 85Z (refund). No vendor found marketing it.

**Why voice (our own data must prove it):** Insurance Ombudsman awards where insurers held the customer's recorded "yes" and still lost (BNG-L-041-1617-0797, BNG-L-014-1617-0598, AHD-L-001-1617-0203). Headline experiment: **teach-back vs yes/no confirmation on the same scenarios.**

**Hero scenario** (re-creates BHP-L-021-1617-0529 with synthetic parties): ₹5,00,000 gold loan, ₹52,000 deducted for a policy, no consent record. The yes/no call passes; the teach-back call ("Bas ek FD, loan security ke liye, bavan hazaar") fails and flags 4(20A)(ii), 85W, 85G and an 85Z refund case, with the quote at 00:41.

**Other gold templates:** BNG-L-033-1617-0600 (policy as a "security deposit" for an overdraft → 85V); Baramulla v J&K Bank 2026 (₹2 lakh premium deducted from a CC loan); AHD-L-021-1617-0367 (Loan Protect bundled into the EMI → health-declaration teach-back); DHFL Pramerica (the recording said fund transfer, the customer paid by cheque).

**Award target:** Real Deal (backup: Demo Day Drop).

**Allowed claims:** quote 85Y verbatim; "no vendor found marketing an 85Y callback (Nov 2026)"; Ombudsman awards show yes/no calls failed; the consent/bundling checks are our added layer; only measured numbers with n and audio source; "flags for human review".
**Banned claims:** "RBI requires voice"; "85Y requires consent/bundling checks"; "captures consent" / "prevents mis-selling"; "this is mis-selling"; any mis-selling prevalence rate; 85X; "PIVC is mandatory"; Indian SMS-vs-voice response rates; TTS accuracy presented as real-world accuracy; "production-ready" / "nobody does this".

**Risks:** (1) credit cost unknown → day-1 pilot, pre-generate bot audio, REST turns, and the 2-week tier if cost per call > ~0.46 credits; (2) circularity → templates from awards, gold frozen with a hash, ≥20 improvised human calls, TTS vs human reported separately; (3) "SMS is enough" + Tamil/Kannada amounts → teach-back-vs-yes/no headline, deterministic lakh/crore/fraction normaliser + read-back, v2.5 vs v3.0.

**Open:** confirm the circular numbers against the PDFs; whether an open streaming session counts as the one active request. **[Superseded 2026-11-10: the circular numbers were confirmed against RBI's published directions (`references/claims/design-corrections.md`, "What held up"), and an open streaming session does not count as the one active request (`references/pilots/api-probe-iter1.md` §5).]**

**Full trajectory:** R1 best 62 (flight recorder) → R2 76 (insurance PIVC) → R3 75 (caller-side failure found) → R4 83 (RBI 85Y) → R5 84 (verified). 24 ideas evaluated by ~30 research passes and one critic.

## Gate result — amounts pilot (2026-11-10)
See `references/pilots/amounts-pilot-2026-11-10.md`. Naive digit-read accuracy: v2.5 phone 11/16, v3.0 phone 17/19, v3.0 clean 18/20. With a fraction-aware parser: 16/16, 18/19, 20/20. ITN leaves fraction words (sawa/saadhe/paune, Tamil/Kannada 1.5/2.5) before a converted base number, a systematic error that is fixable. One real miss (v3.0 dropped "paune" on the phone line) needs read-back. **Below 95% naive → amount accuracy + the parser/read-back fix becomes the second headline finding**, as the critic planned. Credit cost: ~0.02 credits per STT call, ~0.06 per TTS call; the full plan ≈ 180 credits (~4% of the budget). `DESIGN.md` v2 §8 gives about 230 to 265 credits for its four-language plan (about a quarter of the 1,000-credit project cap). Both figures are right for their own plans; the plans differ by about a third. Both rest on one dashboard reading with no saved screenshot.
