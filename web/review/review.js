// The review pages: reviewer queue, one case, the sample and attempt log, the half-yearly report.
// Every label for a rule, tier, outcome or decision is the server's (samajh/ops/views.py).
// Nothing here decides anything: a referral asks a person to look, and the decision is theirs.

const API = "/api/review";
const DASH = "\u2014";

// ---------------------------------------------------------------- fetch

class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function api(path, options) {
  let res;
  try {
    res = await fetch(API + path, { headers: { Accept: "application/json" }, ...options });
  } catch {
    throw new ApiError(0, "no_answer", "The review server did not answer.");
  }
  let body = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const err = (body && body.error) || {};
    throw new ApiError(res.status, err.code || String(res.status), err.message || `The server answered with status ${res.status}.`);
  }
  if (body === null) throw new ApiError(res.status, "not_json", "The server's answer could not be read.");
  return body;
}

// ---------------------------------------------------------------- DOM

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

function facts(pairs) {
  return h("dl", { class: "facts" }, pairs.filter(Boolean).map(([k, v]) => [h("dt", null, k), h("dd", null, v)]));
}

// cols: [{label, num, head, wide, cls}]; rows: [{cells: [...], cls}] or {group: "label"}.
// `stack` turns each row into a card on a phone; the roles keep the table semantics when it does.
function table({ cols, rows, caption, stack = false, long = false }) {
  const role = (r) => (stack ? r : null);
  const head = h(
    "thead",
    { role: role("rowgroup") },
    h("tr", { role: role("row") }, cols.map((c) => h("th", { scope: "col", role: role("columnheader"), class: c.num ? "num" : null }, c.label))),
  );
  const body = h(
    "tbody",
    { role: role("rowgroup") },
    rows.map((row) => {
      if (row.group) return h("tr", { class: "group" }, h("th", { colspan: cols.length, scope: "colgroup" }, row.group));
      return h(
        "tr",
        { role: role("row"), class: row.cls },
        row.cells.map((cell, i) => {
          const c = cols[i];
          const cls = [c.num && "num", c.wide && "wide", c.cls].filter(Boolean).join(" ") || null;
          const inner = stack ? h("div", { class: "cell" }, cell) : cell;
          return c.head
            ? h("th", { scope: "row", role: role("rowheader"), class: cls, "data-label": c.label }, inner)
            : h("td", { role: role("cell"), class: cls, "data-label": c.label }, inner);
        }),
      );
    }),
  );
  return h(
    "div",
    { class: stack ? "table-wrap stack" : "table-wrap", tabindex: stack ? null : "0", role: stack ? null : "group", "aria-label": stack ? null : caption || "Table" },
    h("table", { role: role("table"), class: long ? "long" : null }, caption ? h("caption", null, caption) : null, head, body),
  );
}

