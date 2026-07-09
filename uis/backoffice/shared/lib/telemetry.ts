const SCHEMA_VERSION = "1.1.0";
const SERVICE = "backoffice";
const FLUSH_INTERVAL_MS = 10_000;
const MAX_QUEUE_SIZE = 20;
const MAX_RETRIES = 3;
const SESSION_KEY = "telemetry_session_id";

const STREAM_EVENT_TYPES = new Set(["user_login_failed", "session_expired"]);

export type TelemetryEventPayload = {
  eventId: string;
  timestamp: string;
  sessionId: string;
  userId: string;
  event_type: string;
  schemaVersion: string;
  requestId: string;
  service: string;
  properties: Record<string, unknown>;
};

let queue: TelemetryEventPayload[] = [];
let cachedUserId = "";
let flushTimer: ReturnType<typeof setInterval> | null = null;
let visibilityBound = false;
let flushing = false;

const getEndpoint = (): string | null => process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT ?? null;

const getSessionId = (): string => {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(SESSION_KEY) ?? "";
};

const enrich = (eventType: string, properties: Record<string, unknown>): TelemetryEventPayload => ({
  eventId: crypto.randomUUID(),
  timestamp: new Date().toISOString(),
  sessionId: getSessionId(),
  userId: cachedUserId,
  event_type: eventType,
  schemaVersion: SCHEMA_VERSION,
  requestId: crypto.randomUUID(),
  service: SERVICE,
  properties,
});

const postEvents = async (events: TelemetryEventPayload[], attempt = 0): Promise<boolean> => {
  const endpoint = getEndpoint();
  if (!endpoint || events.length === 0) return true;

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
    });
    if (response.ok) return true;
  } catch {
    // Network errors are retried below; telemetry must not block the app.
  }

  if (attempt < MAX_RETRIES - 1) {
    const delay = 2 ** attempt * 500;
    await new Promise((resolve) => setTimeout(resolve, delay));
    return postEvents(events, attempt + 1);
  }
  return false;
};

const postEventsKeepalive = (events: TelemetryEventPayload[]): void => {
  const endpoint = getEndpoint();
  if (!endpoint || events.length === 0 || typeof window === "undefined") return;

  void fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ events }),
    keepalive: true,
  });
};

export const flush = async (): Promise<void> => {
  if (flushing || queue.length === 0) return;
  flushing = true;
  const batch = queue;
  queue = [];
  await postEvents(batch);
  flushing = false;
};

const flushBeacon = (): void => {
  if (queue.length === 0) return;
  const batch = queue;
  queue = [];
  postEventsKeepalive(batch);
};

export const flushTelemetryBeacon = (): void => {
  flushBeacon();
};

const ensureListeners = (): void => {
  if (typeof window === "undefined" || flushTimer) return;
  flushTimer = setInterval(() => void flush(), FLUSH_INTERVAL_MS);
  if (!visibilityBound) {
    visibilityBound = true;
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") flushBeacon();
    });
  }
};

export const setTelemetryUserId = (userId: string): void => {
  cachedUserId = userId;
};

export const initTelemetrySession = (sessionId: string): void => {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }
};

export const track = (eventType: string, properties: Record<string, unknown>): void => {
  if (typeof window === "undefined") return;
  ensureListeners();
  queue.push(enrich(eventType, properties));
  if (STREAM_EVENT_TYPES.has(eventType) || queue.length >= MAX_QUEUE_SIZE) {
    void flush();
  }
};

export const __resetTelemetryForTests = (): void => {
  queue = [];
  cachedUserId = "";
  flushing = false;
  if (flushTimer) {
    clearInterval(flushTimer);
    flushTimer = null;
  }
  visibilityBound = false;
};

export const __getQueueForTests = (): TelemetryEventPayload[] => queue;

export const __getTelemetryConstantsForTests = () => ({
  SCHEMA_VERSION,
  MAX_QUEUE_SIZE,
  STREAM_EVENT_TYPES,
});
