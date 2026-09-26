from __future__ import annotations

import ast
from pathlib import Path
import re
from typing import Any

import pandas as pd

from core.utils import ensure_parent, write_json


def _as_list(value: Any) -> list[str]:
    """Normalize scalar/list-ish values into a clean list of strings."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [chunk.strip() for chunk in re.split(r",\s*|;\s*\|\s*|\|", text) if chunk.strip()]

    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()
    return [text] if text else []


def _safe_title(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text).strip()


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a balanced 10-item benchmark set from the cleaned paper dataframe."""
    if df is None or df.empty:
        raise ValueError("Cannot build test set from an empty dataframe.")

    required_cols = {"paper_id", "title", "summary", "published", "authors", "categories"}
    missing = sorted(required_cols - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns for eval set: {missing}")

    clean_df = df.copy()
    clean_df["paper_id"] = clean_df["paper_id"].fillna("").astype(str)
    clean_df["title"] = clean_df["title"].fillna("").astype(str)
    clean_df["summary"] = clean_df["summary"].fillna("").astype(str)
    clean_df["published"] = clean_df["published"].fillna("").astype(str)

    valid_mask = (
        clean_df["paper_id"].str.strip().ne("")
        & clean_df["title"].str.strip().ne("")
        & clean_df["summary"].str.strip().ne("")
        & clean_df["published"].str.strip().ne("")
    )
    clean_df = clean_df[valid_mask].copy()

    clean_df["authors_list"] = clean_df["authors"].map(_as_list)
    clean_df["categories_list"] = clean_df["categories"].map(_as_list)
    clean_df = clean_df[
        clean_df["authors_list"].map(len) > 0
        & clean_df["categories_list"].map(len) > 0
    ].copy()

    if len(clean_df) < 10:
        raise ValueError(f"Need at least 10 valid papers to build a benchmark set; found {len(clean_df)}.")

    # Keep the set balanced across the 4 question types: 3 + 3 + 2 + 2.
    type_counts = {"summary": 3, "authors": 3, "date": 2, "categories": 2}
    question_order = [
        question_type
        for question_type, count in type_counts.items()
        for _ in range(count)
    ]

    selected = clean_df.head(len(question_order)).reset_index(drop=True)
    test_set: list[dict[str, Any]] = []

    for index, question_type in enumerate(question_order):
        row = selected.iloc[index]
        title = _safe_title(row["title"])
        paper_id = str(row["paper_id"]).strip()
        authors = ", ".join(_as_list(row.get("authors_list", [])))
        categories = ", ".join(_as_list(row.get("categories_list", [])))
        summary = re.sub(r"\s+", " ", str(row["summary"])).strip()
        published = str(row["published"]).strip()

        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = summary
        elif question_type == "authors":
            question = f"Who are the authors of the paper '{title}'?"
            ground_truth = authors
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = published
        else:
            question = f"What categories or fields does the paper '{title}' belong to?"
            ground_truth = categories

        test_set.append(
            {
                "id": f"eval_{index + 1:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    output = Path(output_path)
    ensure_parent(output)
    write_json(output, test_set)
    return test_set