// ---------------------------------------------------------------- formatting

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// "2027-02-08" and "2027-02-08T10:15:00" both give "8 Feb 2027". Read from the string, so no time zone shifts the day.
function fmtDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
  return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}` : DASH;
}

function fmtDateTime(iso) {
  const t = /T(\d{2}):(\d{2})/.exec(iso || "");
  return t ? `${fmtDate(iso)}, ${t[1]}:${t[2]}` : fmtDate(iso);
}

const int = (n) => Number(n).toLocaleString("en-IN");
const inr = (n) => "\u20B9" + Number(n).toLocaleString("en-IN");
const yesNo = (b) => (b ? "Yes" : "No");
const words = (key) => {
  const s = String(key).replaceAll("_", " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
};
const days = (n) => `${int(n)} ${n === 1 ? "day" : "days"}`;

function mmss(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

// A Proportion is never shown as a bare percentage: the count and its n always travel with it.
const pCount = (p) => `${int(p.count)} of ${int(p.n)}`;
const pShare = (p) => (p.n === 0 || p.share === null ? DASH : `${Math.round(p.share * 100)}%`);
const pInterval = (p) => (p.n === 0 || p.low === null || p.high === null ? DASH : `${Math.round(p.low * 100)} to ${Math.round(p.high * 100)}%`);
const withInterval = (p) => [pBoth(p), h("span", { class: "sub" }, p.n ? `95% interval ${pInterval(p)}` : "no calls")];
const pBoth = (p) => (p.n === 0 || p.share === null ? pCount(p) : `${pCount(p)} (${pShare(p)})`);

const LANGUAGE_NAMES = { hi: "Hindi", "hi-en": "Hinglish", ta: "Tamil", kn: "Kannada" };
const LANG_ATTR = { hi: "hi", "hi-en": "hi", ta: "ta", kn: "kn" };
const LENDER_TYPES = { bank: "Bank", nbfc: "NBFC" };
const languageName = (code) => LANGUAGE_NAMES[code] || code;

const sevLabel = (severity) => h("span", { class: `sev sev-${severity}` }, words(severity));
const simTag = () => h("span", { class: "tag sim" }, "Simulated");
const phoneTag = () => h("span", { class: "tag phone" }, "Phone call");
const sourceTag = (simulated) => (simulated ? simTag() : phoneTag());
const cCount = (c) => `${int(c.count)} of ${int(c.n)}`;
const caseHref = (id) => `case.html?id=${encodeURIComponent(id)}`;

function remember(key, value) {
  try {
    if (value === undefined) return window.localStorage.getItem(key) || "";
    window.localStorage.setItem(key, value);
  } catch {
    // storage is off or full: the page works without it
  }
  return "";
}

// ---------------------------------------------------------------- header

const NAV = [
  ["queue", "index.html", "Reviewer queue"],
  ["attempts", "attempts.html", "Sample and attempts"],
  ["report", "report.html", "Half-yearly report"],
];

function renderHeader(batch, page) {
  const lender = batch ? batch.meta.book.lender_name : null;
  const header = document.getElementById("site-header");
  // h() drops the empty children, so the header is built inside one element and moved over.
  const parts = h(
    "div",
    null,
    h(
      "div",
      { class: "head-row" },
      h("div", { class: "brand" }, "Samajh ", h("span", null, "post-sale feedback review")),
      lender ? h("div", { class: "lender" }, lender) : null,
    ),
    h(
      "nav",
      { class: "site-nav", "aria-label": "Review pages" },
      NAV.map(([key, href, label]) => h("a", { href, "aria-current": key === page ? "page" : null }, label)),
      page === "case" ? h("span", { "aria-current": "page" }, "Case") : null,
    ),
    batch
      ? h(
          "div",
          { class: "sim-band", role: "note" },
          h("p", null, h("strong", null, batch.simulated ? "Simulated" : "Synthetic"), batch.simulated_notice),
          h("p", { class: "access" }, batch.access_notice),
        )
      : null,
  );
  header.replaceChildren(...parts.childNodes);
}

function showError(main, err) {
  const known = err instanceof ApiError;
  const advice =
    known && err.status === 409
      ? ["No batch has been run on this server yet. Run ", h("code", null, "uv run python -m samajh.ops demo"), " first, then reload this page."]
      : known && err.status === 0
        ? ["Check that the server is running (", h("code", null, "uv run python -m samajh.server --port 8085"), "), then reload this page."]
        : known && err.status === 404
          ? ["Go back to the ", h("a", { href: "index.html" }, "reviewer queue"), " and open the case from there."]
          : ["Reload the page. If it happens again, the server log has the detail."];
  main.replaceChildren(
    h(
      "div",
      { class: "panel error", role: "alert" },
      h("h2", null, "This page could not be loaded"),
      h("p", null, known ? err.message : "The page met a problem while showing the data."),
      h("p", null, advice),
      known && err.code ? h("p", { class: "small muted" }, "Code: ", h("code", null, err.code)) : null,
    ),
  );
}

// ---------------------------------------------------------------- queue

const isOpen = (item) => !(item.disposition && item.disposition.final);

async function pageQueue(main, batch) {
  const queue = await api("/queue");
  const items = queue.items;
  const open = items.filter(isOpen).length;
  let show = "all";
  const list = h("div", null);
  const count = h("p", { class: "small muted", role: "status" });

  const draw = () => {
    const rows = items.filter((it) => show === "all" || isOpen(it));
    count.textContent =
      show === "all" ? `Showing ${int(rows.length)} of ${int(items.length)} referred cases.` : `Showing ${int(rows.length)} open of ${int(items.length)} referred cases.`;
    if (items.length === 0) {
      list.replaceChildren(h("div", { class: "panel" }, h("p", null, "No call in this batch has been referred to a reviewer.")));
    } else if (rows.length === 0) {
      list.replaceChildren(h("div", { class: "panel" }, h("p", null, "No case is awaiting a final decision. Choose All to see the decided cases.")));
    } else {
      list.replaceChildren(
        table({
          stack: true,
          caption: "Cases the report counts first (open, then decided), each by severity and then the oldest call; then referred calls the report does not count.",
          cols: [
            { label: "Severity" },
            { label: "Case", wide: true, cls: "case-cell" },
            { label: "Loan and borrower" },
            { label: "Branch and channel" },
            { label: "Day since sale, at the call", num: true },
            { label: "Paragraphs" },
            { label: "Decision" },
          ],
          rows: rows.map((it) => ({
            cls: [isOpen(it) ? null : "decided", it.in_report ? null : "uncounted"].filter(Boolean).join(" ") || null,
            cells: [
              sevLabel(it.severity),
              [
                h("a", { class: "case-link", href: caseHref(it.case_id), lang: "en" }, it.headline),
                h(
                  "span",
                  { class: "sub" },
                  h("span", { class: "id" }, it.case_id),
                  ` \u00B7 ${int(it.refer_lines)} ${it.refer_lines === 1 ? "line" : "lines"} for review \u00B7 ${languageName(it.language)} `,
                  sourceTag(it.simulated),
                ),
                it.in_report ? null : h("span", { class: "sub" }, `Not counted in the report: ${it.not_counted_because}`),
              ],
              [h("span", { class: "id nowrap" }, it.loan_id), h("span", { class: "sub" }, it.borrower)],
              it.branch
                ? [h("span", { class: "nowrap" }, it.branch), h("span", { class: "sub" }, `${words(it.channel)} \u00B7 sold ${fmtDate(it.sold_on)}`)]
                : h("span", { class: "muted" }, "Not on the book"),
              it.day_since_sale === null ? DASH : `Day ${int(it.day_since_sale)}`,
              it.may_engage.length ? h("span", { class: "engage" }, `may engage ${it.may_engage.map((m) => m.replace(/^may engage /, "")).join(", ")}`) : h("span", { class: "muted" }, DASH),
              it.disposition
                ? [it.disposition.decision_label, h("span", { class: "sub" }, `${it.disposition.reviewer}, ${fmtDate(it.disposition.recorded_at)}`)]
                : h("strong", null, "Awaiting review"),
            ],
          })),
        }),
      );
    }
  };

  const radio = (value, label) =>
    h(
      "label",
      null,
      h("input", {
        type: "radio",
        name: "show",
        value,
        checked: value === show,
        onchange: () => {
          show = value;
          draw();
        },
      }),
      label,
    );

  main.replaceChildren(
    h(
      "div",
      { class: "page-head" },
      h(
        "div",
        null,
        h("h1", null, "Reviewer queue"),
        h("p", { class: "muted lead" }, "Calls referred for a person to look at. A referral is a request to review a call against the record, and the decision on each case is the reviewer's."),
      ),
      h("fieldset", { class: "filter" }, h("legend", { class: "vh" }, "Cases to show"), radio("all", `All (${int(items.length)})`), radio("open", `Open (${int(open)})`)),
    ),
    h(
      "ul",
      { class: "stats" },
      h("li", null, h("b", null, `${int(batch.completed)} of ${int(batch.sampled)}`), h("span", null, "sampled loans with a completed call")),
      h("li", null, h("b", null, `${int(batch.referred)} of ${int(batch.completed)}`), h("span", null, "completed calls referred")),
      h("li", null, h("b", null, `${int(batch.open_cases)} of ${int(batch.referred)}`), h("span", null, "counted referrals open (no final decision)")),
      batch.other_referrals ? h("li", null, h("b", null, int(batch.other_referrals)), h("span", null, "referred calls outside the sample or the window")) : null,
    ),
    count,
    list,
  );
  draw();
}

// ---------------------------------------------------------------- one case

function productFacts(p) {
  const features = [...p.features].sort().map(words);
  return facts([
    ["Kind", words(p.kind)],
    ["Provider", p.provider],
    ["Premium", inr(p.premium_inr)],
    ["Cover", inr(p.cover_inr)],
    ["Term", `${int(p.term_months)} months`],
    ["Paid from the loan", yesNo(p.paid_from_loan)],
    ["Required for the loan", yesNo(p.required_for_loan)],
    ["Recorded as a risk mitigant", yesNo(p.risk_mitigant)],
    ["Choice of provider offered", yesNo(p.provider_choice_offered)],
    ["Cancellation window", p.cancel_window_days === null ? "None on record" : days(p.cancel_window_days)],
    ["Consent", p.consent ? `${words(p.consent.method)}, ${fmtDate(p.consent.at)}` : "None on record"],
    ["Features on record", features.length ? features.join(", ") : "None on record"],
  ]);
}

function recordSide(loan) {
  return h(
    "section",
    { class: "record-side", "aria-labelledby": "record-h" },
    h("h2", { id: "record-h" }, "The lender's record"),
    h(
      "div",
      { class: "panel" },
      h("h3", null, "Loan"),
      facts([
        ["Loan", h("span", { class: "id" }, loan.loan_id)],
        ["Borrower", loan.borrower],
        ["Lender type", LENDER_TYPES[loan.lender_type] || words(loan.lender_type)],
        ["Loan kind", words(loan.loan_kind)],
        ["Sanctioned", inr(loan.sanctioned_inr)],
        ["Disbursed", inr(loan.disbursed_inr)],
        ["Sold on", loan.sold_on ? fmtDate(loan.sold_on) : "Not on the lender's book (phone record)"],
        loan.branch ? ["Branch", loan.branch] : null,
        loan.channel ? ["Channel", words(loan.channel)] : null,
      ]),
    ),
    loan.products.map((p) => h("div", { class: "panel" }, h("h3", null, "Product ", h("span", { class: "id" }, p.id)), productFacts(p))),
    loan.products.length === 0 ? h("div", { class: "panel" }, h("p", { class: "muted" }, "No product on the record for this loan.")) : null,
  );
}

function quoteFigure(q, ctx) {
  return h(
    "figure",
    { class: "quote" },
    h("blockquote", { lang: ctx.lang }, q.quote),
    h(
      "figcaption",
      null,
      h("a", { href: `#turn-${q.turn_id}`, onclick: () => ctx.openTranscript() }, `Turn ${q.turn_id}`),
      q.start_s !== null && ctx.recording
        ? h(
            "a",
            { href: `${ctx.recording}#t=${q.start_s}`, onclick: (ev) => ctx.playFrom(ev, q.start_s) },
            `Play the recording from ${mmss(q.start_s)}`,
          )
        : q.start_s !== null
          ? h("span", null, `At ${mmss(q.start_s)} in the call`)
          : null,
    ),
  );
}

