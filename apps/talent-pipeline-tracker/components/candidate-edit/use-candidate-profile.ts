import { useEffect, useState } from "react";

import { mapCandidateProfile, type CandidateProfile, initialProfile } from "@/components/candidate-edit/profile-model";
import { saveCorrectionsMutation, savePipelineMutation } from "@/components/candidate-edit/profile-mutations";
import { getCandidateById } from "@/lib/api";

type Notify = (kind: "success" | "error", message: string) => void;

export const useCandidateProfile = (
  id: string,
  reloadVersion: number,
  notify: Notify,
  requestReload: () => void,
) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState(initialProfile);

  useEffect(() => {
    let active = true;

    const loadProfile = async () => {
      setLoading(true);
      setError("");
      try {
        const candidate = await getCandidateById(id);
        if (active) setProfile(mapCandidateProfile(candidate));
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : "Failed to load data.");
      } finally {
        if (active) setLoading(false);
      }
    };

    loadProfile();
    return () => {
      active = false;
    };
  }, [id, reloadVersion]);

  const setField = <K extends keyof CandidateProfile>(field: K, value: CandidateProfile[K]) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
  };

  const savePipeline = async () => {
    setSaving(true);
    try {
      await savePipelineMutation({ id, profile, notify });
    } catch {
      // Mutation helper already reports errors via notify.
    } finally {
      setSaving(false);
    }
  };

  const saveCorrections = async () => {
    setSaving(true);
    try {
      await saveCorrectionsMutation({ id, profile, notify });
      requestReload();
    } catch {
      // Mutation helper already reports errors via notify.
    } finally {
      setSaving(false);
    }
  };

  return { loading, error, saving, profile, setField, savePipeline, saveCorrections };
};