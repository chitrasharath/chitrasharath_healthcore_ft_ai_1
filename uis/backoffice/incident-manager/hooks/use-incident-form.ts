"use client";

import { useState } from "react";

import { createIncident } from "@backoffice/incident-manager/lib/incidents-api";
import type { IncidentCreate } from "@backoffice/incident-manager/types/incidents";

const EMPTY_FORM: IncidentCreate = {
  title: "",
  description: "",
  category: "ADMINISTRATIVE",
  origin: "customer",
  branch: "US-TX-01",
};

export const useIncidentForm = () => {
  const [form, setForm] = useState<IncidentCreate>(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);

  const update = (patch: Partial<IncidentCreate>) => {
    setForm((prev) => ({ ...prev, ...patch }));
    setFieldError(null);
    setError(null);
    setSuccess(null);
  };

  const submit = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    setFieldError(null);
    try {
      await createIncident(form);
      setForm(EMPTY_FORM);
      setSuccess("Incident logged successfully.");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      if (message.includes("Title")) setFieldError(message);
      else if (message.includes("Description")) setFieldError(message);
      else if (responseIsServer(message)) setError("Something went wrong. Please try again later.");
      else setError(message);
    } finally {
      setLoading(false);
    }
  };

  return { form, loading, success, error, fieldError, update, submit };
};

const responseIsServer = (message: string) =>
  message.toLowerCase().includes("unexpected error") || message === "Request failed";
