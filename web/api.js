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
  clips: async () => (await json("/api/clips")).clips,
  createSession: (settings) => postJson("/api/sessions", settings),
  endSession: (id) => postJson(`${session(id)}/end`, { reason: "hangup" }),
  logUrl: (id) => session(id),
  recordingUrl: (id) => `${session(id)}/recording.wav`,
  bytes: async (url) => (await send(url)).arrayBuffer(),
  clipBytes: (name) => api.bytes(`/api/clips/${encodeURIComponent(name)}`),
  // source "none" sends no body: nothing was said.
  postTurn(id, { source, body = null, eosWaitMs = null, replyTo = null }) {
    const query = new URLSearchParams({ source });
    if (replyTo != null) query.set("reply_to", String(replyTo));
    if (eosWaitMs != null) query.set("eos_wait_ms", eosWaitMs.toFixed(1));
    const init = body ? { method: "POST", headers: { "Content-Type": "audio/wav" }, body } : { method: "POST" };
    return json(`${session(id)}/turns?${query}`, init);
  },
};
