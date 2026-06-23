import { ExternalLinkIcon } from "@backoffice/talent-tracker/components/icons";

type CandidateSummaryCardProps = {
  fullName: string;
  position: string;
  email: string;
  phone: string;
  linkedinUrl: string | null;
  cvUrl: string | null;
  status: string;
  stage: string;
  experienceYears: number;
  appliedAt: string;
};

export const CandidateSummaryCard = ({
  fullName,
  position,
  email,
  phone,
  linkedinUrl,
  cvUrl,
  status,
  stage,
  experienceYears,
  appliedAt,
}: CandidateSummaryCardProps) => {
  return (
    <section className="rounded-xl border border-[var(--hc-border)] bg-white p-4">
      <div className="mb-3 border-b border-[var(--hc-border)] pb-3">
        <h2 className="text-lg font-semibold">{fullName}</h2><p className="text-sm text-[var(--hc-text-muted)]">{position}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Phone:</strong> {phone}</p>
        <p><strong>Status:</strong> {status}</p>
        <p><strong>Stage:</strong> {stage}</p>
        <p><strong>Experience:</strong> {experienceYears} years</p>
        <p><strong>Applied:</strong> {new Date(appliedAt).toLocaleDateString()}</p>
        <ProfileLink label="LinkedIn" href={linkedinUrl} />
        <ProfileLink label="CV" href={cvUrl} />
      </div>
    </section>
  );
};

const ProfileLink = ({ label, href }: { label: string; href: string | null }) => {
  if (!href) {
    return <p><strong>{label}:</strong> Not provided</p>;
  }

  return (
    <p>
      <strong>{label}:</strong>{" "}
      <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-[var(--hc-brand)] hover:text-[var(--hc-brand-strong)]">
        Open link
        <ExternalLinkIcon className="h-4 w-4" />
      </a>
    </p>
  );
};
