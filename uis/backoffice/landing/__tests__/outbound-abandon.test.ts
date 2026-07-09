import { emptyOutbound } from "@backoffice/inventory/lib/outbound-form-logic";
import {
  buildAbandonProperties,
  isOutboundDirty,
  trackOutboundAbandon,
} from "@backoffice/inventory/lib/outbound-abandon";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";
import {
  __getQueueForTests,
  __resetTelemetryForTests,
  flush,
} from "@backoffice/shared/lib/telemetry";

const product: MedicalSupply = {
  id: 1,
  name: "Gloves",
  category: "ppe",
  country: "US",
  unit: "box",
  stock: 10,
};

const sessionStore = new Map<string, string>();
const mockFetch = jest.fn();

describe("outbound abandon telemetry", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT = "http://localhost:8000/api/v1/telemetry/events";
    sessionStore.clear();
    mockFetch.mockReset();
    mockFetch.mockResolvedValue({ ok: true });
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
    __resetTelemetryForTests();
  });

  it("treats partial form as dirty when only supply or only quantity is filled", () => {
    expect(isOutboundDirty({ ...emptyOutbound(), supplyId: 1 })).toBe(true);
    expect(isOutboundDirty({ ...emptyOutbound(), quantity: "5" })).toBe(true);
    expect(isOutboundDirty({ ...emptyOutbound(), supplyId: 1, quantity: "5" })).toBe(false);
    expect(isOutboundDirty(emptyOutbound())).toBe(false);
  });

  it("tracks abandon when only a quantity is entered", async () => {
    const tracked = trackOutboundAbandon({ ...emptyOutbound(), quantity: "3" }, [product], "navigation");
    await flush();

    expect(tracked).toBe(true);
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    const payload = JSON.parse(String(init.body)) as {
      events: { properties: Record<string, unknown> }[];
    };
    expect(payload.events[0].properties).toEqual({
      clinic_id: 1,
      had_supply_selected: false,
      had_quantity: true,
      abandon_trigger: "navigation",
    });
  });

  it("does not track when both supply and quantity are filled", async () => {
    const tracked = trackOutboundAbandon(
      { ...emptyOutbound(), supplyId: 1, quantity: "5" },
      [product],
      "navigation",
    );
    await flush();
    expect(tracked).toBe(false);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("tracks abandon when only a supply is selected", async () => {
    const tracked = trackOutboundAbandon({ ...emptyOutbound(), supplyId: 1 }, [product], "navigation");
    await flush();

    expect(tracked).toBe(true);
    expect(__getQueueForTests()).toHaveLength(0);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    const payload = JSON.parse(String(init.body)) as {
      events: { event_type: string; properties: Record<string, unknown> }[];
    };
    expect(payload.events[0].event_type).toBe("supply_consumption_form_abandoned");
    expect(payload.events[0].properties).toEqual({
      clinic_id: 1,
      had_supply_selected: true,
      had_quantity: false,
      abandon_trigger: "navigation",
      jurisdiction: "us",
    });
  });

  it("returns false when no supply is selected", async () => {
    const tracked = trackOutboundAbandon(emptyOutbound(), [product], "navigation");
    await flush();
    expect(tracked).toBe(false);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("allows a later abandon after a no-op emit", async () => {
    let abandonEmitted = false;
    const emit = (fields: ReturnType<typeof emptyOutbound>) => {
      if (abandonEmitted) return;
      if (!isOutboundDirty(fields)) return;
      if (trackOutboundAbandon(fields, [product], "navigation")) {
        abandonEmitted = true;
      }
    };

    emit(emptyOutbound());
    expect(abandonEmitted).toBe(false);

    emit({ ...emptyOutbound(), supplyId: 1 });
    await flush();
    expect(abandonEmitted).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("builds abandon properties without jurisdiction when supply missing", () => {
    expect(
      buildAbandonProperties({ ...emptyOutbound(), supplyId: null }, [product], "tab_hidden"),
    ).toEqual({
      clinic_id: 1,
      had_supply_selected: false,
      had_quantity: false,
      abandon_trigger: "tab_hidden",
    });
  });
});
