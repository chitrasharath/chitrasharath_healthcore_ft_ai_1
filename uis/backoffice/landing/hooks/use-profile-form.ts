import { useEffect, useState } from "react";

import { apiFetch, type UserProfile } from "@/lib/api";

export const formatAccountDate = (iso: string): string =>
  new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });

export const useProfileForm = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const loadProfile = async () => {
      try {
        const response = await apiFetch("/auth/me");
        if (!response.ok) {
          if (active) setError("Could not load profile.");
          return;
        }
        const data = (await response.json()) as UserProfile;
        if (active) {
          setUser(data);
          setName(data.name);
        }
      } catch {
        if (active) setError("Could not load profile.");
      } finally {
        if (active) setLoading(false);
      }
    };

    void loadProfile();
    return () => {
      active = false;
    };
  }, []);

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const response = await apiFetch(`/users/${user.id}`, {
        method: "PUT",
        body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        setError("Could not save profile.");
        return;
      }
      const updated = (await response.json()) as UserProfile;
      setUser(updated);
      setName(updated.name);
      setSaved(true);
    } catch {
      // 401 redirect handled by apiFetch
    } finally {
      setSaving(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    window.location.href = "/";
  };

  return { user, name, setName, loading, saving, saved, error, handleSave, logout };
};
