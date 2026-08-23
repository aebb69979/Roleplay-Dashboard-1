"""
Merge Responses with the roster (Mapping 'Data' sheet) and compute scores.

Sale Code is a free-text field on the Form, so ~9% of historical rows are
dirty. classify_sale_code() sorts each raw value into one of:

  clean               - a plain numeric code, ready to join as-is
  extracted_from_text - digits with a name jammed on (e.g. "39134585ปิยังกูร
                         สิริโย") - digits are pulled out and cross-checked
                         against the roster name for a confidence signal
  ambiguous_suffix     - a "<code>-N" pattern (e.g. "39131042-2") - this is
                         NOT a real code, it's an evaluator's ad hoc way of
                         telling apart several reps evaluated under one
                         leader's code in a single session. Not resolvable
                         without asking the evaluator, so it's never
                         auto-matched - it always lands in the review queue.
  unparseable          - nothing usable found

Rows that aren't 'clean', plus any row whose code simply doesn't match the
roster (or matches a roster placeholder), are surfaced via `needs_review`
rather than silently dropped or mismatched.
"""
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from data import schema as s

_HONORIFICS = ["นางสาว", "นาย", "นาง", "น.ส."]

_CLEAN_RE = re.compile(r"^\d{6,}(\.0)?$")
_SUFFIX_RE = re.compile(r"^(\d{5,})\s*-\s*\d+$")
_GLUED_RE = re.compile(r"^(\d{6,})\s*(\S.*)$")


def _strip_honorific(name: str) -> str:
    name = name.strip()
    for h in _HONORIFICS:
        if name.startswith(h):
            return name[len(h):].strip()
    return name


@dataclass
class SaleCodeResult:
    code: float           # np.nan if not confidently resolvable
    confidence: str       # clean | extracted_from_text | ambiguous_suffix | unparseable
    extracted_name: str | None = None


def classify_sale_code(raw) -> SaleCodeResult:
    text = "" if raw is None else str(raw).strip()
    if not text:
        return SaleCodeResult(np.nan, "unparseable")

    if _CLEAN_RE.match(text):
        return SaleCodeResult(float(text.split(".")[0]), "clean")

    if _SUFFIX_RE.match(text):
        # Deliberately NOT resolved to a code - see module docstring.
        return SaleCodeResult(np.nan, "ambiguous_suffix")

    glued = _GLUED_RE.match(text)
    if glued:
        digits, name_part = glued.groups()
        return SaleCodeResult(float(digits), "extracted_from_text", _strip_honorific(name_part))

    return SaleCodeResult(np.nan, "unparseable")


def _names_plausibly_match(extracted: str | None, roster_name: str) -> bool:
    if not extracted or not isinstance(roster_name, str):
        return False
    extracted = _strip_honorific(extracted)
    roster_name = _strip_honorific(roster_name)
    if not extracted or not roster_name:
        return False
    return extracted in roster_name or roster_name in extracted


def _clean_mapping(mapping: pd.DataFrame) -> pd.DataFrame:
    mapping = mapping[~mapping["LOWER_Sale_Code2"].astype(str).str.strip().isin(s.ROSTER_PLACEHOLDER_CODES)].copy()
    mapping["sale_code_clean"] = pd.to_numeric(mapping["LOWER_Sale_Code2"], errors="coerce")
    mapping = mapping.dropna(subset=["sale_code_clean"])
    return mapping.drop_duplicates(subset="sale_code_clean", keep="last")


def build_dashboard_df(responses: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    df = responses.copy()

    classified = df["sale_code_raw"].apply(classify_sale_code)
    df["sale_code_clean"] = [r.code for r in classified]
    df["sale_code_confidence"] = [r.confidence for r in classified]
    df["sale_code_extracted_name"] = [r.extracted_name for r in classified]

    # For display: the clean numeric code where we have one, otherwise the
    # original raw text (e.g. "39129998-2") so ambiguous/unresolved rows
    # stay visually traceable instead of showing blank.
    df["sale_code_display"] = df["sale_code_clean"].apply(
        lambda v: str(int(v)) if pd.notna(v) else None
    )
    df["sale_code_display"] = df["sale_code_display"].fillna(df["sale_code_raw"])

    mapping_clean = _clean_mapping(mapping)
    df = df.merge(
        mapping_clean[["sale_code_clean", *s.MAPPING_KEEP_COLUMNS[:-3], "LOWER_FULL_Name_TH", "LOWER_DMS_Type2", "LOWER_Status"]],
        on="sale_code_clean",
        how="left",
    )

    df["roster_matched"] = df["LOWER_FULL_Name_TH"].notna()
    df["name_sanity_check_ok"] = df.apply(
        lambda r: _names_plausibly_match(r["sale_code_extracted_name"], r["LOWER_FULL_Name_TH"])
        if r["sale_code_confidence"] == "extracted_from_text"
        else True,
        axis=1,
    )
    df["needs_review"] = (
        (df["sale_code_confidence"] != "clean")
        | ~df["roster_matched"]
        | ~df["name_sanity_check_ok"]
    )

    for col in s.SCORE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["score_raw"] = df[s.SCORE_COLS].sum(axis=1, min_count=len(s.SCORE_COLS))
    df["score_pct"] = df["score_raw"] * 2
    df["passed"] = df["score_pct"] >= s.PASS_THRESHOLD_PCT

    return df
