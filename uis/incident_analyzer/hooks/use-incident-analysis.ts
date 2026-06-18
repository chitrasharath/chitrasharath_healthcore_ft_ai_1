"use client";

import { useState } from "react";

import { analyzeIncidents, exportAnalysisResults } from "@/lib/api";
import type { IncidentAnalysisResponse } from "@/lib/types";

export const useIncidentAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IncidentAnalysisResponse | null>(null);

  const upload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Invalid file format. Upload a CSV file.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeIncidents(file));
    } catch (uploadError) {
      setResult(null);
      setError(uploadError instanceof Error ? uploadError.message : "Unable to analyze file.");
    } finally {
      setLoading(false);
    }
  };

  const exportResults = async () => {
    setExporting(true);
    setError(null);
    try {
      const blob = await exportAnalysisResults();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "incident-analysis-export.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Unable to export results.");
    } finally {
      setExporting(false);
    }
  };

  return { loading, exporting, error, result, upload, exportResults };
};
