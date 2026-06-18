"use client";

import { useCallback, useMemo, useState } from "react";

import { formatJson } from "@/lib/format-json";
import type { OperationDefinition, OperationResult, RawParamValue } from "@/lib/operation-types";
import { defaultParamValues, getOperations } from "@/lib/operations-registry";

function initialParamState(operation: OperationDefinition): Record<string, RawParamValue> {
  return defaultParamValues(operation);
}

export function useManualTestRunner() {
  const operations = useMemo(() => getOperations(), []);
  const [selectedId, setSelectedId] = useState(operations[0]?.id ?? "");
  const [paramValues, setParamValues] = useState<Record<string, RawParamValue>>(() =>
    initialParamState(operations[0] ?? { id: "", label: "", description: "", params: [], run: () => null })
  );
  const [latestResult, setLatestResult] = useState<OperationResult | null>(null);
  const [history, setHistory] = useState<OperationResult[]>([]);

  const selectedOperation = useMemo(
    () => operations.find((op) => op.id === selectedId) ?? operations[0],
    [operations, selectedId]
  );

  const selectOperation = useCallback(
    (id: string) => {
      const operation = operations.find((op) => op.id === id) ?? operations[0];
      setSelectedId(operation.id);
      setParamValues(initialParamState(operation));
    },
    [operations]
  );

  const setParam = useCallback((key: string, value: RawParamValue) => {
    setParamValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  const executeOperation = useCallback((operation: OperationDefinition, params: Record<string, RawParamValue>) => {
    const parameterSuffix = Object.keys(params).length === 0 ? "" : ` | params=${formatJson(params)}`;
    const result: OperationResult = {
      label: `${operation.label}${parameterSuffix}`,
      value: operation.run(params),
    };
    setLatestResult(result);
    setHistory((prev) => [...prev, result]);
  }, []);

  const runSelected = useCallback(() => {
    if (!selectedOperation) return;
    executeOperation(selectedOperation, paramValues);
  }, [executeOperation, paramValues, selectedOperation]);

  const runAll = useCallback(() => {
    operations.forEach((operation) => {
      executeOperation(operation, defaultParamValues(operation));
    });
  }, [executeOperation, operations]);

  const clearOutput = useCallback(() => {
    setLatestResult(null);
    setHistory([]);
  }, []);

  return {
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
  };
}
