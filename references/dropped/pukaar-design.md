# [DROPPED] Pukaar — women's-safety distress agent design

> **Status: dropped 2026-11-10.** Kept for reference only. Reasons: RESEARCH.md §10b. Do not build from this without new evidence.

> A woman triggers distress with a few vague words. An AI agent turns them into a brief, calls her people and the helplines in parallel, in each person's language, and keeps calling until a human confirms they are coming.

Evidence: `references/helpline-evidence.md`. Eval data: `references/real-voice-datasets.md`.

## 1. Problem (verified facts only)

India's 112 took **10.89 crore calls in FY23** (Rajya Sabha Q192, 2023). MHA's own 2015 guidelines require answering within 15 s, abandoning < 5%, and **dedicated outbound staff to call back missed and dropped calls**. Nobody publishes whether that happens. Where CAG auditors looked, the follow-up step had failed:

- Karnataka 108 called back **3% of 55 lakh disconnected calls**; a pregnant woman whose call dropped was never called back and died (CAG 3/2020).
- Madhya Pradesh never set up its missed-call desk (CAG, 2015–20).
- Punjab 112 call-takers took **over 5 minutes to forward ~30% of emergencies**, and 181 is still not linked to 112 (CAG 2024).

Meanwhile police take ~18.6 min on average to reach a caller (MHA via Tribune, 2025), though that is improving. Family and friends are often closer than that, but an SMS with a location is fire-and-forget: nobody knows whether anyone read it or is going.

**The gap isn't "112 doesn't pick up." It's that no one owns the follow-through.** Pukaar is the outbound follow-up desk MHA planned, on the caller's side.

**Honest framing:** works alongside 112, never replaces it. 112 is called once with a clean brief, never on a loop (most 112 traffic is already blank/prank calls — adding robocall load would be harmful).

## 2. Users
- **Primary:** women travelling alone late (commute, cab, last-mile), and their families.
- **B2B (Gnani's market):** employers running women's night-shift transport, ride-hailing safety desks, insurers. *Unverified: state night-shift transport obligations — check before claiming.*

## 3. The loop

```
TRIGGER ──> BRIEF ──> FAN-OUT (waves) ──> CONFIRMED RESPONDER ──> LIVE UPDATES
  │           │            │                     │                     │
button /   speech →     per-contact          read-back of          she gets silent
code phrase  LLM →      call state           commitment +          "Mum coming, 8 min"
/ speech    schema →    machine              ETA                   responder gets
            validator                                              location updates
                                      └──────── EVIDENCE LOG (every step, timestamped, hash-chained) ────────┘
```

### 3.1 Trigger
- Button / power-key (the primary path — no speech needed).
- Covert code phrase during an app-placed fake call ("tamatar liye?").
- Speech: her description is the *input to the brief*, not the only way to trigger.

### 3.2 Brief
- Prisma (v3.0 `indic-auto` + `codemix`, `keyterms` for distress words and local landmarks; v2.5 as comparison) → transcript.
- LLM extracts into a strict schema:
  `situation` (enum: followed, harassed, attacked, unsafe_vehicle, medical, other) · `threat_level` (1–3) · `her_state` · `location` (GPS → nearest landmark, synthetic gazetteer) · `transport` (e.g. auto, cab with plate) · `time` · `raw_quote`.
- **Deterministic validator** checks types, enums, plate format, and which fields are missing. It never fills gaps. If it's safe, the agent asks one clarifying question; otherwise it proceeds with what it has, marking unknowns as "not known" in the spoken brief.

### 3.3 Fan-out
Each contact is a state machine:
`queued → dialling → (no_answer | answered) → briefed → (committed | declined | question ↺ | unclear ↺) → covered/standby`

Policy (configurable, pure function of state + clock):
- Wave 1: top family + nearest friends in parallel. Wave 2 after T seconds without commitment: next contacts + local police station desk. 112 / 181: one call with the brief.
- Severity 3 needs **two** committed responders.
- No-answer → retry with backoff; switch number if a contact has two.
- On commitment: others get a short "covered by X, please stay on standby" call.
- Gnani concurrency = 1: brief audio is generated **once per language** with Timbre and cached, so N parallel calls cost one TTS request per language. STT on responder turns goes through a single-flight queue.

### 3.4 The call
- Opens with: automated call on behalf of <name>, then the brief in the recipient's preferred language.
- Recipient can interrupt with questions; the agent answers **only from the brief + live location**, otherwise "not known".
- Intent: commit / decline / question / unclear (classifier on Prisma transcript).
- Commitment confirmed by read-back: "You're going to Silk Board, about 10 minutes — correct?"

### 3.5 Live updates
- Committed responder: location updates via a link / SMS (simulated in demo).
- Her: silent confirmation (vibration pattern + one line on lock screen).

### 3.6 Evidence log
Append-only, hash-chained JSONL: trigger, transcript, brief, each call event, each utterance, commitment. Exportable as an incident report.

## 4. Telephony
- **Demo:** simulated phones in the browser (each contact is a tab with a ringing UI, audio over WebRTC) + simulated 112 / 181 / police desks. Optional real calls to consenting teammates via Exotel/Twilio, numbers blurred.
- All IDs, numbers, plates and addresses synthetic and obviously fake.

## 5. Evaluation
| # | Question | Metric | Data |
|---|---|---|---|
| E1 | Does STT catch distress words and landmarks in noise? | keyword recall, WER; by SNR (clean, 10, 5, 0 dB) and 8 kHz; v2.5 vs v3.0; with/without `keyterms` | IndicVoices solo + Kathbath noisy (real voices) + MUSAN/DEMAND mixes; Timbre-generated triggers |
| E2 | Is the brief right? | per-field accuracy, missing-field detection rate, hallucinated-field rate | ~100 synthetic scenarios with gold briefs, spoken by multiple Timbre voices + noise |
| E3 | Does the agent read the responder correctly? | commit/decline/question/unclear F1; false-commit rate (the dangerous error) | synthetic responder utterances (Timbre) + real-voice clips where applicable |
| E4 | **How fast does a human commit?** | time to first confirmed responder; % incidents with no responder in 5 min | simulator: contacts with answer probability, delay, language; Pukaar vs sequential calling vs SMS-only |
| E5 | Does the listener get the location? | location read-back accuracy | read-back test on E2 briefs |

Report failures honestly, including: TTS-on-TTS flatters E1/E2; not tested on real distressed or whispered speech (no such public data exists); E4 depends on assumed answer rates — show sensitivity.

## 6. Gnani models used
Prisma STT v2.5 and v3.0 (REST for short clips; WebSocket streaming for live calls), Timbre TTS v2.5/v3.0 (audio tags in v3.0). Voice cloning: not used (an AI speaking in her voice to her family would confuse and mislead). LLM: any (reasoning only — no arithmetic, no field invention).

## 7. Open decisions
1. Stack: Python (FastAPI) backend + web frontend? (Recommended — Gnani WebSockets need a backend proxy anyway.)
2. LLM provider.
3. Real telephony in v1, or simulated phones only?
4. Languages for v1 (suggest Hindi/Hinglish + one regional: Kannada or Tamil).
