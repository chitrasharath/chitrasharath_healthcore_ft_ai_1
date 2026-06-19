"use client";

import { startTransition, useEffect, useState, type ReactNode } from "react";

const LOGIN_URL = "http://localhost:3004/login";

export const AuthGuard = ({ children }: { children: ReactNode }) => {
  const [isAuthed, setIsAuthed] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("token");
    if (urlToken) {
      localStorage.setItem("token", urlToken);
      params.delete("token");
      const cleanUrl = window.location.pathname + (params.toString() ? `?${params.toString()}` : "");
      window.history.replaceState({}, "", cleanUrl);
    }

    const token = localStorage.getItem("token");
    if (!token) {
      window.location.href = LOGIN_URL;
      return;
    }
    startTransition(() => setIsAuthed(true));
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
