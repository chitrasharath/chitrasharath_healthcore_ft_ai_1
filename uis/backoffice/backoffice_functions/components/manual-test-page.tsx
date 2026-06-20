"use client";

import { BackofficeHeader } from "@backoffice/backoffice-functions/components/layout/backoffice-header";
import { ActionBar } from "@backoffice/backoffice-functions/components/manual-test/action-bar";
import { FunctionSelector } from "@backoffice/backoffice-functions/components/manual-test/function-selector";
import { HistoryPanel } from "@backoffice/backoffice-functions/components/manual-test/history-panel";
import { HowToRunPanel } from "@backoffice/backoffice-functions/components/manual-test/how-to-run-panel";
import { ParamControls } from "@backoffice/backoffice-functions/components/manual-test/param-controls";
import { ResultPanel } from "@backoffice/backoffice-functions/components/manual-test/result-panel";
import { useManualTestRunner } from "@backoffice/backoffice-functions/hooks/use-manual-test-runner";

export function ManualTestPage() {
  const {
    operations,
    selectedOperation,
    paramValues,
    latestResult,
    history,
    selectOperation,
    setParam,
    runSelected,
    runAll,
    clearOutput,
  } = useManualTestRunner();

  if (!selectedOperation) {
    return <p className="p-6 text-sm text-slate-700">No operations available.</p>;
  }

  return (
    <main className="mx-auto max-w-7xl p-6 md:p-10">
      <BackofficeHeader />
      <HowToRunPanel />
      <section className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-bold text-sky-800">Run functions with parameters</h2>
        <p className="mt-2 text-sm text-slate-700">
          Select a function, choose parameter values, then run it against the sample data from the milestone context.
        </p>
        <div className="mt-4">
          <FunctionSelector
            operations={operations}
            selectedId={selectedOperation.id}
            description={selectedOperation.description}
            onSelect={selectOperation}
          />
          <ParamControls operation={selectedOperation} values={paramValues} onChange={setParam} />
          <ActionBar onRunSelected={runSelected} onRunAll={runAll} onClear={clearOutput} />
        </div>
      </section>
      <section className="grid gap-4 md:grid-cols-2">
        <ResultPanel latestResult={latestResult} />
        <HistoryPanel history={history} />
      </section>
    </main>
  );
}
