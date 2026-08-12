"""Complaint -> department routing.

Strategy (in order of sophistication, all available offline):
  1. Weighted keyword scoring (deterministic, explainable).
  2. TF-IDF + Naive-Bayes model trained on a corpus generated from the
     keyword tables (scikit-learn, optional).
  3. Optional LLM cross-check lives in `llm.py` and is orchestrated by `service.py`.
"""
from __future__ import annotations

import re
from collections import defaultdict

from ..database import fetch_all, fetch_one

_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^\w\s]")
_SPACE_RE = re.compile(r"\s+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with",
    "is", "are", "was", "were", "has", "have", "had", "been", "being", "be",
    "i", "me", "my", "we", "our", "us", "you", "your", "it", "its", "this",
    "that", "these", "those", "from", "by", "as", "but", "not", "so", "if",
    "please", "kindly", "very", "much", "there", "here", "about", "into",
}


def normalize(text: str) -> str:
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def _tokenize(text: str) -> set[str]:
    words = _WORD_RE.findall(normalize(text))
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def load_keyword_map() -> dict[int, list[dict]]:
    """department_id -> [{keyword, weight, is_negative}]"""
    rows = fetch_all(
        """
        SELECT k.department_id, k.keyword, k.weight, k.is_negative
        FROM keywords k JOIN departments d ON d.id = k.department_id
        """
    )
    mapping: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        mapping[r["department_id"]].append(r)
    return mapping


def _phrase_hit(norm_text: str, norm_keyword: str) -> bool:
    """Match a multi-word phrase by normalising both sides."""
    return norm_keyword in norm_text


class KeywordClassifier:
    def __init__(self, keyword_map: dict[int, list[dict]] | None = None):
        self.keyword_map = keyword_map or {}
        self._compiled: dict[int, dict] = {}
        if self.keyword_map:
            self._compile()

    def _compile(self) -> None:
        self._compiled = {}
        for dept_id, kws in self.keyword_map.items():
            self._compiled[dept_id] = {
                "positive": [(normalize(k["keyword"]), k["weight"]) for k in kws if not k["is_negative"]],
                "negative": [(normalize(k["keyword"]), k["weight"]) for k in kws if k["is_negative"]],
            }

    def reload(self) -> None:
        self.keyword_map = load_keyword_map()
        self._compile()

    def _ensure(self) -> None:
        if not self._compiled:
            self.reload()

    def score(self, text: str) -> dict:
        self._ensure()
        norm = normalize(text)
        raw: dict[int, float] = defaultdict(float)
        matched: dict[int, list[str]] = defaultdict(list)
        for dept_id, comp in self._compiled.items():
            score = 0.0
            hits: list[str] = []
            for keyword, weight in comp["positive"]:
                if _phrase_hit(norm, keyword):
                    score += weight
                    hits.append(keyword)
            for keyword, weight in comp["negative"]:
                if _phrase_hit(norm, keyword):
                    score -= weight
            if score != 0.0:
                raw[dept_id] = score
                if hits:
                    matched[dept_id] = hits
        return {"scores": dict(raw), "matched": dict(matched)}

    def rank(self, text: str, top: int = 3) -> list[dict]:
        result = self.score(text)
        scores = result["scores"]
        if not scores:
            return []
        max_score = max(scores.values())
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        out = []
        for dept_id, score in ranked[:top]:
            confidence = score / max_score if max_score > 0 else 0.0
            dept = fetch_one("SELECT * FROM departments WHERE id = ?", (dept_id,))
            if dept:
                out.append({
                    "department_id": dept_id,
                    "department_code": dept["code"],
                    "department_name": dept["name"],
                    "confidence": round(confidence, 4),
                    "score": score,
                    "matched_keywords": result["matched"].get(dept_id, []),
                })
        return out


class MLClassifier:
    """TF-IDF + MultinomialNB trained on a corpus derived from keyword tables.

    This is the 'learning' layer: even when a phrase is novel, nearby words
    (after stemming) nudge the complaint toward the right department.
    """

    def __init__(self):
        self.vectorizer = None
        self.model = None
        self.dept_labels: list[int] = []
        self.available = False
        self.trained_on = None  # 'saved' | 'built'

    def build(self, keyword_map: dict[int, list[dict]] | None = None) -> None:
        """Try the pre-trained saved model first (train_model.py), then fall
        back to an in-memory model built from the keyword tables."""
        if self._load_saved():
            return
        self._build_in_memory(keyword_map)

    def _load_saved(self) -> bool:
        try:
            from pathlib import Path
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB
            import joblib

            model_path = Path(__file__).resolve().parents[2] / "models" / "routing_model.joblib"
            if not model_path.exists():
                return False
            data = joblib.load(model_path)
            self.vectorizer = data["vectorizer"]
            self.model = data["model"]
            self.available = True
            self.trained_on = "saved"
            return True
        except Exception:
            self.available = False
            return False

    def _build_in_memory(self, keyword_map: dict[int, list[dict]] | None = None) -> None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB
        except Exception:
            self.available = False
            return

        keyword_map = keyword_map or load_keyword_map()
        corpus: list[str] = []
        labels: list[int] = []
        for dept_id, kws in keyword_map.items():
            positives = [k["keyword"] for k in kws if not k["is_negative"]]
            text = " ".join(positives)
            if not text.strip():
                continue
            corpus.append(text)
            labels.append(dept_id)
            # Add a synonym-style expansion so the model can generalise a bit
            corpus.append(f"complaint problem issue {text}")
            labels.append(dept_id)

        if len(corpus) < 4:
            self.available = False
            return

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            lowercase=True,
            token_pattern=r"[a-z0-9]+",
            max_features=4000,
        )
        X = self.vectorizer.fit_transform(corpus)
        self.model = MultinomialNB()
        self.model.fit(X, labels)
        self.dept_labels = sorted(set(labels))
        self.available = True
        self.trained_on = "built"

    def predict(self, text: str, top: int = 3) -> list[dict]:
        if not self.available:
            return []
        X = self.vectorizer.transform([normalize(text)])
        probs = self.model.predict_proba(X)[0]
        indexed = sorted(zip(self.model.classes_, probs), key=lambda p: p[1], reverse=True)
        out = []
        for dept_id, prob in indexed[:top]:
            dept = fetch_one("SELECT * FROM departments WHERE id = ?", (int(dept_id),))
            if dept:
                out.append({
                    "department_id": dept["id"],
                    "department_code": dept["code"],
                    "department_name": dept["name"],
                    "confidence": round(float(prob), 4),
                    "matched_keywords": [],
                })
        return out
