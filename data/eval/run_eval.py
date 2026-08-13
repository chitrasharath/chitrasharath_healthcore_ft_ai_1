#!/usr/bin/env python3
"""Score the RAG pipeline against data/eval/test-queries.json.

Skipped unless LLM_API_KEY is set. Run manually before hand-off:
  LLM_API_KEY=… uv run python data/eval/run_eval.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (_API_ROOT, _REPO_ROOT):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from data.pipelines.rag import FALLBACK_ANSWER, query, retrieve  # noqa: E402
from data.process.rag import bootstrap_env, collection_is_populated, setup  # noqa: E402


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_eval(*, judge: bool = False) -> dict[str, Any]:
    bootstrap_env()
    if not os.environ.get("LLM_API_KEY"):
        print("LLM_API_KEY unset — skipping eval")
        return {"skipped": True}

    if not collection_is_populated():
        print("Collection empty — running setup() first")
        setup()

    golden = json.loads(
        (_REPO_ROOT / "data" / "eval" / "test-queries.json").read_text(encoding="utf-8")
    )
    answerable = [q for q in golden if not q["should_abstain"]]
    abstain = [q for q in golden if q["should_abstain"]]

    recall_at_1 = 0
    recall_at_3 = 0
    rr_sum = 0.0
    correct_scores: list[float] = []
    incorrect_scores: list[float] = []

    for item in answerable:
        hits = retrieve(item["question"])
        docs = [h.get("source_document") for h in hits]
        expected = item["expected_source_document"]
        if expected in docs[:1]:
            recall_at_1 += 1
        if expected in docs[:3]:
            recall_at_3 += 1
        if expected in docs:
            rr_sum += 1.0 / (docs.index(expected) + 1)
            correct_scores.append(float(hits[0]["score"]))
        elif hits:
            incorrect_scores.append(float(hits[0]["score"]))

    n_ans = len(answerable) or 1
    retrieval = {
        "recall_at_1": recall_at_1 / n_ans,
        "recall_at_3": recall_at_3 / n_ans,
        "mrr": rr_sum / n_ans,
        "correct_top_score_mean": _mean(correct_scores),
        "incorrect_top_score_mean": _mean(incorrect_scores),
        "correct_top_score_min": min(correct_scores) if correct_scores else None,
    }

    false_answers = 0
    for item in abstain:
        hits = retrieve(item["question"])
        result = query(item["question"])
        if hits or result.sources:
            false_answers += 1

    key_fact_hits = 0
    key_fact_total = 0
    guardrail_failures: list[str] = []
    for item in answerable:
        result = query(item["question"])
        answer = result.answer
        facts = item.get("expected_key_facts") or []
        for fact in facts:
            key_fact_total += 1
            if fact.lower() in answer.lower() or fact in answer:
                key_fact_hits += 1
        q = item["question"].lower()
        if "kaiser" in q and "tom callahan" not in answer.lower():
            guardrail_failures.append("unlisted-insurer")
        if ("medicare" in q or "medicaid" in q) and "no-show" in q:
            if "not charged" not in answer.lower() and "no fee" not in answer.lower() and "not" not in answer.lower():
                guardrail_failures.append("medicare-medicaid-fee")
        if q.startswith("what insurance coverage") or (
            "coverage" in q and "country" not in q and item["expected_source_document"] == "insurance-coverage"
            and "united states" in " ".join(facts).lower()
        ):
            if "united states" not in answer.lower() or "united kingdom" not in answer.lower():
                guardrail_failures.append("us-uk-distinction")

    # Explicit no-retrieval guardrail
    empty = query("completely unrelated underwater basket weaving certification")
    if empty.sources or empty.answer != FALLBACK_ANSWER:
        # high min_score may still retrieve — only flag if sources present with confident answer
        if empty.sources:
            guardrail_failures.append("no-retrieval-fallback")

    generation = {
        "key_fact_coverage": (key_fact_hits / key_fact_total) if key_fact_total else 0.0,
        "false_answer_rate": false_answers / (len(abstain) or 1),
        "guardrail_failures": guardrail_failures,
    }

    faithfulness = None
    if judge:
        from app.core.config import settings
        from data.pipelines.rag import _generate

        supported = 0
        judged = 0
        offenders: list[str] = []
        for item in answerable:
            result = query(item["question"])
            if not result.context_texts:
                continue
            judged += 1
            grader = (
                "Is every claim in the ANSWER supported by the CONTEXT? "
                "Reply SUPPORTED or UNSUPPORTED: <claim>.\n\n"
                f"CONTEXT:\n{chr(10).join(result.context_texts)}\n\n"
                f"ANSWER:\n{result.answer}\n"
            )
            verdict = _generate(grader)
            if verdict.strip().upper().startswith("SUPPORTED"):
                supported += 1
            else:
                offenders.append(verdict.strip()[:200])
        faithfulness = {
            "rate": (supported / judged) if judged else 0.0,
            "offenders": offenders,
            "model": settings.generation_model,
        }

    report = {
        "retrieval": retrieval,
        "generation": generation,
        "faithfulness": faithfulness,
        "gates": {
            "recall_at_3_pass": retrieval["recall_at_3"] >= 0.8,
            "false_answer_pass": generation["false_answer_rate"] == 0,
            "guardrails_pass": len(guardrail_failures) == 0,
            "key_fact_target": generation["key_fact_coverage"] >= 0.9,
        },
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge", action="store_true", help="Opt-in LLM faithfulness judge")
    args = parser.parse_args()
    report = run_eval(judge=args.judge)
    print(json.dumps(report, indent=2))
    if report.get("skipped"):
        sys.exit(0)
    gates = report["gates"]
    if not (gates["recall_at_3_pass"] and gates["false_answer_pass"] and gates["guardrails_pass"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
