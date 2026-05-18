import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { getCandidates } from "@/lib/api";
import type { CandidateStage, CandidateStatus } from "@/types/candidate";

import type { CandidateListState, CandidateQueryState } from "./types";
import { toQuery, withParams } from "./query-utils";

export const useCandidateList = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const query: CandidateQueryState = toQuery(searchParams);
  const [state, setState] = useState<CandidateListState>({ result: null, candidates: [], loading: true, error: "", totalPages: 1 });

  useEffect(() => {
    let active = true;

    const loadCandidates = async () => {
      setState((previous) => ({ ...previous, loading: true, error: "" }));

      try {
        const payload = await getCandidates({
          search: query.search || undefined,
          status: (query.status || undefined) as CandidateStatus | undefined,
          stage: (query.stage || undefined) as CandidateStage | undefined,
          page: query.page,
          limit: query.limit,
        });

        if (!active) return;

        setState({
          result: payload,
          candidates: payload.data,
          loading: false,
          error: "",
          totalPages: Math.max(1, Math.ceil(payload.total / payload.limit)),
        });
      } catch (fetchError) {
        if (!active) return;

        setState((previous) => ({
          ...previous,
          loading: false,
          error:
            fetchError instanceof Error
              ? fetchError.message
              : "Failed to load candidates.",
        }));
      }
    };

    loadCandidates();
    return () => {
      active = false;
    };
  }, [query.search, query.status, query.stage, query.page, query.limit]);

  const setQueryParam = (key: string, value: string) => {
    router.replace(withParams(searchParams, (next) => {
      if (!value || value === "all") next.delete(key);
      else next.set(key, value);
      next.set("page", "1");
    }), { scroll: false });
  };

  const clearFilters = () => {
    router.replace(withParams(searchParams, (next) => {
      next.delete("search");
      next.delete("status");
      next.delete("stage");
      next.set("page", "1");
    }), { scroll: false });
  };

  const setPage = (nextPage: number) => router.replace(withParams(searchParams, (next) => next.set("page", String(nextPage))), { scroll: false });
  const retry = () => router.replace(withParams(searchParams, () => undefined), { scroll: false });

  return { query, ...state, setQueryParam, clearFilters, setPage, retry };
};
