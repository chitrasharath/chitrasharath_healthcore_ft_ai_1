import { PUBLIC_WEBSITE_URL } from "@/lib/public-website-url";

const BULLETS = [
  "Secure access to internal dashboards and operational tools",
  "Central hub for HealthCore Digital applications",
  "Account and credential management in one place",
];

export const PublicIntro = () => (
  <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
    <h2 className="text-lg font-bold text-slate-900">Internal staff portal</h2>
    <p className="mt-3 text-sm leading-6 text-slate-600">
      HealthCore Back Office is for authorized HealthCore staff. Sign in to access internal operational tools,
      dashboards, and administration workflows.
    </p>
    <ul className="mt-5 space-y-2">
      {BULLETS.map((item) => (
        <li key={item} className="flex gap-2 text-sm text-slate-700">
          <span aria-hidden="true" className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-700" />
          {item}
        </li>
      ))}
    </ul>
    <p className="mt-6 text-sm text-slate-600">
      Looking for patient information?{" "}
      <a href={PUBLIC_WEBSITE_URL} className="font-semibold text-sky-700 underline-offset-2 hover:underline">
        Visit the public HealthCore website
      </a>
      .
    </p>
    <p className="mt-4 text-sm text-slate-500">Use Log In or Register above to get started.</p>
  </section>
);
