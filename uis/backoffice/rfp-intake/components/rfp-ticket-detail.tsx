"use client";

import type { TicketDetail } from "../types/rfp-intake";
import { RfpTicketBanners } from "./rfp-ticket-banners";

type Props = { detail: TicketDetail };

const asList = (value: unknown): string[] => {
  if (Array.isArray(value)) return value.map(String);
  return [];
};

export const RfpTicketDetail = ({ detail }: Props) => {
  const meta = detail.metadata;
  return (
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-800">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-slate-900">
          {meta?.client_name || detail.rfp_id}
        </h2>
        <p className="text-slate-600">
          Status: <span className="font-medium">{detail.status}</span> · {detail.ticket_id}
        </p>
      </header>

      <RfpTicketBanners detail={detail} />

      {meta ? (
        <dl className="grid gap-2 sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Program</dt>
            <dd>{meta.program_type || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Country</dt>
            <dd>{meta.client_country || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Population</dt>
            <dd>{meta.covered_population || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Departments</dt>
            <dd>{(meta.departments_needed || []).join(", ") || "—"}</dd>
          </div>
        </dl>
      ) : null}

      {detail.sections.map((section) => (
        <section key={section.department_id} className="space-y-1">
          <h3 className="font-medium capitalize text-slate-900">{section.department_id}</h3>
          <ul className="list-disc space-y-1 pl-5">
            {asList(section.key_aspects).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}

      {meta?.sales_summary ? (
        <section className="space-y-1">
          <h3 className="font-medium text-slate-900">What to ask whom</h3>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs">
            {JSON.stringify(meta.sales_summary, null, 2)}
          </pre>
        </section>
      ) : null}

      {meta?.markdown_preview ? (
        <section className="space-y-1">
          <h3 className="font-medium text-slate-900">Redacted preview</h3>
          <p className="whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs text-slate-700">
            {meta.markdown_preview}
          </p>
        </section>
      ) : null}
    </div>
  );
};
