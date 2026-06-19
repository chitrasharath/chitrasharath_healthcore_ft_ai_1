"use client";

import { useEffect, useState } from "react";

import { fetchCurrentUser, getStoredToken, type UserProfile } from "@/lib/api";

export const useLandingSession = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const loadSession = async () => {
      const storedToken = getStoredToken();
      if (!storedToken) {
        if (active) {
          setUser(null);
          setToken(null);
          setLoading(false);
        }
        return;
      }

      try {
        const profile = await fetchCurrentUser();
        if (!active) return;
        if (profile) {
          setUser(profile);
          setToken(storedToken);
        } else {
          setUser(null);
          setToken(null);
        }
      } catch {
        if (active) {
          setUser(null);
          setToken(null);
        }
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
    window.location.reload();
  };

  return { user, token, loading, logout };
};
