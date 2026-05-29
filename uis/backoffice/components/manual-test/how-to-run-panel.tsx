export function HowToRunPanel() {
  return (
    <section className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">How to run</h2>
      <ol className="mt-2 list-decimal pl-5 text-sm text-slate-700">
        <li>
          Start dev server:{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5">cd uis/backoffice &amp;&amp; npm run dev</code>
        </li>
        <li>Open this page at the URL shown in the terminal (default port 3001).</li>
      </ol>
      <p className="mt-2 text-xs text-slate-500">
        Legacy browser page remains at <code className="rounded bg-slate-100 px-1">apps/src/index.html</code> with
        compile + refresh workflow.
      </p>
    </section>
  );
}