function lineCard(line, ctx) {
  return h(
    "article",
    { class: "line" },
    h(
      "div",
      { class: "line-head" },
      h("h3", null, line.title),
      line.tier !== "refer" ? h("span", { class: `tier tier-${line.tier}` }, line.tier_label) : null,
    ),
    h(
      "p",
      { class: "small muted line-rules" },
      [line.product_id ? `Product ${line.product_id}` : "Whole call", line.rule_labels.join(", ")].join(" \u00B7 "),
      line.may_engage.length ? [" \u00B7 ", h("span", { class: "engage" }, line.may_engage.join("; "))] : null,
    ),
    h(
      "div",
      { class: "sides" },
      h("div", { class: "side record" }, h("span", { class: "side-label" }, "Record"), h("p", null, line.record_value)),
      h(
        "div",
        { class: "side customer" },
        h("span", { class: "side-label" }, "Customer"),
        line.quote ? quoteFigure(line.quote, ctx) : h("p", { class: "small muted" }, "No quote is attached to this line."),
      ),
    ),
  );
}

function dispositionBlock(d) {
  return [
    h("p", { class: "what" }, d.decision_label),
    h("p", { class: "small muted" }, `Recorded by ${d.reviewer} on ${fmtDateTime(d.recorded_at)}. ${d.final ? "Final: the case is closed." : "Not final: the case stays open."}`),
    h("p", { class: "note-text" }, d.note),
  ];
}

