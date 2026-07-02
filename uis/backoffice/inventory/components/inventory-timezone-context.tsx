"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import {
  DEFAULT_TIMEZONE,
  isValidTimezone,
  TIMEZONE_STORAGE_KEY,
} from "@backoffice/inventory/lib/timezones";

type InventoryTimezoneContextValue = {
  timezone: string;
  setTimezone: (value: string) => void;
};

const InventoryTimezoneContext = createContext<InventoryTimezoneContextValue | null>(null);

const readStoredTimezone = (): string => {
  if (typeof window === "undefined") return DEFAULT_TIMEZONE;
  const stored = localStorage.getItem(TIMEZONE_STORAGE_KEY);
  return stored && isValidTimezone(stored) ? stored : DEFAULT_TIMEZONE;
};

export const InventoryTimezoneProvider = ({ children }: { children: ReactNode }) => {
  const [timezone, setTimezoneState] = useState(DEFAULT_TIMEZONE);

  useEffect(() => {
    setTimezoneState(readStoredTimezone());
  }, []);

  const setTimezone = (value: string) => {
    if (!isValidTimezone(value)) return;
    setTimezoneState(value);
    localStorage.setItem(TIMEZONE_STORAGE_KEY, value);
  };

  return (
    <InventoryTimezoneContext.Provider value={{ timezone, setTimezone }}>
      {children}
    </InventoryTimezoneContext.Provider>
  );
};

export const useInventoryTimezone = (): InventoryTimezoneContextValue => {
  const context = useContext(InventoryTimezoneContext);
  if (!context) {
    throw new Error("useInventoryTimezone must be used within InventoryTimezoneProvider");
  }
  return context;
};
