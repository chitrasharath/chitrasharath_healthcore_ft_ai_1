"use client";

import { startTransition, useEffect, useState, type ReactNode } from "react";

import { fetchCurrentUser, getStoredToken } from "@/lib/api";

const LOGIN_URL = "/login";

export const AuthGuard = ({ children }: { children: ReactNode }) => {
  const [isAuthed, setIsAuthed] = useState(false);

  useEffect(() => {
    let active = true;

    const verifySession = async () => {
      const token = getStoredToken();
      if (!token) {
        window.location.href = LOGIN_URL;
        return;
      }

      try {
        const user = await fetchCurrentUser();
        if (!active) return;

        if (!user) {
          window.location.href = LOGIN_URL;
          return;
        }

        startTransition(() => setIsAuthed(true));
      } catch {
        if (!active) return;
        window.location.href = LOGIN_URL;
      }
    };

    void verifySession();
    return () => {
      active = false;
    };
  }, []);

  if (!isAuthed) {
    return (
      <div className="flex flex-1 items-center justify-center py-16">
        <p className="text-sm text-slate-500">Checking authentication…</p>
      </div>
    );
  }

  return <>{children}</>;
};
