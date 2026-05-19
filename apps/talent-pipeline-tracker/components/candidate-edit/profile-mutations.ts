import { patchCandidate, replaceCandidate } from "@/lib/api";

import type { CandidateProfile } from "@/components/candidate-edit/profile-model";

type Notify = (kind: "success" | "error", message: string) => void;

type MutationOptions = {
  id: string;
  profile: CandidateProfile;
  notify: Notify;
};

export const savePipelineMutation = async ({ id, profile, notify }: MutationOptions) => {
  try {
    await patchCandidate(id, { status: profile.status, stage: profile.stage });
    notify("success", "Candidate status and stage updated.");
  } catch (error) {
    notify("error", error instanceof Error ? error.message : "Failed to update.");
    throw error;
  }
};

export const saveCorrectionsMutation = async ({ id, profile, notify }: MutationOptions) => {
  try {
    const yearsText = profile.experienceYears.trim();
    const experienceYears = Number.parseInt(yearsText, 10);
    if (!/^\d+$/.test(yearsText) || Number.isNaN(experienceYears) || experienceYears < 0) {
      throw new Error("Experience years must be a non-negative whole number.");
    }

    await replaceCandidate(id, {
      full_name: profile.fullName.trim(),
      email: profile.email.trim(),
      phone: profile.phone.trim(),
      position: profile.position.trim(),
      linkedin_url: profile.linkedinUrl.trim() || null,
      cv_url: profile.cvUrl.trim() || null,
      experience_years: experienceYears,
    });
    notify("success", "Candidate data corrected.");
  } catch (error) {
    notify("error", error instanceof Error ? error.message : "Failed to save candidate data.");
    throw error;
  }
};