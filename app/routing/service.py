"""Routing orchestrator: combines keyword + ML + optional LLM results."""
from __future__ import annotations

from ..config import settings
from ..database import fetch_one
from .classifier import KeywordClassifier, MLClassifier
from .llm import LLMRouter


class Router:
    def __init__(self):
        self.keyword = KeywordClassifier()
        self.ml = MLClassifier()
        self.llm = LLMRouter()

    def reload(self) -> None:
        self.keyword.reload()
        if settings.USE_ML:
            self.ml.build()

    def analyze(self, title: str, description: str) -> dict:
        """Return one best match with explanation. Method:
        classifier -> keyword (+ML boost) when ROUTER_DEFAULT is 'classifier'.
        llm        -> pure LLM (falls back to classifier on failure).
        hybrid     -> LLM first, cross-checked with classifier.
        """
        text = f"{title} {description}"
        kw_ranks = self.keyword.rank(text, top=3)
        ml_ranks = self.ml.predict(text, top=3) if self.ml.available else []

        # Merge keyword + ML: keyword score dominates, ML nudges ties.
        combined: dict[int, float] = {}
        method = "classifier"
        for i, r in enumerate(kw_ranks):
            combined[r["department_id"]] = r["confidence"] * (1.0 - 0.15 * i)
        if ml_ranks:
            method = "classifier+ml"
            ml_boost = 0.85  # ML only breaks ties, never overrides a clear keyword hit
            for r in ml_ranks:
                did = r["department_id"]
                combined[did] = max(combined.get(did, 0.0), r["confidence"] * ml_boost)

        best = max(combined.items(), key=lambda kv: kv[1]) if combined else (None, 0.0)
        best_id, best_conf = best

        kw_best = kw_ranks[0] if kw_ranks else None

        # ---- Optional LLM ----
        llm_result = self.llm.route(title, description) if self.llm.enabled else {"used": False}

        if llm_result.get("used"):
            method = "llm" if settings.ROUTER_DEFAULT == "llm" else "hybrid"
            llm_code = llm_result.get("department_code")
            llm_dept = fetch_one(
                "SELECT id, code, name FROM departments WHERE UPPER(code) = ?", (llm_code,)
            ) if llm_code else None
            llm_conf = float(llm_result.get("confidence", 0.0) or 0.0)

            if llm_dept and llm_conf >= settings.CONFIDENCE_ACCEPT:
                best_id, best_conf = llm_dept["id"], llm_conf
                best_dept = dict(llm_dept)
            elif best_id:
                # LLM failed or was unsure -> classifier result stands
                best_conf = max(best_conf, llm_conf)
                best_dept = fetch_one("SELECT id, code, name FROM departments WHERE id = ?", (best_id,))
        else:
            best_dept = fetch_one("SELECT id, code, name FROM departments WHERE id = ?", (best_id,)) if best_id else None

        if not best_dept:
            return {
                "department_id": None,
                "department_code": None,
                "department_name": None,
                "confidence": 0.0,
                "method": method,
                "matched_keywords": [],
                "explanation": "Could not confidently route this complaint to any department.",
                "low_confidence": True,
            }

        matched = kw_best["matched_keywords"] if kw_best else []
        explanation = (
            f"Routed by {method}. Matched keywords: {', '.join(matched) if matched else 'no strong keyword match'}. "
            f"Confidence {best_conf:.0%}."
        )
        if llm_result.get("reason"):
            explanation += f" LLM note: {llm_result['reason']}"

        return {
            "department_id": best_dept["id"],
            "department_code": best_dept["code"],
            "department_name": best_dept["name"],
            "confidence": round(min(best_conf, 1.0), 4),
            "method": method,
            "matched_keywords": matched,
            "explanation": explanation,
            "low_confidence": best_conf < settings.MIN_ROUTE_CONFIDENCE,
        }


router = Router()
