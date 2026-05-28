import Link from "next/link";

export const HealthCoreLogo = () => {
  return (
    <Link href="/" className="inline-flex items-center gap-2 text-sky-800" aria-label="HealthCore Home">
      <svg className="h-7 w-7" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
        <rect x="2" y="2" width="44" height="44" rx="12" fill="#0C4A6E" />
        <path d="M24 12V36M12 24H36" stroke="#FFFFFF" strokeWidth="4" strokeLinecap="round" />
        <circle cx="24" cy="24" r="18" stroke="#67E8F9" strokeWidth="2" />
      </svg>
      <span className="text-lg font-bold tracking-tight">HealthCore</span>
    </Link>
  );
};