function decisionSection(first) {
  const now = h("div", { class: "panel decision-now" });
  const history = h("div", null);
  const msg = h("p", { class: "form-msg", role: "status", "aria-live": "polite" });
  const note = h("textarea", { id: "d-note", name: "note", required: true, maxlength: "2000", rows: "4" });
  const who = h("input", { id: "d-who", name: "reviewer", type: "text", required: true, maxlength: "80", autocomplete: "name" });
  who.value = remember("samajh.review.reviewer");
  const submit = h("button", { class: "btn primary", type: "submit" }, "Record decision");
  const caseId = first.case_id;

  const show = (c) => {
    now.className = `panel decision-now${c.disposition && c.disposition.final ? " final" : ""}`;
    now.replaceChildren(
      h("h3", null, "Current decision"),
      ...(c.disposition ? dispositionBlock(c.disposition) : [h("p", { class: "what" }, "Awaiting review"), h("p", { class: "small muted" }, "No decision has been recorded on this case.")]),
    );
    history.replaceChildren(
      h("h3", null, `Decisions recorded on this case (${int(c.history.length)})`),
      c.history.length
        ? h("ol", { class: "history panel" }, c.history.map((d) => h("li", null, dispositionBlock(d))))
        : h("p", { class: "small muted" }, "None yet."),
    );
  };

  const form = h(
    "form",
    {
      class: "decide panel",
      novalidate: true,
      onsubmit: async (ev) => {
        ev.preventDefault();
        const picked = form.querySelector('input[name="decision"]:checked');
        const problem = !picked
          ? "Choose one of the decisions."
          : !note.value.trim()
            ? "Write a note that says what you looked at and why you decided this."
            : !who.value.trim()
              ? "Enter your name."
              : "";
        msg.className = problem ? "form-msg bad" : "form-msg";
        msg.textContent = problem || "Saving\u2026";
        if (problem) {
          (!picked ? form.querySelector('input[name="decision"]') : !note.value.trim() ? note : who).focus();
          return;
        }
        submit.disabled = true;
        try {
          const saved = await api(`/cases/${encodeURIComponent(caseId)}/disposition`, {
            method: "POST",
            headers: { Accept: "application/json", "Content-Type": "application/json" },
            body: JSON.stringify({ decision: picked.value, note: note.value.trim(), reviewer: who.value.trim() }),
          });
          remember("samajh.review.reviewer", who.value.trim());
          show(saved);
          note.value = "";
          picked.checked = false;
          msg.className = "form-msg ok";
          msg.textContent = saved.disposition ? `Saved: ${saved.disposition.decision_label}.` : "Saved.";
        } catch (err) {
          msg.className = "form-msg bad";
          msg.textContent = err instanceof ApiError ? `Not saved. ${err.message}` : "Not saved. The page met a problem.";
        } finally {
          submit.disabled = false;
        }
      },
    },
    h("h3", null, "Record a decision"),
    h(
      "fieldset",
      null,
      h("legend", null, "Decision"),
      first.decisions.map((d) => h("label", { class: "choice" }, h("input", { type: "radio", name: "decision", value: d.key, required: true }), h("span", null, d.label))),
    ),
    h("div", null, h("label", { class: "field", for: "d-note" }, "Note (required): what you looked at and why"), note),
    h("div", null, h("label", { class: "field", for: "d-who" }, "Your name"), who),
    h("div", { class: "form-row" }, submit, msg),
  );

  show(first);
  return h("section", { "aria-labelledby": "decide-h" }, h("h2", { id: "decide-h" }, "Reviewer's decision"), now, form, h("div", { style: "margin-top:16px" }, history));
}

