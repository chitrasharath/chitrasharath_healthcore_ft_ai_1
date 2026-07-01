"use client";

import { useEffect, useState } from "react";

import { getIncident, updateIncident } from "@backoffice/incident-manager/lib/incidents-api";
import type { IncidentCreate } from "@backoffice/incident-manager/types/incidents";

export const useIncidentEdit = (incidentId: number) => {
  const [form, setForm] = useState<IncidentCreate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);

  useEffect(() => {
    void getIncident(incidentId)
      .then((incident) =>
        setForm({
          title: incident.title,
          description: incident.description,
          category: incident.category,
          origin: incident.origin,
          branch: incident.branch,
        }),
      )
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load incident"))
      .finally(() => setLoading(false));
  }, [incidentId]);

  const update = (patch: Partial<IncidentCreate>) => {
    setForm((prev) => (prev ? { ...prev, ...patch } : prev));
    setFieldError(null);
    setError(null);
    setSuccess(null);
  };

  const submit = async () => {
    if (!form) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    setFieldError(null);
    try {
      await updateIncident(incidentId, form);
      setSuccess("Incident updated successfully.");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      if (message.includes("Title") || message.includes("Description")) setFieldError(message);
      else setError(message.includes("unexpected error") ? "Something went wrong. Please try again later." : message);
    } finally {
      setSaving(false);
    }
  };

  return { form, loading, saving, error, success, fieldError, update, submit };
};
