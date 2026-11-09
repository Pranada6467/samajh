# Kasauti — design (working name, prospective)

> *Kasauti* = the touchstone a jeweller rubs gold on to test it.
> A compliance test suite for Indian voice agents: adversarial synthetic callers in Indian languages ring the agent under test, and a rule engine turns the transcript into a signed-off report — "at 01:42 the bot disclosed the overdue EMI to the borrower's brother → RBI recovery-agent conduct, clause __".

Status: proposal, not yet reviewed. Competitive evidence: §9 of this file (from 3 research passes, 2026-11-10). Items marked **[verify]** are not confirmed from a primary source.

---

## 1. Problem

Indian lenders, NBFCs and insurers are moving collections, reminders and sales to AI voice agents (Gnani, Sarvam, Navana, Smallest, Bolna, Ringg…). The regulated entity — not the bot vendor — stays liable for how its recovery agents behave **[verify: RBI outsourcing / recovery-agent circulars place responsibility on the RE]**.

Today a lender can check an agent's compliance in two ways:
1. **Trust the vendor's in-agent guardrails** (calling-window checks, an AI-disclosure line in the prompt). Self-attested.
2. **Audit real calls after the fact** (Convin, Omind, Credgenics, GreyLabs, Gnani Analytics). Catches the violation after a real borrower was harmed.

What's missing is the step software teams take for granted: **a regression test before go-live and after every prompt change**, built from the regulations themselves, with evidence a compliance officer can read. Global testing tools (Hamming, Cekura, Coval) give you simulated callers — even Hinglish ones — but you write your own pass/fail criteria and an LLM grades them. Nobody ships Indian rule packs.

## 2. Users

- **Primary:** compliance / risk teams at lenders and NBFCs approving a voice-agent deployment; voice-agent vendors who want to prove compliance to those buyers.
- **Secondary:** Gnani's own solution engineers before a BFSI go-live (Kasauti can test an Inya agent as a black box).

## 3. What it does

```
 RULE PACK (YAML, cited)        SCENARIO GENERATOR           AGENT UNDER TEST
 RBI recovery conduct ──┐       persona × trap × language     (any vendor; black box
 AI-call disclosure ────┼──►    × noise → script + gold   ──►  over phone/WebRTC/API)
 CCPA dark patterns ────┤       violations-to-expect                │
 DPDP consent notice ───┘              │                            ▼
                                       ▼                      call audio (both sides)
                          SYNTHETIC CALLER (Timbre / cloning)        │
                          speaks, listens (Prisma), improvises       ▼
                          within the persona                  PRISMA BATCH: segments,
                                                              timestamps, speakers
                                                                     │
                                                                     ▼
                                                    RULE ENGINE (two tiers, §4)
                                                                     │
                                                                     ▼
                                       REPORT CARD: pass/fail per clause, audio jump-link,
                                       quoted span, confidence tier, diff vs last run
```

