/** @jest-environment node */

const ENDPOINT = "http://localhost:8000/api/v1/telemetry/events";

const mockFetch = jest.fn();
const mockSendBeacon = jest.fn(() => true);
const sessionStore = new Map<string, string>();

beforeAll(() => {
  global.fetch = mockFetch as unknown as typeof fetch;
  Object.defineProperty(global, "window", {
    configurable: true,
    value: global,
  });
  Object.defineProperty(global, "document", {
    configurable: true,
    value: {
      visibilityState: "visible",
      addEventListener: jest.fn(),
    },
  });
  Object.defineProperty(global.navigator, "sendBeacon", {
    configurable: true,
    value: mockSendBeacon,
  });
  Object.defineProperty(global, "sessionStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => sessionStore.get(key) ?? null,
      setItem: (key: string, value: string) => {
        sessionStore.set(key, value);
      },
      clear: () => sessionStore.clear(),
    },
  });
});

beforeEach(() => {
  jest.resetModules();
  mockFetch.mockReset();
  mockSendBeacon.mockReset();
  mockFetch.mockResolvedValue({ ok: true });
  process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT = ENDPOINT;
  sessionStore.clear();
});

afterEach(async () => {
  const mod = await import("@backoffice/shared/lib/telemetry");
  mod.__resetTelemetryForTests();
});

const loadTelemetry = async () => {
  const mod = await import("@backoffice/shared/lib/telemetry");
  mod.__resetTelemetryForTests();
  return mod;
};

describe("TelemetryService", () => {
  it("enriches events with schemaVersion 1.1.0", async () => {
    const { track, __getQueueForTests } = await loadTelemetry();

    track("supply_list_viewed", { item_count: 3 });

    const queued = __getQueueForTests();
    expect(queued).toHaveLength(1);
    expect(queued[0].schemaVersion).toBe("1.1.0");
    expect(queued[0].service).toBe("backoffice");
    expect(queued[0].event_type).toBe("supply_list_viewed");
    expect(queued[0].properties).toEqual({ item_count: 3 });
  });

  it("flushes stream events immediately", async () => {
    const { track, flush } = await loadTelemetry();

    track("user_login_failed", { reason: "invalid_credentials" });
    await flush();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(String(init.body)) as { events: { event_type: string }[] };
    expect(body.events[0].event_type).toBe("user_login_failed");
  });

  it("queues batch events until flush threshold", async () => {
    const { track, flush, __getQueueForTests, __getTelemetryConstantsForTests } =
      await loadTelemetry();
    const { MAX_QUEUE_SIZE } = __getTelemetryConstantsForTests();

    track("supply_list_viewed", { item_count: 1 });
    expect(__getQueueForTests()).toHaveLength(1);
    expect(mockFetch).not.toHaveBeenCalled();
    await flush();
    expect(mockFetch).toHaveBeenCalledTimes(1);

    mockFetch.mockClear();
    for (let i = 0; i < MAX_QUEUE_SIZE; i += 1) {
      track("orders_list_viewed", { item_count: i });
    }
    await flush();
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("retries failed posts with backoff", async () => {
    jest.useFakeTimers();
    mockFetch.mockResolvedValueOnce({ ok: false }).mockResolvedValueOnce({ ok: true });

    const { track, flush, __getTelemetryConstantsForTests } = await loadTelemetry();
    const { MAX_QUEUE_SIZE } = __getTelemetryConstantsForTests();

    for (let i = 0; i < MAX_QUEUE_SIZE; i += 1) {
      track("user_login_succeeded", {});
    }

    const flushPromise = flush();
    await jest.advanceTimersByTimeAsync(500);
    await flushPromise;

    expect(mockFetch).toHaveBeenCalledTimes(2);
    jest.useRealTimers();
  });

  it("stores session and user ids on enrich", async () => {
    const { initTelemetrySession, setTelemetryUserId, track, __getQueueForTests } =
      await loadTelemetry();

    initTelemetrySession("session-abc");
    setTelemetryUserId("7");
    track("user_login_succeeded", {});

    const [event] = __getQueueForTests();
    expect(event.sessionId).toBe("session-abc");
    expect(event.userId).toBe("7");
  });
});