async function pageCase(main) {
  const id = new URLSearchParams(window.location.search).get("id");
  if (!id) throw new ApiError(404, "no_case_id", "This address names no case.");
  const c = await api(`/cases/${encodeURIComponent(id)}`);
  document.title = `Case ${c.case_id} \u00B7 Samajh review`;

  const call = c.call;
  const audio = call.recording_url ? h("audio", { controls: true, preload: "none", src: call.recording_url }) : null;
  const transcript = h("details", { class: "transcript", id: "transcript" });
  const ctx = {
    lang: LANG_ATTR[call.language] || null,
    recording: call.recording_url,
    openTranscript: () => {
      transcript.open = true;
    },
    playFrom: (ev, start) => {
      ev.preventDefault();
      // The #t fragment asks the browser to start there; the listener covers a browser that ignores it.
      audio.addEventListener(
        "loadedmetadata",
        () => {
          if (Math.abs(audio.currentTime - start) > 0.5) audio.currentTime = start;
        },
        { once: true },
      );
      audio.src = `${call.recording_url}#t=${start}`;
      audio.load();
      audio.play().catch(() => {
        // the browser refused to start playback: the controls are still there
      });
      audio.scrollIntoView({ block: "nearest" });
    },
  };

  const cited = c.transcript.filter((t) => t.cited).length;
  transcript.append(
    h("summary", null, `Full transcript (${int(c.transcript.length)} turns, ${int(cited)} cited above)`),
    call.transcript_note ? h("p", { class: "small muted" }, call.transcript_note) : null,
    h(
      "ol",
      { class: "turns" },
      c.transcript.map((t) =>
        h(
          "li",
          { id: `turn-${t.turn_id}`, class: t.cited ? "cited" : null },
          h(
            "div",
            { class: "meta" },
            h("b", null, `Turn ${t.turn_id}`),
            h("span", null, words(t.speaker)),
            t.start_s !== null ? h("span", { class: "num" }, mmss(t.start_s)) : null,
            t.cited ? h("b", null, "Cited above") : null,
          ),
          h("p", { lang: ctx.lang }, t.text),
        ),
      ),
    ),
  );
  if (window.location.hash.startsWith("#turn-")) transcript.open = true;

  const source = call.source.kind === "phone_session" ? ["Phone session ", h("span", { class: "id" }, call.source.session_id)] : ["Scripted, no phone involved (", h("code", null, call.source.script), ")"];

  main.replaceChildren(
    h("p", { class: "small" }, h("a", { href: "index.html" }, "\u2190 Reviewer queue")),
    h(
      "div",
      { class: "page-head" },
      h(
        "div",
        { class: "case-title" },
        h("h1", null, "Case ", h("span", { class: "id" }, c.case_id)),
        sevLabel(c.severity),
        h("span", { class: `tier tier-${c.tier}` }, c.tier_label),
        sourceTag(call.simulated),
        h(
          "p",
          { class: "muted" },
          `${c.loan.borrower} \u00B7 loan `,
          h("span", { class: "id" }, c.loan.loan_id),
          c.loan.branch ? ` \u00B7 ${c.loan.branch}, ${words(c.loan.channel).toLowerCase()} channel` : "",
        ),
      ),
    ),
    h("p", { class: "notice" }, "This call was referred so that a person can compare what the customer said with the record. Nothing on this page is a finding about the sale. The decision is the reviewer's."),
    c.in_report ? null : h("p", { class: "notice warn" }, `The half-yearly report does not count this call: ${c.not_counted_because}. It is here so that a person still looks at it.`),
    h(
      "div",
      { class: "case-grid", style: "margin-top:20px" },
      recordSide(c.loan),
      h(
        "div",
        null,
        h(
          "section",
          { "aria-labelledby": "words-h" },
          h("h2", { id: "words-h" }, "The customer's words, against the record"),
          c.refer_lines.map((line) => lineCard(line, ctx)),
        ),
        h(
          "section",
          { "aria-labelledby": "call-h" },
          h("h2", { id: "call-h" }, "The call"),
          h(
            "div",
            { class: "panel" },
            facts([
              ["Call", h("span", { class: "id" }, call.call_id)],
              ["When", fmtDateTime(call.at)],
              ["Language", languageName(call.language)],
              ["Attempt", call.attempt_number === null ? "Outside the sample" : int(call.attempt_number)],
              ["Day since sale", call.day_since_sale === null ? DASH : int(call.day_since_sale)],
              ["Source", source],
              ["Analysis", call.analysis],
              ["Recording", audio ? "Below. The play links beside each quote start it at that turn." : "No recording for this call."],
            ]),
            audio,
          ),
        ),
        c.other_lines.length
          ? h(
              "section",
              { "aria-labelledby": "other-h" },
              h("h2", { id: "other-h" }, "Other issues on the same call"),
              h("p", { class: "small muted", style: "margin-bottom:10px" }, c.in_report ? "Questions the call left undecided and understanding gaps. They are counted in the half-yearly report and are not the reason this case was referred." : "Questions the call left undecided and understanding gaps. This call is not counted in the report, and these lines are not the reason it was referred."),
              c.other_lines.map((line) => lineCard(line, ctx)),
            )
          : null,
        c.undecided.length
          ? h(
              "section",
              { "aria-labelledby": "undecided-h" },
              h("h2", { id: "undecided-h" }, "Checks that could not decide"),
              h("div", { class: "panel" }, h("ul", { class: "plain-list" }, c.undecided.map((u) => h("li", null, u.label)))),
            )
          : null,
        h("section", { "aria-labelledby": "transcript-h" }, h("h2", { id: "transcript-h" }, "Transcript"), transcript),
        decisionSection(c),
      ),
    ),
  );
}

// ---------------------------------------------------------------- draws (attempt log and report)

function drawsTable(draws, caption) {
  return table({
    caption,
    cols: [
      { label: "Draw", head: true },
      { label: "As of" },
      { label: "Sales covered" },
      { label: "Share taken", num: true },
      { label: "Eligible", num: true },
      { label: "Drawn", num: true },
      { label: "Chance of being drawn", num: true },
      { label: "Seed", num: true },
      { label: "Recomputed and matched" },
    ],
    rows: draws.map((d) => ({
      cells: [
        h("span", { class: "id nowrap" }, d.draw_id),
        h("span", { class: "nowrap" }, fmtDate(d.as_of)),
        d.after ? `sold after ${fmtDate(d.after)} and ${d.min_day} to ${d.max_day} days before` : `sold ${d.min_day} to ${d.max_day} days before`,
        `${Math.round(d.rate * 100)}%`,
        int(d.eligible),
        int(d.drawn),
        d.inclusion === null ? DASH : `${int(d.drawn)} of ${int(d.eligible)} (${(d.inclusion * 100).toFixed(1)}%)`,
        String(d.seed),
        yesNo(d.verified),
      ],
    })),
  });
}

