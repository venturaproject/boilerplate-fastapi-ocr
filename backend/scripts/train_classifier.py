"""Train the ML document-type classifier used by OCR_CLASSIFIER=ml.

Layout of the training directory:

    <dir>/invoice/*.txt
    <dir>/cv/*.txt
    <dir>/payslip/*.txt
    ...

Each `.txt` is the OCR text of one document. Run:

    uv run --extra ml python scripts/train_classifier.py path/to/dir

Writes `app/services/ocr/models/classifier.joblib`.
"""

from __future__ import annotations

import pathlib
import sys

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

OUT = pathlib.Path(__file__).resolve().parent.parent / "app" / "services" / "ocr" / "models" / "classifier.joblib"


def main(root: str) -> None:
    base = pathlib.Path(root)
    texts: list[str] = []
    labels: list[str] = []
    for label_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        for txt in label_dir.glob("*.txt"):
            texts.append(txt.read_text(encoding="utf-8", errors="ignore"))
            labels.append(label_dir.name)

    if len({*labels}) < 2:
        raise SystemExit(f"Necesito >=2 clases con datos en {base}")

    pipe = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(lowercase=True, strip_accents="unicode", max_features=20_000, ngram_range=(1, 2)),
            ),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    pipe.fit(texts, labels)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, OUT)
    print(f"{len(texts)} docs / {len({*labels})} clases -> {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("uso: train_classifier.py <dir-con-subcarpetas-por-clase>")
    main(sys.argv[1])
