"use client";

import { useEffect, useState } from "react";

import { fetchCurrentUser, getStoredToken, type UserProfile } from "@/lib/api";
import { setTelemetryUserId } from "@backoffice/shared/lib/telemetry";

export const useLandingSession = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const loadSession = async () => {
      const storedToken = getStoredToken();
      if (!storedToken) {
        if (active) {
          setUser(null);
          setLoading(false);
        }
        return;
      }

      try {
        const profile = await fetchCurrentUser();
        if (!active) return;
        if (profile) setTelemetryUserId(String(profile.id));
        setUser(profile ?? null);
      } catch {
        if (active) setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    };

    void loadSession();
    return () => {
      active = false;
    };
  }, []);

  const logout = () => {
    localStorage.removeItem("token");
    window.location.href = "/";
  };

  return { user, loading, logout };
};