function outsideTable(rows) {
  return table({
    stack: true,
    caption: "Phone calls whose loan was not drawn in this batch. They are listed so that nothing is lost, and never enter the sampled statistics.",
    cols: [
      { label: "Session", head: true },
      { label: "Record and loan" },
      { label: "When" },
      { label: "Language" },
      { label: "Call outcome" },
      { label: "Why outside the sample" },
      { label: "Case" },
    ],
    rows: rows.map((o) => ({
      cells: [
        [h("span", { class: "id" }, o.session_id), " ", phoneTag()],
        [h("span", { class: "id" }, o.record_id), h("span", { class: "sub id" }, o.loan_id)],
        h("span", { class: "nowrap" }, fmtDateTime(o.at)),
        languageName(o.language),
        [o.outcome_label, o.tier_label ? h("span", { class: `sub tier tier-${o.tier}` }, o.tier_label) : null],
        o.reason,
        o.case_id ? h("a", { href: caseHref(o.case_id), class: "nowrap" }, "Open case") : h("span", { class: "muted" }, DASH),
      ],
    })),
  });
}

async function pageAttempts(main) {
  const log = await api("/attempts");
  const attempts = log.loans.reduce((sum, l) => sum + l.attempts.length, 0);
  main.replaceChildren(
    h(
      "div",
      { class: "page-head" },
      h("div", null, h("h1", null, "Sample and attempt log"), h("p", { class: "muted lead" }, "Which loans were drawn for a feedback call, how each draw can be repeated, and every attempt made to reach each customer. No attempt is made after day 30 from the sale.")),
    ),
    h(
      "section",
      { "aria-labelledby": "draws-h" },
      h("h2", { id: "draws-h" }, "Draws"),
      log.draws.length
        ? drawsTable(log.draws, "Each draw covers the sales made since the previous draw that are still within 30 days of the sale, so no sale is eligible twice.")
        : h("div", { class: "panel" }, h("p", null, "No draw has been made.")),
      h("p", { class: "small", style: "margin-top:8px" }, h("a", { href: `${API}/draws` }, "Raw selection audit (JSON)"), ": every eligible loan id, the seed and the loans drawn."),
    ),
    h(
      "section",
      { "aria-labelledby": "loans-h" },
      h("h2", { id: "loans-h" }, "Sampled loans"),
      h("p", { class: "small muted", style: "margin-bottom:10px" }, `${int(log.loans.length)} sampled loans, ${int(attempts)} attempts, in draw order. Each attempt shows its number, how it ended and the day since the sale.`),
      log.loans.length
        ? table({
            stack: true,
            long: true,
            cols: [
              { label: "Loan and draw", head: true },
              { label: "Sold on" },
              { label: "Language" },
              { label: "Branch and channel" },
              { label: "Attempts" },
              { label: "Final status" },
              { label: "Call outcome" },
              { label: "Case" },
            ],
            rows: log.loans.map((l) => ({
              cells: [
                [h("span", { class: "id nowrap" }, l.loan_id), h("span", { class: "sub id nowrap" }, `Draw ${l.draw_id}`)],
                [h("span", { class: "nowrap" }, fmtDate(l.sold_on)), h("span", { class: "sub nowrap" }, `day ${int(l.day_since_sale_at_draw)} at the draw`)],
                languageName(l.language),
                [h("span", { class: "nowrap" }, l.branch), h("span", { class: "sub" }, words(l.channel))],
                l.attempts.length
                  ? h(
                      "ol",
                      { class: "chips" },
                      l.attempts.map((a) =>
                        h(
                          "li",
                          { class: `chip${a.outcome === "completed" ? " done" : ""}`, title: fmtDateTime(a.at) },
                          h("b", null, a.number),
                          h("span", null, a.outcome_label),
                          h("span", { class: "muted" }, `day ${a.day_since_sale} \u00B7 ${a.simulated ? "simulated" : "phone call"}`),
                        ),
                      ),
                    )
                  : h("span", { class: "muted" }, "None"),
                l.status_label,
                l.tier_label ? h("span", { class: `tier tier-${l.tier}` }, l.tier_label) : h("span", { class: "muted" }, DASH),
                l.case_id ? h("a", { href: caseHref(l.case_id), class: "nowrap" }, "Open case") : h("span", { class: "muted" }, DASH),
              ],
            })),
          })
        : h("div", { class: "panel" }, h("p", null, "No loan has been sampled.")),
    ),
    h(
      "section",
      { "aria-labelledby": "outside-h" },
      h("h2", { id: "outside-h" }, `Calls outside the sample (${int(log.outside.length)})`),
      log.outside.length ? outsideTable(log.outside) : h("div", { class: "panel" }, h("p", null, "None. Every call in this batch was made to a sampled loan.")),
    ),
  );
}

// ---------------------------------------------------------------- the half-yearly report

