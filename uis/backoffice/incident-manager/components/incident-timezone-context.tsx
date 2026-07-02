"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import {
  DEFAULT_TIMEZONE,
  isValidTimezone,
  TIMEZONE_STORAGE_KEY,
} from "@backoffice/incident-manager/lib/timezones";

type IncidentTimezoneContextValue = {
  timezone: string;
  setTimezone: (value: string) => void;
};

const IncidentTimezoneContext = createContext<IncidentTimezoneContextValue | null>(null);

const readStoredTimezone = (): string => {
  if (typeof window === "undefined") return DEFAULT_TIMEZONE;
  const stored = localStorage.getItem(TIMEZONE_STORAGE_KEY);
  return stored && isValidTimezone(stored) ? stored : DEFAULT_TIMEZONE;
};

export const IncidentTimezoneProvider = ({ children }: { children: ReactNode }) => {
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
    <IncidentTimezoneContext.Provider value={{ timezone, setTimezone }}>
      {children}
    </IncidentTimezoneContext.Provider>
  );
};

export const useIncidentTimezone = (): IncidentTimezoneContextValue => {
  const context = useContext(IncidentTimezoneContext);
  if (!context) {
    throw new Error("useIncidentTimezone must be used within IncidentTimezoneProvider");
  }
  return context;
};
