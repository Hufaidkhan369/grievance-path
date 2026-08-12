"""Train & save the routing ML model (TF-IDF + MultinomialNB).

Generates a labelled corpus from the department keyword tables, department
descriptions, and any high-confidence complaints already in the database, then
trains and serialises a model to models/routing_model.joblib.

Run after seeding the database:

    ..\\.venv\\Scripts\\python.exe train_model.py

The running server loads this file at startup if present (falling back to an
in-memory model otherwise). Admins can also retrain from the UI
(POST /api/admin/train).
"""
from __future__ import annotations

import random
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

from app.config import settings
from app.database import init_db, fetch_all, fetch_one
from app.routing.classifier import normalize
from app.services.seed import seed

MODEL_PATH = Path(__file__).resolve().parent / "models" / "routing_model.joblib"

_DEPARTMENT_WORDS = {
    "MCD": "city municipal roads street garbage sanitation drain park civic",
    "PWD": "road highway bridge culvert construction building public works",
    "EB": "electricity power voltage transformer meter bill current supply",
    "WS": "water supply pipeline tanker drinking leakage contamination shortage",
    "POLICE": "police theft crime robbery harassment assault law order traffic missing",
    "HEALTH": "hospital doctor ambulance patient medicine vaccination health dengue",
    "EDU": "school college student teacher education scholarship exam hostel",
    "TRANS": "bus metro railway train auto transport fare route conductor station",
    "ENV": "environment pollution air noise plastic waste forest tree river",
    "CONSUMER": "consumer shop product defective warranty refund overcharge mrp bill quality",
    "AGRI": "farmer crop agriculture fertilizer seed subsidy irrigation insurance mandi",
    "REV": "land property revenue mutation patta registration stamp tax records tehsildar",
    "TELECOM": "mobile network internet broadband signal telecom tower call data",
    "RATIONS": "ration card pds grains lpg gas fair price shop subsidy food",
    "DM": "disaster flood cyclone earthquake rescue relief shelter evacuation emergency",
}

_TEMPLATES = [
    "{kw} is a serious problem in our area and nothing has been done about it.",
    "Please help us, {kw} has been going on for months.",
    "We are facing {kw} and the authorities are not responding.",
    "Complaint regarding {kw} near our locality, kindly take action.",
    "This is about {kw} which needs immediate attention from the department.",
    "There is a major issue of {kw} and we demand a resolution soon.",
    "Residents are suffering due to {kw}, please look into it.",
    "I want to report {kw} in our ward, it is getting worse every day.",
    "{kw} affecting many families here, urgent action required.",
    "Issue with {kw} at our place, please assign the right team.",
]


def _get_positive_keywords(department_id: int) -> list[str]:
    rows = fetch_all(
        "SELECT keyword FROM keywords WHERE department_id = ? AND is_negative = 0",
        (department_id,),
    )
    return [r["keyword"] for r in rows]


def _build_corpus() -> tuple[list[str], list[int], list[int]]:
    """Return (texts, labels, dept_ids) using keywords + demo complaints."""
    depts = fetch_all("SELECT id, code FROM departments ORDER BY id")
    corpus: list[str] = []
    labels: list[int] = []
    dept_ids: list[int] = []

    def add(text: str, label: int, dept_id: int) -> None:
        t = normalize(text)
        if len(t) < 3:
            return
        corpus.append(t)
        labels.append(label)
        dept_ids.append(dept_id)

    for d in depts:
        kws = _get_positive_keywords(d["id"])
        # Keyword phrases -> synthetic sentences
        for kw in kws:
            for _ in range(2):
                t = random.choice(_TEMPLATES).replace("{kw}", kw)
                add(t, d["id"], d["id"])
            add(kw, d["id"], d["id"])
        # Department vocabulary phrase
        words = _DEPARTMENT_WORDS.get(d["code"], "")
        if words:
            add(words, d["id"], d["id"])

    # Real high-confidence complaints already in the DB (strongest signals)
    rows = fetch_all(
        "SELECT title, description, department_id FROM complaints "
        "WHERE department_confidence >= 0.8 AND department_id IS NOT NULL LIMIT 300"
    )
    for r in rows:
        add(f"{r['title']} {r['description']}", r["department_id"], r["department_id"])

    # Hard negatives: for each complaint, other departments' keywords
    for r in rows:
        others = [d for d in depts if d["id"] != r["department_id"]]
        other = random.choice(others) if others else None
        if other:
            kws = _get_positive_keywords(other["id"])
            if kws:
                add(f"{random.choice(_TEMPLATES).replace('{kw}', random.choice(kws))}",
                    other["id"], other["id"])
    return corpus, labels, dept_ids


def train_and_save() -> dict:
    random.seed(42)
    corpus, labels, dept_ids = _build_corpus()
    if len(set(labels)) < 2:
        return {"ok": False, "message": "Not enough labelled samples to train."}

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True,
                                 token_pattern=r"[a-z0-9]+", max_features=8000)
    X = vectorizer.fit_transform(corpus)
    model = MultinomialNB(alpha=0.3)
    model.fit(X, labels)

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": model}, MODEL_PATH)
    return {"ok": True, "samples": len(corpus), "classes": sorted(set(labels)),
            "path": str(MODEL_PATH)}


def load_model() -> dict | None:
    if not MODEL_PATH.exists():
        return None
    data = joblib.load(MODEL_PATH)
    return data


if __name__ == "__main__":
    init_db()
    seed()
    result = train_and_save()
    print(result)
