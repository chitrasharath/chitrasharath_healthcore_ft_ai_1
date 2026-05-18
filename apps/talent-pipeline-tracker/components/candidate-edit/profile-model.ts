import type { CandidateStage, CandidateStatus } from "@/types/candidate";

type CandidateResponse = {
  full_name: string;
  position: string;
  email: string;
  phone: string;
  linkedin_url: string | null;
  cv_url: string | null;
  experience_years: number;
  applied_at: string;
  status: CandidateStatus;
  stage: CandidateStage;
};

export type CandidateProfile = {
  fullName: string;
  position: string;
  email: string;
  phone: string;
  linkedinUrl: string;
  cvUrl: string;
  experienceYears: number;
  appliedAt: string;
  status: CandidateStatus;
  stage: CandidateStage;
};

export const initialProfile: CandidateProfile = {
  fullName: "Candidate",
  position: "",
  email: "",
  phone: "",
  linkedinUrl: "",
  cvUrl: "",
  experienceYears: 0,
  appliedAt: new Date().toISOString(),
  status: "received",
  stage: "pending",
};

export const mapCandidateProfile = (candidate: CandidateResponse): CandidateProfile => ({
  fullName: candidate.full_name,
  position: candidate.position,
  email: candidate.email,
  phone: candidate.phone,
  linkedinUrl: candidate.linkedin_url || "",
  cvUrl: candidate.cv_url || "",
  experienceYears: candidate.experience_years,
  appliedAt: candidate.applied_at,
  status: candidate.status,
  stage: candidate.stage,
});