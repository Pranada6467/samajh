# Gnani Voice AI Challenge — Research Notes

Everything explored while preparing for Gnani AI's *Great Indian AI Internship Challenge*: the challenge itself, Gnani's products, the Indian voice-AI market, what other entrants built, what wins hackathons, and every idea direction we evaluated (including the ones we dropped and why).

Conventions:
- **[V]** = vendor's own claim, not independently verified.
- "Confirmed / Weakened / Refuted / Unverified" = result of an independent fact-check pass.
- Sources are linked inline. Key reference files are in `references/`.

---

## 1. The challenge

**Organiser:** Gnani AI (Bengaluru voice-AI company). **Theme:** build sovereign AI for India on Gnani's models/APIs.

**Brief:** open — any *working* application built on at least one Gnani model or API.

**What a submission needs**
- A working app, shown in a public demo video.
- Video posted on LinkedIn and/or X, tagging Gnani AI with `#GnaniAI` and `#GreatIndianAIInternshipChallenge` (Gnani's own later posts sometimes drop "AI" from the hashtag — use the one in the rules).
- Written explanation: project title, problem, target users, Gnani models/APIs used, each member's contribution.
- One nominated post link per platform.
- Solo or team of two; Indian college students, 18+.

**Rules that shape the build**
- **Synthetic data only.** No real phone numbers, account numbers, Aadhaar, PAN, or recorded calls.
- The **Agent Builder is out of scope** (no APIs for it).
- 5,000 programme credits per registration (team credits go to the primary registrant); 3 API keys per participant.

**Prizes**
- Up to 100 paid six-month internships (stipend up to ₹1 lakh/month, individual).
- Ten awards of ₹50,000; one award max per team:

| Award | What wins |
|---|---|
| Main Character | Regional or low-resource Indian language |
| Mixed Vibes | Code-mixed voice (Hinglish, Tanglish, Benglish) |
| Real Deal | Most useful real-world problem (farmers, kirana, rural health workers…) |
| Noise Canceller | Noisy, real telephonic audio |
| Two-Person Army / Solo Ninja | Best team of two / best solo |
| Jugaad Genius | Most creative use of Gnani's models |
| Small Town, Big Build | Tier 2/3 college or city |
| Demo Day Drop | Best 60-second demo video |
| Crowd Favourite | Public votes on LinkedIn/X |

**How internships are selected:** verified engagement on nominated posts (only engagement recorded by the closing cutoff counts) → eligibility check (genuine use of Gnani tech) → individual interviews → written offers based on skills and role fit. Awards are judged separately on category criteria.

**Gnani's starter ideas (non-binding):** Kannada crop/weather helpline; Hinglish kirana phone-ordering; noisy call summariser; Tamil voice tutor.

Sources: [gnani.ai/internship](https://www.gnani.ai/internship), [challenge blog](https://www.gnani.ai/resources/blogs/great-indian-ai-internship-challenge-2026), [CXOToday](https://cxotoday.com/media-coverage/gnani-ai-launches-the-great-indian-ai-internship-challenge/).

---

## 2. Gnani AI — models, APIs, products

### Models and APIs (what we build on)
| Model | What it is | Key details |
|---|---|---|
| **Prisma** (STT) | Speech-to-text | **v2.5:** you set the language; number formatting (Hindi/English only); `bias_list` word boosting (≤100 letters-only words); 10 find-and-replace rules. **v3.0:** auto language ID, code-mixed speech, `keyterms` (≤200), topic/name hints, writes digits in all 10 languages. Delivery: REST (clips ≤30 s), WebSocket streaming (sessions ≤15 min), Batch (long files, per-segment timestamps, speaker labels up to 8, denoising). Claims #1 in 8/9 languages on noisy 8 kHz [V]; trained on 14M+ hours of telephone audio [V]. |
| **Timbre** (TTS) | Text-to-speech | v2.5 (beta) and v3.0; streaming via SSE/WebSocket; audio tags for expressive delivery (v3.0); normalises numbers, currency, dates, IDs into speech. |
| **Voice cloning** | Cloned-voice TTS | Embeddings from an audio sample; REST, SSE and WebSocket output. |
| **Warp** | Speech-to-speech | 5B-parameter model; appears to be what press called *Inya VoiceOS*. |
| **Evon v3.3** | LLM | 30B mixture-of-experts, open weights (Apache 2.0, by request on Hugging Face). **Not on the API** — use any LLM for reasoning, or self-host. |

**API realities to design around**
- No confidence scores and no word timestamps on REST/streaming responses — confidence must come from validation and read-back.
- 429 `RATE_LIMITED` errors; docs show "1 active request" as an example limit. Queue requests one at a time with backoff.
- Per-call credit cost is not documented — measure it early.
- API host is `api.vachana.ai`; auth header `X-API-Key-ID` (browsers can't set it on WebSockets → use a backend proxy).
- **Not supported:** Odia, Assamese, Bhojpuri.
- The challenge page names Prisma v2.5 / Timbre v2.5; v3.0 shipped later and many entrants use it. Rules say "any Gnani model or API" — safest to run both and report both.

Docs: [docs.gnani.ai](https://docs.gnani.ai) · [llms.txt index](https://docs.gnani.ai/llms.txt) · Platform: app.gnani.ai/voice · Community: Discord (official updates now go there).

### Gnani's business (enterprise products)
Gnani is mostly **not** an API company — the APIs are the newer developer layer. Revenue (~₹54 cr FY25, profitable [V]) comes from enterprise products:

| Current name | Old name | What it does |
|---|---|---|
| **Agents** | Automate365, Collect365 | Voice/chat agents for collections, customer service, KYC, HR, operations |
| **Analytics** | Aura365 | 100% call coverage: sentiment, insights, real-time quality and compliance |
| **Biometrics** | Armour365 | Voice authentication (no PIN), anti-spoofing, deepfake detection |
| **Assist** | Assist365 | Live help for human agents: knowledge retrieval, coaching, scoring |

Platforms: **Inya** (agent builder), **Plexus** ("agentic AI workforce", early access), **Artha** (sovereign stack for government/regulated sectors).
Industries: BFSI, healthcare, automobile, real estate, hospitality, consumer durables, government, BPOs, telecom, insurance.
Named clients [V]: Bank of Baroda (biometrics), LazyPay, KreditBee, Hero FinCorp, Mahindra Holidays (collections), HDFC, Airtel, TVS Credit, Indian Bank (logos).

Sources: [gnani.ai](https://www.gnani.ai/), [/enterprise](https://www.gnani.ai/enterprise), [/solutions](https://www.gnani.ai/solutions), [/models](https://www.gnani.ai/models), [Artha](https://gnani.ai/artha-sovereign-ai), [Armour365 launch](https://www.businesswireindia.com/gnaniai-launches-armour365-voice-biometrics-software-based-on-patented-technologies-75022.html).

---

## 3. The Indian voice-AI market

### Players
| Player | What they do | Signal |
|---|---|---|
| Gnani | Full stack: models, agents, analytics, biometrics | ~₹54 cr revenue, profitable [V] |
| Sarvam | Models + Samvaad agents; best independent Indic ASR scores | ~$12M run rate [R]; Tata Capital, SBI Life (pilot), Swiggy (demo), Ministry of Agriculture |
| Navana | BFSI voice agents | Bajaj Finserv, Ujjivan, Jana SFB; 100M+ minutes [R] |
| Smallest.ai | Models + agents, global contact centres | RingCentral, Truecaller [R] |
| Yellow.ai | Omnichannel; Nexus Vox voice | ~$35M revenue, flat |
| Bolna | Voice orchestration | Spinny, Snabbit; ~200k calls/day |
| Exotel / Ozonetel | Telephony layer + voice bots | — |
| Reverie, CoRover, Bhashini, NPCI Hello! UPI | In-car voice, IRCTC AskDISHA, govt language stack, voice UPI | — |
| Global (for scale) | ElevenLabs (>$500M ARR), Deepgram, AssemblyAI, Vapi, Retell, PolyAI, Sierra, Coval (voice-agent testing, $28M) | Indian players are small by comparison |

### What's actually in production
1. **Loan collections / payment reminders** — the most proven use case; Gnani's core.
2. **Lead qualification / outbound sales.**
3. **Call QA and compliance analytics.**
4. Inbound L1 support — mostly pilots.
5. Voice ordering — mostly hype (Swiggy was a demo).
6. KYC/voice biometrics and govt helplines — real but narrow.

Industry survey (Nasscom–Krisp): 31% of Indian firms in limited production, 13% scaled.

### What buyers want
- Accuracy in Indian languages and code-mixing on **noisy 8 kHz phone audio** (63% rank language accuracy in top-3 priorities).
- Correct numbers, names, amounts (a recognised weak spot).
- A path to a human (Gartner: 87% of customers want one — not re-verified).
- Compliance: RBI recovery-call hours (8 AM–7 PM), AI-call disclosure, IT Rules on synthetic audio, data-protection (DPDP) consent rules, SEBI/AMFI/IRDAI selling rules.
- Data sovereignty, low cost per minute, voice-agent testing tools.

### Where products are heading
Speech-to-speech models; agents that take actions; sovereign/on-prem stacks; voice analytics; testing/evaluation tooling. Regulated buyers still prefer cascaded pipelines (STT → LLM → TTS) because they're auditable.

### The full map of voice-AI use cases (beyond "replace the call-centre agent")
- **AI talks:** support, collections, sales, verification calls, surveys, reminders.
- **AI listens:** call QA, compliance auditing, speech analytics, voice biometrics, fraud/deepfake detection.
- **AI assists a human:** live agent assist, handoff with summary, training role-play.
- **Voice in products:** in-car, set-top boxes, voice payments, voice for low-literacy users.
- **Voice as content:** TTS, dubbing, audiobooks, brand voices.
- **Voice as documentation:** medical scribes, field data entry, meeting notes.
- **Tooling:** testing/evaluation, orchestration, telephony.

Sources: [Business Today (Prisma v2.5)](https://www.businesstoday.in/amp/technology/artificial-intelligence/story/gnani-ai-launches-prisma-v2-5-claims-better-accuracy-than-sarvam-elevenlabs-on-indian-speech-538008-2026-06-19), [Inya VoiceOS](https://www.businesstoday.in/technology/news/story/india-ai-impact-summit-2026-gnaniai-launches-5-billion-parameter-voice-ai-model-under-indiaai-mission-516400-2026-02-17), [Voice of India benchmark](https://arxiv.org/abs/2604.19151), [Bolna (TechCrunch)](https://techcrunch.com/2026/01/20/bolna-nabs-6-3-million-from-general-catalyst-for-its-india-focused-voice-orchestration-platform/), [Nasscom–Krisp](https://www.dtnext.in/lifestyle/technology/voice-ai-adoption-scales-up-in-india-as-31-pc-of-firms-move-to-limited-production-report), [Swiggy × Sarvam](https://www.freepressjournal.in/tech/swiggy-partners-with-sarvam-ai-to-bring-voice-ordering-in-11-indian-languages-how-does-it-work).

---

## 4. The competitive field (other entrants)

- ~130 public GitHub repos look like entries (list: `references/challenge-entries-github.json`). Gnani claims 15,000+ students registered/building [V].
- Public posts are few and low-engagement (typically single or low double-digit reactions; the highest seen ~100).
- Most entries mock telephony and don't measure accuracy. The strongest ones measure: **Rythu Vaani** (Telugu; Prisma v3.0 kept intent 10/10 vs v2.5 6/10 at 0 dB noise), **Scam Sentinel** (self-built 20-call benchmark).

| Theme | Approx. entries | Crowding |
|---|---|---|
| Kirana billing / khata / ordering | ~25 | Very crowded |
| Govt schemes / civic / legal | ~15 | Crowded |
| Call analytics / noise | ~15 | Crowded |
| Education / tutors | ~14 | Crowded |
| ASHA / rural health intake | ~12 | Crowded |
| Scam-call shields | ~12 | Crowded |
| Farmer helplines | ~10 | Crowded |
| Interview coaches | ~8 | Moderate |
| Field operations | ~8 | Moderate |
| Accessibility | ~6 | Thin |
| Real voice cloning use | ~3 | Thin |
| Real telephony, entity accuracy, compliance auditing, eval harnesses, low-resource languages | few | Thin |

Reported API pain from entrants' READMEs: 429s, 30 s REST limit, one-request-at-a-time, Evon unreachable via key, credit caution (some run in mock mode).

---

## 5. Past winners and notable submissions

### Global voice-AI hackathon winners
- **GibberLink** (ElevenLabs Worldwide 2025, global winner) — two AI agents on a call realise they're both AI and switch to a data-over-sound protocol. Won on a single surprising, viral moment.
- **Procuro** (ElevenLabs NYC, 2nd) — phones suppliers to find delayed parts; real-call demo after a late pivot.
- **Dealwise** (ElevenLabs SF, 1st) — researches local businesses and calls them for quotes.
- **Roadmate** (ElevenLabs SF, 2nd) — driving copilot; watches road and driver, keeps a drowsy driver talking, texts a friend.
- **Pep** (ElevenLabs online, 2nd) — real-time voice + vision physiotherapy coach.
- **Espresso Labs** (ElevenLabs London, 2nd) — tracks an engineering manager's obligations across work tools.
- **ORION** (Gemini Live Agent Challenge 2026, grand prize of 1,536) — voice copilot for robotic surgery; surgeon gets data without breaking sterility.
- **JohnKeats.AI** (Gemini Live, best technical execution) — companion that reads pitch, pacing and tone.
- **NagarDrishti** (Gemini Live, honourable mention, Indian team) — drivers report potholes by voice; officials query a dashboard.
- **Ekaette** (Gemini Live, honourable mention) — replaces hold queues; live calls + WhatsApp photos and payments.
- **Call My Parts** (Gemini Live, honourable mention, Indian team) — spoken request for used parts → agent calls suppliers → ranked dashboard.
- **Voxy** (AssemblyAI/LiveKit 2025, grand prize) — type a company name, get a configured voice agent. Judge: "it just works."
- **Podweaver** (same, Most Technically Complex) — swaps podcast ads for sponsor reads in the host's cloned voice, 250 ms timing.
- **Hogwarts Spell Caster** (DEV × AssemblyAI) — spoken spells → game actions under 300 ms.
- **Wynnie** (same, Business Automation) — voice shopping agent for elderly users, auto language detection.
- **Dealty** (AssemblyAI NYC 2024, 1st) — fills real-estate forms live during a call.
- **SpeakEasy** (Cal Hacks 11.0, 1st per sponsor) — language learning that keeps the learner's own voice.
- **Form Wizard Pro** (AGI House 2024, 1st) — turns any online form into a voice-guided conversation.
- **SheBeTalking** (AGI House, 3rd) — practise real-world conversations; praised for cultural sensitivity.
- **Vapi Build Challenge 2025** — FROSTai (hands-free field technician support), Jiffly (phone bookings), Candling (emergency call triage + summaries), LeadSense (car-dealer outbound), Talvin (recruiter screening).
- **Timbre** (Penn AI Hackathon 2026, overall; unrelated to Gnani's Timbre) — 60-second voice screening for Parkinson's; voice as a signal.

### Social-impact / Indian winners
- **MEGHA** (Harvard Kennedy School AI for Good 2025, 1st) — toll-free voice helpline for government schemes on basic phones, grounded in official documents.
- **Agriguru** (Infosys Global Hackathon 2025, 1st) — crop advice, disease diagnosis, satellite data, voice in regional languages.
- **CurePharma AI** (Meta Llama Hackathon India 2024, 1st) — regional-language medicine info on WhatsApp for low-literacy users.
- **CivicFix** (same, 2nd) — civic complaints via WhatsApp voice notes/photos routed to officials.
- **Sarvam hackathon top 3** — tender finder; Indic kids' stories; Setu (visual communication for people who can't speak).
- **Interpreter.ai** (SIH 2022, self-reported) — offline regional translator with small local models.

### Enterprise / banking / compliance winners
- **Vigil** (Elastic Forge the Future 2026, grand winner; Sarvam judge) — audits multilingual Indian sales calls for SEBI/AMFI violations; flags the exact timestamp and links the rule clause. Pitch: humans audit <30% of calls. *Closest template to the enterprise market.* **Unverified (Nov 2026 check): no matching "Vigil" winner found; do not cite until confirmed.**
- **Claimsio** (ElevenLabs Warsaw, 2nd) — compliance-focused debt-collection agent; placed despite admitting outbound calling wasn't finished.
- **ToneTag** (RBI HaRBInger 2021) — voice payments in any language with voice-based authentication.
- **NIDAAN** (RBI 4th Global Hackathon 2026, best all-women team) — multilingual voice + Indian Sign Language grievance platform for banks.
- **Call Centre Analytics** (Bank of Baroda × Microsoft 2022, 1st runner-up) — call audio → sentiment, category, agent performance.
- **Echopay** (Payaza, Nigeria 2024) — voice banking for owners who can't read. **Naledi** (DataHack4Fi 2019) — multilingual banking assistant.
- **DirectDefense** (DEF CON 2025 vishing contest, 1st) — live AI calls over real SIP, operators in the loop, <800 ms.
- **AngryKaren / VoiceGauntlet** (ElevenLabs entries, placement unverified) — simulated difficult callers to test support staff / voice agents.
- **Saakshi** (AssemblyAI voice agent hackathon 2026) — explains a loan's Key Fact Statement in Hinglish, checks understanding, keeps proof of consent.

### Speech-recognition competitions
- **Zindi Swahili ASR winner** — LoRA fine-tune of a distilled Whisper on one T4 GPU with city-noise augmentation (WER 17.81). Most reproducible low-resource recipe.
- **TalTech (MADASR, Indian dialects)** — cheap dialect adaptation. **MUCS 2021** — Hindi-English / Bengali-English code-switching benchmark.

### Notable Gnani-challenge submissions
Rythu Vaani (Telugu farmer helpline, measured v3.0 vs v2.5), Scam Sentinel (scam detection, 20-call benchmark), NoiseProof (Noise Canceller target), AyuSwar (health; partly simulated), Bolo Bill / BoloKhata / Kirana Khata (Hinglish billing), Apni Awaaz (translation in your cloned voice), Polyglot (live SIP phone translator), Maryada (RBI recovery-call conduct coach), Dhwani Desk (Kannada civic helpline), Nyayamitra (legal help; self-hosted Evon), AshaSathi (ASHA assistant, IIT Delhi).

### What winners had in common
- **One specific user, one specific problem** — not "everyone".
- **An obvious reason it must be voice** — hands busy, can't read/type, already on a call.
- **A visible, checkable result** — a quote, a filled form, a flagged violation, a booking.
- **Proof** — measured accuracy, latency you can feel, a timestamp tied to a rule.
- **One memorable demo moment.**
- **It worked live** — reliability beat feature lists. Honest scope was rewarded.
- What tends to lose: generic voice chatbots, voice bolted onto something that works as text, multi-feature platforms with no sharp use case.

### How judges score (published rubrics converge)
Use of sponsor tech · technical execution · impact · UX/polish · creativity · presentation. A working demo beats slides.

### Voice-specific things that impress
Low time-to-first-audio (~800 ms voice-to-voice target); barge-in (user can interrupt); proper turn-taking (don't treat "haan" as an interruption); clean mid-sentence language switching; real noisy phone lines; graceful recovery ("phir se boliye"); tasteful, consented voice cloning; measured WER/entity accuracy.

Sources: [ElevenLabs winners](https://elevenlabs.io/blog/announcing-the-winners-of-the-elevenlabs-worldwide-hackathon), [Gemini Live winners](https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-of-the-gemini-live-agent-challenge), [AssemblyAI Sept 2025](https://www.assemblyai.com/blog/voice-agent-hackathon-sept-19), [AssemblyAI challenge](https://www.assemblyai.com/blog/these-7-voice-ai-projects-just-blew-us-away), [AssemblyAI NYC](https://www.assemblyai.com/blog/top-speech-ai-projects-and-winners-at-2024-assemblyai-hackathon), [Cartesia](https://www.cartesia.ai/blog/hacktober), [Vapi](https://vapi.ai/blog/meet-the-winners-of-the-vapi-build-challenge-2025), [Meta Llama India](https://ai.meta.com/blog/llama-hackathon-india/), [MEGHA](https://www.freepressjournal.in/india/ai-solution-for-india-wins-top-spot-at-harvards-hackathon), [Vigil](https://www.elastic.co/blog/mumbai-forge-the-future-hackathon-2026), [ToneTag](https://www.freepressjournal.in/business/tonetag-emerges-the-winner-in-two-categories-in-rbis-first-global-hackathon), [NIDAAN](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62590), [DirectDefense](https://www.directdefense.com/?p=8713), [Zindi](https://zindi.world/blog/winning-solution-to-the-swahili-asr-challenge), [Saakshi](https://lablab.build/ai-hackathons/assemblyai-voice-agent-hackathon/monster/saakshi-consent-you-can-prove).

---

## 6. Direction A — Hands-busy workers who must still keep records

**Lens:** jobs where hands/eyes are fully occupied by the primary task, yet a record, count, report or transaction is still required. Overlaps two winner patterns: "voice because hands are busy" + "the agent produces a real output".

**Key caveat:** no study anywhere measures the gap itself ("hands were busy, so the record was late/wrong/skipped"). What's documented is downstream harm. A build here would be producing that measurement for the first time.

### Settings shortlisted
| Job | Hands busy with | Record required | Documented harm |
|---|---|---|---|
| Electricity linemen | Live wires at height, insulated gloves | Permit-to-work / line-clear messages | Wrong-feeder shutdowns; linemen electrocuted (phone line-clear blamed in OERC 2008 order, Punjab 2025) |
| Railway track maintainers | Walking ~12 km with tools | Keyman/patrol defect books | 361 track-worker deaths (2019–Nov 2023); CAG: 422 derailments attributed to engineering |
| Lift technicians | In the shaft, greasy hands | Maintenance logbook | Logbooks used as evidence in negligence cases |
| ASHA/ANM workers | Antenatal/newborn care in homes (partly) | RCH registers → portal (double entry); incentive claims | ~¼ of ANM time on registers; register vs survey concordance 26.6%; claims delayed 3–12 months |
| Ward nurses | Gloved bedside care | Charts, medication records, shift handover | Kerala (obstetric units, observed 2015): median 6 of 25 handover items, allergies mentioned 3% |
| OT staff | Sterile hands | Swab/instrument counts | Retained-gauze consumer-court awards (₹12–19 lakh) |
| Livestock AI technicians | Arm inside the animal, AI gun in the other hand | Bharat Pashudhan app entries; pay released only after pregnancy-diagnosis upload | 49.2M AIs vs 6.7M calvings recorded (under-recording) |
| Dairy collection centres | Cans, sampling, analysers | Weight/fat per pour → payment | Fraud probes; fat disputes |
| Mandi weighing | Lifting sacks | Bag weights, receipts | Under-weighing claims |
| Construction supervisors | Moving between crews | Muster roll, wage register | Unverifiable wage records |
| Garment workers | Eyes on the needle | Piece counts (pay) | ILO: piece rates raise wage-theft risk |
| Quick-commerce dark stores | Fast picking, cold rooms | Expiry rotation, temperature logs | Maharashtra FDA suspended licences (2026) |

Rejected: meter readers (smart meters replacing them), sanitation, home technicians, auto workshops (Gnani already markets voice job cards), security guards, inspectors, tower technicians, truck drivers, loco pilots, FCI godowns, brick kilns (no willing payer), jewellery, mining, pharmacists, labs, 108 crews, cloud kitchens, fisheries, kirana.

Warning: in mandis, dairy and construction, some parties **benefit** from loose records — a capture tool alone won't fix that.

### Deep-dives (usage likelihood · voice feasibility · buildability)

**1. Electricity — consumer compensation calculator + lineman line-clear log** (Low–Medium · Medium/High · High)
- Consumer side: computes compensation owed under the Electricity (Rights of Consumers) Rules 2020 and state Standards of Performance (e.g. DERC: ₹50/hr then ₹100/hr for outages beyond the standard), cites the clause, writes a claim letter. **Confirmed novel.** BESCOM received zero applications in four years.
- Lineman side: substation operator speaks the line-clear/return message; system reads back critical fields and blocks unsafe sequences. Grid control rooms already voice-record with read-back (CEA Grid Standards; NERC three-part communication).
- Blockers: phones banned on some maintenance sites (MP Transco); phone line-clear condemned after deaths → voice must supplement, never authorise; rules vary by state and amendment; insulating gloves rule out touchscreens.
- Sources: [OERC 2008 order](https://www.orierc.org/Orders/2008/C-28-2008.pdf), [DERC 3rd amendment](https://www.derc.gov.in/sites/default/files/3rd-Amendment-Regulations-18.12.18_0.pdf), [BESCOM zero claims](https://www.deccanherald.com/india/karnataka/no-plea-in-4-years-under-rules-that-protect-power-consumers-rights-3181930), [MP Transco phone ban](https://www.freepressjournal.in/indore/indore-news-transco-bans-use-of-cellphones-during-maintenance-work).

**2. Livestock AI technicians** (Medium · Medium for event fields, Low–Medium for tag IDs · High in Hindi)
- Dictate AI/PD/calving/vaccination events; validate against INAPH rules (12-digit tag with check digit, bull-ID format, species/sex consistency, event order, PD 45–90 days); read back; offline queue.
- For: national SoP makes upload mandatory and gates the incentive; DataGene (Australia) logs inseminations by voice via headset.
- Against: **ear tags carry a Code-128 barcode** (voice for the tag is redundant); check-digit algorithm undocumented; no Odia; no upload API; technicians paid ~₹50/AI; no clear buyer.
- Sources: [DAHD SoP](https://dahvs.odisha.gov.in/dahvsodisha/wp-content/uploads/2026/02/SoP-for-Artificial-Insemination-in-NDLM-24.1.2026-1.pdf), [NDDB INAPH deck](https://www.standardsfacility.org/sites/default/files/4-KamleshTrived_INAPH_AIRS_India.pdf), [NDDB tag spec](https://www.nddb.org/sites/default/files/pdfs/procurement/TECHNICAL%20SPECIFICATIONS%20OF%20EARTAG%20%20EARTAG%20APPLICATOR_15022016.pdf), [DataGene](https://www.icar.org/Documents/technical_series/ICAR-Technical-Series-no-23-Auckland/Francis.pdf).

**3. Dark-store FSSAI voice self-audit** (Medium · Medium · High)
- Manager walks aisles answering the 32-item / 74-point FSSAI storage checklist by voice; deterministic scoring including the starred-item rule; exception capture (near-expiry, damaged, temperature).
- For: enforcement wave (Maharashtra, Telangana, Karnataka); Zepto regained a licence by showing records; official checklist is a clean gold standard.
- Against: a 2026 FSSAI amendment exempts retailers from FIFO/FEFO records (lead with temperature, pests, hygiene, medical/training records instead); buyer unclear (platform vs partner operator); platforms may have in-house tools.
- Sources: [FSSAI storage checklist](https://infotrain.fssai.gov.in/AMS/doc/RDC_Draft_Storage_01_11_2017.pdf), [Maharashtra FDA](https://ianslive.in/maharashtra-fda-suspends-14-food-licences-after-statewide-quick-commerce-safety-drive--20260814210456), [Telangana](https://thesouthfirst.com/telangana/hyderabad-expired-food-cockroaches-found-at-instamart-zepto-and-flipkart-dark-stores-tg-safe-suspends-licences/), [FIFO amendment](https://taxguru.in/corporate-law/fssai-amends-licensing-rules-exempt-non-manufacturing-food-businesses-daily-production-records.html).

**4. ASHA visit → health card + incentive claim** (Medium · Medium · High; generic version crowded)
- Spoken visit fills MCP-card fields with MoHFW rule flags (Hb <11 / <7, BP ≥140/90, EDD = LMP + 280 days), digit-by-digit read-back, and tallies the official ASHA incentive claim form (Assam's has row codes and rupee amounts).
- For: "we do everything twice"; claims delayed 3–12 months (Meghalaya cut it to days with an app); ASHAs prefer voice to typing (ASHABot: 26.7% voice notes).
- Against: generic voice-to-form is crowded (Sakhi, Dendrite, ~12 entries); no government API; state-specific forms; privacy of speaking health details in homes; Assamese unsupported.
- Sources: [Assam claim form](https://nhmssd.assam.gov.in/APPMS_2024_25/ASHA_documents/ASHA_Incentive_Master_Claim_Form_Draft_ENGLISH_2024.pdf), [New Lines](https://newlinesmag.com/reportage/indias-digital-health-push-is-overworking-its-front-line-women/), [ASHABot paper](https://arxiv.org/html/2409.10913v3), [MoHFW SBA guidelines](https://nhm.gov.in/images/pdf/programmes/maternal-health/guidelines/sba_guidelines_for_skilled_attendance_at_birth.pdf).

**5. Nurse SBAR handover + PvPI adverse-drug-reaction form** (Medium–High · Medium · High)
- Live completeness meter against the 25 SBAR items; a mentioned drug reaction pre-fills the PvPI form (6 mandatory fields) with brand→generic normalisation. OT counts dropped (weakest evidence, least voice-suited).
- For: ~~no Indian nurse-facing voice tool found~~ **corrected: Grapes BSA Pro (May 2026) sells Malayalam/Hindi/Tamil nurse voice notes incl. shift handover; Manipal generates handovers from EMR data with no voice (23 hospitals)**; NABH training covers digital handover; PvPI form public; Eka Care medical ASR eval set (MIT) exists.
- Against: dose errors are dangerous; ward privacy and noise; hospitals buy via EMR vendors; drug vocabulary licensing (MedDRA paid).
- Sources: [Kerala handover study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9098034/), [PvPI form](https://ipc.gov.in/images/ADR-Reporting-Form1.3.pdf) (copy in `references/`), [PvPI newsletter](https://ipc.gov.in/images/pvpi/PvPI-Newsletter-Vol.-16-Issue-1-2026-January-to-March-2026.pdf), [Eka eval set](https://huggingface.co/datasets/ekacare/eka-medical-asr-evaluation-dataset).

---

## 7. Direction B — Helping people claim rights the rules already give them

**Lens:** vendors cluster on revenue (sales, renewals, collections). Regulated workflows that *cost* companies money — grievances, disputes, compensation, consent — are underserved, and a published rule gives an objective answer key.

| Idea | Evidence it's real | Data | Novelty |
|---|---|---|---|
| RBI Ombudsman pre-check (is this complaint even maintainable?) | ~85% of complaints at RBI's receipt centre closed as non-complaints / non-maintainable | High — RB-IOS 2021 clause 10 + date logic (**RB-IOS 2021 was replaced by the Integrated Ombudsman Scheme 2026 from 1 Jul 2026 — re-check clauses**); fully synthetic | Weakened (RBI plans a chatbot) |
| Broadband fault docket with TRAI repair-time clock | TRAI draft proposes a wireline repair benchmark; operators dispute clock rules | High | Weakened; rule still a draft |
| PvPI adverse-drug-reaction capture in Indian languages | Helpline is a menu IVR that doesn't fill forms | High | Weakened |
| Discharge teach-back (patient explains medicines back) | Teach-back improves recall (non-Indian study) | Medium–High (needs clinician labels) | Weakened (reminder calls exist, teach-back doesn't) |
| FASTag wrong-deduction disputes | 12.55 lakh refunds (2024), ~18 lakh (early 2026) | High | **Dropped** — see §10 |
| Gig-worker grievance intake (Karnataka/Rajasthan Acts) | ~~Official portal is text-only~~ corrected: Karnataka IPGRS intake (May 2026) + phone helpline 1902; the Act is under High Court challenge | Medium–High | Weakened |
| Electricity compensation calculator | Compensation rarely claimed | Medium–Low (state PDFs) | **Confirmed novel** |
| Spam-call complaint intake | 31 lakh complaints (2025) | Medium | Weakened and shrinking (TRAI acting on AI-flagged spam) |

Rejected as already done: loan KFS explainer (Saakshi), insurance pre-issuance verification (Ringg; also AuthBridge, Perfios, Signzy, Artivatic; NuSummit compares calls with policy terms), auto job cards (Gnani), Indic role-play training (Disprz), complaint→category mapping (CPGRAMS Samadhan Didi).

Pattern: novelty decays fast — what lasts is the validation layer *after* intake (maintainability checks, compensation maths, understanding checks).

Sources: [RB-IOS 2021](https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12192&Mode=0), [Ombudsman stats](https://hellobanker.in/over-13-lac-complaints-received-by-rbi-ombudsman-in-fy-2024-25-complaints-against-private-sector-banks-increased), [TRAI consultation](https://www.trai.gov.in/sites/default/files/2026-08/CP_05082026.pdf), [NETC guidelines](https://ihmcl.co.in/wp-content/uploads/2025/12/NETC_PG_V2.1.pdf).

---

## 8. Direction C — Checking companies' calls against the law

| Idea | What it does | Status |
|---|---|---|
| **Dark-pattern auditor** | Detects manipulative tactics (false urgency, hidden charges, etc.) in AI sales/retention calls against CCPA's 2023 Dark Patterns Guidelines (13 patterns) | **Confirmed novel**; existing audits cover screens only; no voice dataset (synthetic span-labelled scripts feasible) |
| **Consent-notice conformance tester** | Checks spoken consent notices against DPDP Rule 3 (itemised notice, specific purposes, easy withdrawal, complaint route) | Weakened (consent-capture products exist; no conformance test suite) |
| **Collections compliance guardrails** | RBI recovery-call hours, AI disclosure, consent, promise-to-pay capture, no threats | Gnani's core; Claimsio precedent |
| **Recovery-call conduct auditor** | Flags threats, wrong-hour calls, third-party disclosure in collection recordings with timestamps → RBI clause | None seen beyond Maryada (a challenge entry) |
| **Mis-selling auditor** | Flags rule breaks in insurance/loan/DSA sales calls | One winner exists (Vigil); variants open |

Feasibility note: Prisma Batch returns per-segment timestamps and speaker labels — this makes the "timestamp → rule clause" evidence pattern buildable.

Sources: [CCPA guidelines](https://www.scconline.com/blog/post/2023/12/04/ccpa-notifies-guidelines-for-prevention-and-regulation-of-dark-patterns-2023-legal-news/), [DarkBench](https://arxiv.org/abs/2503.10728), [DPDP Rule 3 explainer](https://www.sansalegal.com/post/how-to-draft-a-dpdp-notice-that-meets-rule-3-of-the-dpdp-rules-2025), [RBI recovery rules](https://www.business-standard.com/amp/article/finance/rbi-directs-loan-recovery-agents-not-to-intimidate-borrowers-no-calling-before-8am-after-7pm-122081201144_1.html).

---

## 9. Directions D–G — Listening, assisting, tooling, creative

**D. Listen only (no conversation):** noisy call QA (crowded; Gnani sells it); who-spoke-in-which-language timeline; spelling-tolerant code-mixed call search.

**E. Assist the human:** handoff packager (detect anger/dispute → summary to human); live agent assist + after-call summary.

**F. Tools for voice-agent builders:** Indic test harness (simulated angry borrower, Tanglish speaker, bad line; scored) — ~~none exist for Indian languages/rules~~ **corrected: Hamming (Hindi/Hinglish) and Cekura (9 Indian languages) support Indian languages; none ship Indian regulatory rule packs.**

**G. Creative:** consented own-voice cross-language speech; synthetic-voice labelling/watermarking (IT Rules); voice payment confirmation with liveness; low-resource language build (Tamil/Kannada supported; Odia/Assamese/Bhojpuri not).

### Commercial fit with Gnani and competitors
- **Plugs straight into Gnani products:** collections guardrails (Agents), conduct auditor and mis-selling auditor (Analytics), handoff packager (Assist), dark-pattern and consent checkers (new Analytics compliance modules).
- **Fits Gnani's Artha / government:** electricity compensation, Ombudsman pre-check, gig-worker grievances, ASHA claims (slow sales; Sarvam strong in government).
- **Better for others:** Sarvam (government rights claims), Navana (BFSI compliance), Exotel/Ozonetel (telephony robustness), Bolna/Vapi-style platforms and Coval-type tools (Indic test harness).
- **Weak businesses:** livestock (no payer), dark stores (unclear buyer), nurse handover (EMR vendors), teach-back (needs clinical validation).
- **Easiest for incumbents to copy:** call QA, agent assist, collections guardrails, generic form-filling. Defensibility comes from evidence (rule-derived test sets, measured accuracy), not code.

---

## 10. Dropped direction — spoken numbers/IDs layer (and FASTag)

**Idea:** a layer that captures spoken numbers/IDs/amounts correctly on noisy, code-mixed phone audio (format validators, checksums, read-back), demoed as FASTag dispute intake, plus an open mini-benchmark.

**Why it was dropped**
- **FASTag demand is weak:** wrong deductions are ~0.03% of ~445 crore annual transactions; many refunds appear to be processed without a complaint; one channel sees ~50 genuine complaints/month. Nobody we know has ever filed one.
- **Industry evidence for the numbers problem is mostly indirect:**
  - Strong only in **healthcare** (JAMA 2018: 7.4 errors/100 words in speech-recognised clinical notes, e.g. "17-year-old"→"70-year-old", wrong drug names; ISMP: insulin 80 units vs 8).
  - Platforms build workarounds (Amazon Lex spelling modes, Microsoft alphanumeric guidance, Retell NATO alphabet), and Sarvam defines an entity score — but **no source quantifies cost**, and **India-specific evidence is anecdotal** (one Retell forum thread on Hindi numbers; vendor blogs).
  - Correction: Gnani's DTMF docs recommend keypad input for security and noisy audio; they do not say Prisma misreads digits.

Sources: [JAMA 2018](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2687052), [ISMP via ECRI](https://home.ecri.org/blogs/ismp-alerts-and-articles-library/can-we-ensure-medication-safety-with-the-use-of-speech-recognition-software), [Amazon Lex](https://docs.aws.amazon.com/lexv2/latest/dg/spelling-styles.html), [Microsoft](https://learn.microsoft.com/en-us/dynamics365/guidance/resources/cs-mcs-alphanumentity), [Sarvam](https://www.sarvam.ai/blogs/evaluating-indian-language-asr), [Retell thread](https://community.retellai.com/t/problem-with-stt/2713), [FASTag refunds 2024](https://www.millenniumpost.in/business/govt-says-1255-lakh-refunds-made-for-faulty-toll-collections-in-2024-603225), [~18 lakh refunds](https://www.etvbharat.com/en/bharat/refunds-issued-to-around-18-lakh-fastag-users-charged-erroneously-nhai-enn26013005907).

---

## 10b. Dropped direction — women's-safety distress agent ("Pukaar")

**Idea:** a woman triggers distress (button, code phrase or speech); an LLM turns her words into a structured brief; an agent calls family, friends, the police station and 112/181 in parallel in each person's language and retries until a human commits, with read-back and a hash-chained evidence log. Design: `references/dropped/pukaar-design.md`.

**Why it was dropped** (independent review scored it 5.5/10)
- **Evidence didn't support the product.** Verified CAG audits show the *state* failing to call callers back (Karnataka 108 called back 3% of 55 lakh dropped calls; MP never built its missed-call desk; Punjab forwarded ~30% of emergencies after >5 min). That is not evidence that calling her family closes a gap. "Family is closer than police" and "nobody reads the SOS SMS" had no source. "Helplines don't pick up" is not supported: no post-2019 answer-rate data exists, and measured abandon rates were 2.9–5.5%.
- **Real-world risk:** a bot calling 112 (58–80% of 112 traffic is already blank/prank), false alarms fanning out to everyone, unknown-number calls going unanswered, "call until confirmed" becoming harassment.
- **Gnani concurrency = 1 breaks live parallel conversations;** only the opening brief can be cached.
- **Headline metric was circular:** a simulator with assumed answer rates shows parallel beats sequential by construction.
- **Weak fit with Gnani's market** (BFSI, collections, contact centres) for the interview.

**What survives:** `references/real-voice-datasets.md` (licensed real-voice eval sets, reusable for any idea) and `references/helpline-evidence.md` (verified emergency-response facts). Possible pivot noted by the reviewer, not pursued: an organisation's follow-up desk (night-shift transport / cab fleet safety).

---

## 11. Independent evaluation (ranking of all ideas)

A fresh evaluator scored all ideas on: feasibility (30%), award fit and differentiation (20%), defensible evidence (20%), value and Gnani fit (15%), demo strength (10%), risk (5%). Assumed a solo, Python-capable builder speaking Hindi/English.

Original top 5 (before the numbers direction was dropped):
1. ~~Numbers layer wrapped as FASTag disputes~~ — dropped (§10).
2. **Recovery-call conduct auditor** (absorbing collections guardrails) — timestamp → RBI clause via Batch STT; precision/recall on synthetic calls with planted violations. Strongest Gnani fit; drag: crowded call-audit theme.
3. **Dark-pattern auditor for AI sales calls** — confirmed novel; strong creative story; softer legal mapping ("applies the CCPA taxonomy to voice").
4. ~~Telephony robustness report card~~ — closest to the dropped direction; no end user.
5. **ASHA visit → health card + incentive claim** — real users and pain; drag: crowded theme, form modelling effort.

Explicitly avoid: call QA and handoff (crowded, copyable), livestock (barcode makes voice redundant for tags), dark stores (no buyer), lineman permit log (unsafe failure mode), Odia/Assamese builds (unsupported), discharge teach-back (needs clinician labels).

Sensitivity: a Tamil/Kannada speaker can target Main Character with a regional subset; a team of two can combine directions; strong frontend skills lift the ASHA idea.

---

## 12. Recurring design pattern (all deep-dives converged on it)

1. Capture speech (push-to-talk / streaming / batch).
2. Extract structured fields with an LLM into a strict schema (quote source text per field).
3. Validate deterministically against the official rule/form (never let the LLM do arithmetic or rule checks).
4. Read back critical values with TTS; re-ask only the failed field.
5. Log evidence (transcript snippet, timestamp, rule clause).
6. Evaluate on a synthetic test set derived from public forms/regulations, with ground truth generated first; report per-field accuracy, precision/recall, and failure cases honestly. Include some self-recorded audio, since TTS-only audio overstates accuracy.

---

## 12b. Current direction (Nov 2026)
Chosen after a 5-round evaluation (`IDEAS-HILLCLIMB.md`): **Samajh**, an RBI 85Y post-sale understanding callback. See `DESIGN.md`. Amounts pilot: `references/pilots/amounts-pilot-2026-11-10.md`.

## 13. Open items / unverified
- Whether Prisma/Timbre v3.0 are explicitly allowed (rules say "any Gnani model or API").
- Gnani concurrency limit and per-call credit cost.
- Primary texts read only via summaries: some TRAI, CCPA, DPDP, RBI annual-report figures.
- Electricity research files were not preserved; claims rely on cited URLs.
- Real noise levels in target environments; dark-store tooling; current immunisation schedule details.