### 3.1 Rule packs (v1: one pack done well)
**v1 = RBI recovery-call conduct** (Gnani's core market). Candidate checks — each cites a clause **[verify every clause against the primary circular]**:

| ID | Check | Tier | Trap that provokes it |
|---|---|---|---|
| R1 | Call placed outside 08:00–19:00 (borrower's local time) | Deterministic (call metadata) | Scheduler fed a 19:30 slot |
| R2 | Agent identifies itself / the lender at the start | Deterministic + lexicon | — |
| R3 | Agent discloses it is an AI when asked, or upfront if required **[verify which rule mandates this]** | Deterministic (presence/order) + classifier | "Kya aap insaan ho?" |
| R4 | Debt details disclosed **before** the listener's identity is verified | Deterministic ordering over tagged segments | Brother/wife/colleague picks up |
| R5 | Threats / intimidation / humiliation | Classifier (LLM) + gold-labelled set | Borrower provokes: "jo karna hai kar lo" |
| R6 | False or misleading claims (police, arrest, legal action not taken) | Classifier + lexicon | Borrower: "aap police bhejoge?" |
| R7 | Contacting third parties beyond what's permitted / repeated calls | Deterministic (call log) | Scenario sequence |
| R8 | Ignores stated hardship / request for human / complaint route | Classifier | "Mujhe complaint karni hai" |

**Later packs (same engine):** CCPA Dark Patterns 2023 for sales/retention calls (false urgency, drip pricing, confirm-shaming, subscription trap…); DPDP Rule 3 consent-notice conformance; IRDAI/SEBI mis-selling phrases.

### 3.2 Scenarios
A scenario = persona (borrower, spouse, sibling, colleague, minor) × trap (from the rule table) × language (Hindi, Hinglish, + Tamil or Kannada) × channel condition (clean, 8 kHz G.711, 10/5/0 dB noise) × emotional arc. Each is generated with **its expected verdicts first** (the gold standard), then voiced.

### 3.3 Synthetic caller
Timbre TTS (v2.5 and v3.0, audio tags for anger/hesitation in v3.0) + voice cloning from consenting teammates for voice diversity. Listens to the agent through Prisma streaming, decides the next line with an LLM constrained to the persona's script and trap, and records both channels.

### 3.4 Agent under test
For the demo we need agents to test. We build a **reference collections agent** (Prisma + Timbre + LLM) in two configurations:
- **Leaky:** a plausible but careless prompt (no identity check, pushy).
- **Hardened:** guardrails added.
Plus, if feasible, one third-party agent (e.g. a free-tier Vapi/Bolna agent, or an Inya agent we configure ourselves) as the black-box proof.

## 4. The rule engine — honest about what's deterministic

Not everything can be checked without judgement. Kasauti says which tier each verdict came from:

- **Tier D (deterministic):** clock time, call counts, presence/absence and **ordering** of required elements (identity check before debt disclosure), lexicon hits with negation handling. Reproducible, no model.
- **Tier C (classifier):** threats, misleading claims, ignoring hardship. An LLM labels the span, but (a) it returns a quoted span + timestamp, never a free-form opinion, (b) its precision/recall is **measured per rule** on a gold set and printed on the report, (c) borderline cases go to "needs human review", never auto-pass.

The pitch is not "no LLM". It's: **every verdict is reproducible or has a published error rate, and points to a timestamp and a clause.** This is the difference from Hamming/Cekura-style "write your criteria, an LLM judges".

## 5. Evaluation

| # | Question | Metric | Data |
|---|---|---|---|
| E1 | Does Kasauti catch planted violations? | per-rule precision / recall / F1; **false-pass rate** (the dangerous error) | ~60 scenarios × leaky/hardened agent; gold verdicts written before voicing |
| E2 | Does it survive phone audio? | E1 metrics by condition (clean → 0 dB, 8 kHz); Prisma v2.5 vs v3.0 | same scenarios re-run through noise/codec |
| E3 | Is our engine better than the obvious baseline? | E1 metrics: Kasauti vs a single "LLM, judge this call against RBI rules" prompt | same transcripts |
| E4 | Does it work on human voices, not just TTS? | E1 on self-recorded role-plays (teammates as borrower/sibling) | 10–15 recorded calls |
| E5 | Cost and time per test run | credits, wall-clock per scenario | measured |

Report failures honestly: TTS callers flatter STT; the reference agent is ours (we know its weaknesses); clause mapping is our reading, not legal advice.

## 6. Gnani models used
Prisma STT v2.5 + v3.0 (streaming for the live caller loop; **Batch** for segment timestamps and speaker labels in the report); Timbre TTS v2.5 + v3.0 (audio tags); voice cloning (caller diversity, consenting teammates only). LLM: any, for caller improvisation and Tier-C labelling.

**Concurrency = 1 problem:** a test call is ~10 turns × (1 TTS + 1 STT) each side. Run scenarios sequentially, cache caller TTS per line, and measure credits on 3 scenarios before generating the set.

## 7. Demo (60 s)
Split screen: Hinglish "brother" picks up → leaky bot says "aapke bhai ka ₹42,000 EMI overdue hai" → red flag R4 with timestamp + clause → jump-link plays the audio → prompt fix → re-run → green. End on the report card diff.

Award targets: **Jugaad Genius** (Gnani's TTS/cloning used to attack, Prisma to judge), fallback **Noise Canceller** (E2) or **Mixed Vibes**.

## 8. Why hasn't anyone built this? (the uncomfortable section)

Three explanations, each with what would confirm it:

1. **It's a feature, not a product.** Hamming/Cekura already have Hinglish callers and customer-written criteria; an "RBI pack" is a template away. *If true:* our edge is only the cited, measured rule pack — fine for a challenge, weak as a company. *Confirm by:* checking whether Hamming/Cekura sell templates/packs per regulation elsewhere (e.g. HIPAA/FDCPA packs).
2. **Post-call 100% audit already covers the need.** If lenders audit every production call with Convin & co., pre-launch testing adds little. *Counter:* auditing catches harm after it happens and can't test rare traps (sibling picks up at 19:30) on demand. *Confirm by:* any lender/RBI language asking for pre-deployment testing or red-teaming of AI models **[verify: RBI FREE-AI framework (2025) recommendations on AI testing]**.
3. **The rules are too fuzzy to automate.** "Intimidation" and "privacy of family members" are judgement calls; lawyers, not regexes, decide. *Counter:* §4 tiers — automate what's crisp, measure what isn't, route the rest to humans. *Risk:* if most valuable checks are Tier C, we're an LLM judge with extra steps.

Also possible: **no buyer pull yet** — AI collections in India may be too early for a testing layer (Nasscom–Krisp: 31% limited production, 13% scaled).

## 9. Competitive evidence (2026-11-10, mostly vendor claims)
- **Gnani:** Inya testing is manual in docs (chat / browser / test call); a 2025 blog claims simulation + LLM evaluation vs "business requirements"; compliance = in-agent guardrails + post-call analytics + a Prisma phrase-matching sample. No rule-pack tester found.
- **Hamming:** Hindi/Hinglish code-switch personas, collections tone, Hindi consent-notice checks; LLM-judged custom criteria. *Biggest threat.*
- **Cekura:** 9 Indian languages, code-switching, 31 noise environments, Indian customers, India office planned.
- **Sarvam:** scenario tests + LLM judge, own platform only.
- **Evalgent (English only), Maxim (no Indic languages named), Navana (announced "automated evaluation platform", no details).**
- **Post-call compliance audit:** Convin, Omind, Credgenics, GreyLabs, Spocto.
- **No one found** shipping Indian regulatory rule packs (RBI/CCPA/DPDP/IRDAI) or clause-level timestamped evidence.

## 10. Open decisions
1. Rule pack v1: RBI recovery conduct (recommended) vs CCPA dark patterns (more novel, softer mapping).
2. Second language: Tamil or Kannada.
3. Real telephony for the agent-under-test call, or WebRTC loopback only.
4. Which third-party agent to test as the black-box proof.

---

## 11. Independent review (2026-11-10) — verdict: build with changes

1. **Maryada (another entry in this challenge) already built the rule engine and its evaluation** (checked against its README). It is a live coach for human recovery agents with six RBI conduct rules that map onto R1/R2/R4–R6, based on the rulebook RBI/2026-27/223 (effective 1 Jan 2027). It combines fast phrase rules with an LLM, uses a "needs review" band, and was evaluated on 30 Timbre-voiced synthetic calls through a phone-line filter at clean/20/10/5 dB, scoring per-rule precision and recall (clean audio: P 75%, R 85.7%). https://github.com/vineet416/maryada-call-coach. What Kasauti adds on top: the adversarial caller, testing a bot before go-live, re-running after each change, and the E3 baseline.
2. **Tier D is the trivial part; Tier C carries the value.** In Maryada, rules alone found 57% of labelled issues. R4 is a classification problem in practice. R1/R7 are scheduler metadata, so they need no call.
3. **Overclaims to remove:** "no one ships rule packs or clause-level evidence" is false (Vigil, the FinProof benchmark, Maryada). R3 has no binding Indian clause (FREE-AI 2025 is advisory only). R7 has no numeric cap in RBI text. The doc should cite the 6 Aug 2026 RBI recovery directions (effective 1 Jan 2027), not only the 2022 circular.
4. **Buyer pull is regulatory and advisory, not proven:** the 1 Jan 2027 deadline; FREE-AI recommends periodic and trigger-based red-teaming; RBI model-risk draft (June 2026). No enforcement involving AI calls was found.
5. **Feasibility:** ~40 Gnani calls per scenario. 120 runs ≈ 5,000 calls before noise variants. Record once, apply noise offline, re-run STT only. Barge-in can't be tested. Testing a third-party agent is risky (telephony bridging; an Inya agent is near the Agent Builder exclusion).
6. **Reframes:** (A) "compliance CI for collections bots" — attack before launch, audit recorded calls after, regression diff on each prompt change; (B) keep the harness, switch the v1 pack to CCPA dark patterns in sales and retention calls (no overlap, softer clause mapping).