const cssString = (s) => `"${String(s).replace(/[\\"]/g, "\\$&").replace(/[\r\n]+/g, " ")}"`;

function proportionTable({ caption, first, rows, bars = false }) {
  return table({
    caption,
    cols: [{ label: first, head: true }, { label: "Count", num: true }, { label: "Share", num: true }, { label: "95% interval", num: true, cls: "interval" }, ...(bars ? [{ label: "", cls: "bar-cell" }] : [])],
    rows: rows.map((r) => ({
      cells: [
        r.label,
        pCount(r.value),
        pShare(r.value),
        pInterval(r.value),
        ...(bars ? [h("span", { class: "bar", "aria-hidden": "true" }, h("span", { style: `width:${r.value.share === null ? 0 : Math.round(r.value.share * 100)}%` }))] : []),
      ],
    })),
  });
}

function section(id, title, ...kids) {
  return h("section", { "aria-labelledby": id }, h("h2", { id }, title), kids);
}

const TO_FILL = "To be filled in by the policy review";

async function pageReport(main) {
  const r = await api("/report");
  const lender = r.batch.meta.book.lender_name;
  const para = `para ${r.paragraph}`;
  const simulated = r.batch.simulated;
  document.title = `Half-yearly report \u00B7 ${lender} \u00B7 Samajh review`;

  // The running title on every printed page.
  const running = `${simulated ? "SIMULATED. " : "SYNTHETIC. "}${lender}: feedback under ${para}, ${r.period_label}`;
  document.head.append(
    h(
      "style",
      null,
      `@page { @top-left { content: ${cssString(running)}; font: 8pt system-ui, sans-serif; color: #000; } @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8pt system-ui, sans-serif; color: #000; } }`,
    ),
  );

  const f = r.funnel;
  const t = r.timing;
  const s = r.sampling;
  const previous = r.previous_period === null ? "No previous period" : r.previous_period;
  const findingRow = (x) => ({
    cells: [
      [x.statement, h("span", { class: "sub" }, x.rule_label)],
      x.seriousness_label,
      pCount(x.flagged),
      pShare(x.flagged),
      pInterval(x.flagged),
      `${int(x.undecided)} of ${int(x.flagged.n)}`,
      `${int(x.referred)} of ${int(x.flagged.count)}`,
      x.previous ? pBoth(x.previous) : h("span", { class: "muted" }, "None"),
      x.may_engage ? h("span", { class: "engage" }, x.may_engage) : h("span", { class: "muted" }, DASH),
    ],
  });
  const supported = r.referrals.find((row) => row.key === "concern_supported");
  const e = r.supported_of_decided;

  main.className = "report";
  main.replaceChildren(
    h(
      "div",
      { class: "page-head" },
      h(
        "div",
        null,
        h("p", { class: "eyebrow" }, `Feedback under ${para}`),
        h("h1", null, `Half-yearly report: ${lender}`),
        h("p", { class: "period" }, r.period_label),
        h("p", { class: "meta" }, r.coverage),
        h("p", { class: "meta" }, `As of ${fmtDate(r.as_of)} (synthetic date) \u00B7 batch `, h("span", { class: "id" }, r.batch.meta.batch_id)),
      ),
      h("button", { class: "btn no-print", type: "button", onclick: () => window.print() }, "Print or save as PDF"),
    ),
    h(
      "section",
      { class: "limits", "aria-labelledby": "limits-h" },
      h("h2", { id: "limits-h" }, "What this report is and is not"),
      h("p", { class: "sim" }, r.batch.simulated_notice),
      h("ul", null, r.limits.map((x) => h("li", null, x))),
      h("p", { class: "small muted" }, r.as_of_note),
    ),
    section(
      "mechanism-h",
      "The mechanism",
      facts([
        ["Run by", r.unit],
        ["Calls read by", r.reading.length ? h("ul", { class: "plain-list" }, r.reading.map((x) => h("li", null, `${x.key}: ${x.label}`))) : "No call was read"],
        ["Previous period", previous],
        ["Phone calls outside the sample", `${int(r.outside_calls)} (listed on the attempt log, not counted here)`],
      ]),
    ),
    section(
      "sampling-h",
      "Sampling",
      h(
        "p",
        null,
        `${int(s.sales_in_period)} sales were made in the period. ${int(s.eligible)} were eligible (a draw covered them) and ${int(s.sampled)} were sampled. ${int(s.sales_in_period - s.eligible)} were never eligible`,
        s.never_eligible.length ? `: ${s.never_eligible.map((x) => `${int(x.count)} ${x.reason}`).join("; ")}.` : ".",
      ),
      h("p", null, s.statement),
      r.draws.length ? drawsTable(r.draws, "Draws") : null,
    ),
    section(
      "reach-h",
      "Reach",
      h("p", null, `${int(f.attempts)} attempts were made on ${int(f.sampled)} sampled loans, retries included, none after day 30 from the sale. Every share below is of the ${int(f.sampled)} sampled loans.`),
      proportionTable({ caption: "How far the sampled loans got. Each stage is within the one before.", first: "Stage", rows: f.stages, bars: true }),
      proportionTable({ caption: "Where the loans without a completed call ended", first: "Final status", rows: f.exits, bars: true }),
    ),
    section(
      "timing-h",
      "Timing",
      h("p", null, "Days are counted from the sale to the attempt, not to the draw."),
      table({
        caption: "Timing against the 30-day window",
        cols: [{ label: "Measure", head: true }, { label: "Value", num: true }],
        rows: [
          {
            cells: [
              `Days from sale to first attempt, over the ${int(t.attempted)} loans attempted`,
              t.first_attempt_days ? `least ${t.first_attempt_days[0]}, median ${t.first_attempt_days[1]}, most ${t.first_attempt_days[2]}` : "No attempt made",
            ],
          },
          { cells: ["Attempts made after day 30 from the sale", cCount(t.attempts_after_window)] },
          { cells: ["Calls completed after day 30 (shown apart, not in the findings)", int(t.completed_late)] },
        ],
      }),
    ),
    section("tiers-h", "Outcome of the counted calls", proportionTable({ caption: "One outcome per call completed within 30 days of the sale", first: "Outcome", rows: r.tiers })),
    section(
      "findings-h",
      "Findings: features and risks",
      h("p", null, `${para} asks that the findings be used to review product features and risks. Each rule runs on every counted call. Undecided calls had a gap under the rule and no flag. Referred is the number of the flagged calls that went to a reviewer for that rule.`),
      h("p", { class: "notice" }, r.risk_note),
      h("p", { class: "small muted" }, r.seriousness_note),
      table({
        caption: "A paragraph is one that a line may engage. It is not a finding about any sale.",
        cols: [
          { label: "Customers who\u2026", head: true },
          { label: "Seriousness" },
          { label: "Count", num: true },
          { label: "Share", num: true },
          { label: "95% interval", num: true, cls: "interval" },
          { label: "Undecided", num: true },
          { label: "Referred, of those counted", num: true },
          { label: "Previous period", num: true },
          { label: "Paragraph" },
        ],
        rows: r.groups.flatMap((g) => {
          const rows = r.findings.filter((x) => x.group === g.key);
          return rows.length ? [{ group: g.label }, ...rows.map(findingRow)] : [];
        }),
      }),
    ),
    section(
      "referrals-h",
      "Referrals and reviewer decisions",
      h("p", null, "These are counts of one reviewer's decisions on each referred call, not estimates, so no interval is given."),
      table({
        caption: "Counted referrals by the reviewer's latest decision",
        cols: [{ label: "Decision", head: true }, { label: "Count", num: true }],
        rows: r.referrals.map((row) => ({ cells: [row.label, cCount(row.value)] })),
      }),
      h(
        "p",
        null,
        `${cCount(r.open_referrals)} counted referrals are open (no final decision yet). Of the ${int(e.n)} with a final decision, ${int(e.count)} were marked "${supported ? supported.label : ""}".`,
        r.other_referrals ? ` ${int(r.other_referrals)} further referred call(s) outside the sample or the window are in the reviewer queue and not counted here.` : "",
      ),
    ),
    section(
      "breakdowns-h",
      "Findings by loan kind, branch and channel",
      h("p", null, "Each row's shares are of its own counted calls, set against every other row together. Small rows give wide intervals; overlapping intervals show no clear difference."),
      r.breakdowns.map((b) =>
        table({
          caption: `By ${b.label.toLowerCase()}, against the rest`,
          cols: [
            { label: b.label, head: true },
            { label: "Counted calls", num: true },
            { label: "Referred", num: true },
            { label: "Rest: referred", num: true },
            { label: "Understanding gap", num: true },
            { label: "Rest: gap", num: true },
          ],
          rows: b.rows.map((row) => ({
            cells: [
              row.label,
              `${int(row.completed)} of ${int(row.sampled)} sampled`,
              withInterval(row.referred),
              withInterval(row.rest_referred),
              withInterval(row.understanding_gap),
              withInterval(row.rest_understanding_gap),
            ],
          })),
        }),
      ),
    ),
    section(
      "policy-h",
      "For policy review",
      h("p", null, `Under ${para} this report is used to review policies and product features and risks. Each finding is listed most serious first, then most common. The action, owner and review date are left for the policy review to fill in.`),
      r.policy_review.length
        ? h(
            "ol",
            { class: "policy" },
            r.policy_review.map((p) =>
              h(
                "li",
                null,
                h("p", { class: "sentence" }, `${p.seriousness_label}: ${p.sentence}`),
                h("p", { class: "detail" }, `${pCount(p.value)}, ${pShare(p.value)}; 95% interval ${pInterval(p.value)}`, p.highest ? `; ${p.highest}` : "", "."),
                facts([
                  ["Action", h("span", { class: "fill" }, TO_FILL)],
                  ["Owner", h("span", { class: "fill" }, TO_FILL)],
                  ["Review date", h("span", { class: "fill" }, TO_FILL)],
                  ["Previous period", previous],
                ]),
              ),
            ),
          )
        : h("p", { class: "muted" }, "No finding was counted in this batch."),
    ),
  );
}

// ---------------------------------------------------------------- start

const PAGES = { queue: pageQueue, case: pageCase, attempts: pageAttempts, report: pageReport };

async function start() {
  const page = document.body.dataset.page;
  const main = document.getElementById("main");
  let batch = null;
  try {
    batch = await api("/batch");
  } catch (err) {
    renderHeader(null, page);
    showError(main, err);
    return;
  }
  renderHeader(batch, page);
  try {
    await PAGES[page](main, batch);
  } catch (err) {
    if (!(err instanceof ApiError)) console.error(err);
    showError(main, err);
  }
}

start();
