// Same-origin calls to the local server. Every failure becomes one ApiError.

export class ApiError extends Error {
  constructor({ stage, code, message, retryable = false, upstream_status = null, status = null }) {
    super(String(message ?? ""));
    this.name = "ApiError";
    this.stage = stage;
    this.code = code;
    this.retryable = Boolean(retryable);
    this.upstreamStatus = upstream_status;
    this.status = status;
  }
}

async function send(path, init) {
  let res;
  try {
    res = await fetch(path, init);
  } catch (e) {
    throw new ApiError({
      stage: "network",
      code: "server_unreachable",
      message: `The local server did not answer (${e.message}).`,
      retryable: true,
    });
  }
  if (res.ok) return res;
  let err = null;
  try {
    err = (await res.json()).error;
  } catch {
    // not the contract's error body; reported below as the bare HTTP status
  }
  if (err && err.code) throw new ApiError({ ...err, status: res.status });
  throw new ApiError({
    stage: "request",
    code: `http_${res.status}`,
    message: res.statusText || "The server sent an error with no readable body.",
    status: res.status,
  });
}

async function json(path, init) {
  const res = await send(path, init);
  try {
    return await res.json();
  } catch (e) {
    throw new ApiError({
      stage: "request",
      code: "bad_response_body",
      message: `The server's reply was not JSON (${e.message}).`,
      status: res.status,
    });
  }
}

const postJson = (path, body) =>
  json(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

const session = (id) => `/api/sessions/${encodeURIComponent(id)}`;

export const api = {
  health: () => json("/api/health"),
  records: () => json("/api/records"),
  clips: async () => (await json("/api/clips")).clips,
  createSession: (settings) => postJson("/api/sessions", settings),
  endSession: (id) => postJson(`${session(id)}/end`, { reason: "hangup" }),
  logUrl: (id) => session(id),
  recordingUrl: (id) => `${session(id)}/recording.wav`,
  caseUrl: (id) => `${session(id)}/case`,
  startCase: (id) => json(`${session(id)}/case`, { method: "POST" }),
  getCase: (id) => json(`${session(id)}/case`),
  bytes: async (url) => (await send(url)).arrayBuffer(),
  clipBytes: (name) => api.bytes(`/api/clips/${encodeURIComponent(name)}`),
  // source "none" sends no body: nothing was said. `part` numbers the takes of one answer: a later,
  // longer take replaces the earlier one on the server. mode, cutMs and graceMs are logged only.
  postTurn(id, { source, body = null, eosWaitMs = null, replyTo = null, part = 1, mode = null, cutMs = null, graceMs = null }) {
    const query = new URLSearchParams({ source, part: String(part) });
    if (replyTo != null) query.set("reply_to", String(replyTo));
    if (eosWaitMs != null) query.set("eos_wait_ms", eosWaitMs.toFixed(1));
    if (mode != null) query.set("mode", mode);
    if (cutMs != null) query.set("cut_ms", String(cutMs));
    if (graceMs != null) query.set("grace_ms", String(graceMs));
    const init = body ? { method: "POST", headers: { "Content-Type": "audio/wav" }, body } : { method: "POST" };
    return json(`${session(id)}/turns?${query}`, init);
  },
};
