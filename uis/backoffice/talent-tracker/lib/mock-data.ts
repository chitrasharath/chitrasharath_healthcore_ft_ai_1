import type { CandidateNote, CandidateRecord } from "@backoffice/talent-tracker/types/candidate";

export const sampleCandidates: CandidateRecord[] = [
  {
    id: "c-1001",
    full_name: "Ava Chen",
    email: "ava.chen@example.com",
    phone: "+1 555-0145",
    position: "Product Designer",
    linkedin_url: "https://linkedin.com/in/ava-chen",
    cv_url: "https://storage.example.com/cv/c-1001.pdf",
    experience_years: 4,
    status: "received",
    stage: "pending",
    notes_count: 1,
    applied_at: "2026-05-18T09:00:00.000Z",
  },
  {
    id: "c-1002",
    full_name: "Mateo Rivera",
    email: "mateo.rivera@example.com",
    phone: "+1 555-0177",
    position: "Frontend Engineer",
    linkedin_url: "https://linkedin.com/in/mateo-rivera",
    cv_url: "https://storage.example.com/cv/c-1002.pdf",
    experience_years: 6,
    status: "in_progress",
    stage: "technical_interview",
    notes_count: 2,
    applied_at: "2026-05-10T14:30:00.000Z",
  },
  {
    id: "c-1003",
    full_name: "Nina Patel",
    email: "nina.patel@example.com",
    phone: "+1 555-0119",
    position: "Recruiting Coordinator",
    linkedin_url: null,
    cv_url: "https://storage.example.com/cv/c-1003.pdf",
    experience_years: 3,
    status: "selected",
    stage: "offer_presented",
    notes_count: 0,
    applied_at: "2026-05-02T08:15:00.000Z",
  },
];

export const sampleNotesByCandidateId: Record<string, CandidateNote[]> = {
  "c-1001": [
    {
      id: "n-7000",
      record_id: "c-1001",
      content: "Portfolio review complete. Move to recruiter screen.",
      created_at: "2026-05-18T11:00:00.000Z",
    },
  ],
  "c-1002": [
    {
      id: "n-7001",
      record_id: "c-1002",
      content: "Strong portfolio review. Move forward to technical interview.",
      created_at: "2026-05-15T10:00:00.000Z",
    },
    {
      id: "n-7002",
      record_id: "c-1002",
      content: "Follow-up call complete. Available to start in 30 days.",
      created_at: "2026-05-17T15:20:00.000Z",
    },
  ],
  "c-1003": [],
};

export const findCandidateById = (id: string): CandidateRecord | undefined =>
  sampleCandidates.find((candidate) => candidate.id === id);
