"""Read-only, reusable preprocessing for the archived COVID-19 sources.

All cleaning occurs in memory. Source CSVs are never rewritten. Missing values
remain missing unless a caller explicitly chooses a domain-specific operation.
"""
from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Sources are deliberately not merged: several contain overlapping snapshots.
DATASETS = {
    "state_wise_daily": {"path": ROOT / "datasets/state_wise_daily.csv", "date": "Date_YMD", "key": ["Date_YMD", "Status"], "kind": "wide daily state/status counts", "authority": "Primary state daily incidence source; TT is the source's national aggregate."},
    "states": {"path": ROOT / "datasets/states.csv", "date": "Date", "key": ["Date", "State"], "kind": "state cumulative snapshots", "authority": "Primary long-run state cumulative series; India is an aggregate row."},
    "districts": {"path": ROOT / "datasets/districts.csv", "date": "Date", "key": ["Date", "State", "District"], "kind": "district cumulative snapshots", "authority": "Primary dated district series; observations are not necessarily daily."},
    "statewise_tested": {"path": ROOT / "datasets/statewise_tested_numbers_data.csv", "date": "Updated On", "key": ["Updated On", "State"], "kind": "irregular state testing snapshots", "authority": "Primary long-run state testing export; fields are sparse and update dates differ by state."},
    "complete": {"path": ROOT / "backend/data/complete.csv", "date": "Date", "key": ["Date", "Name of State / UT"], "kind": "state snapshot export", "authority": "Overlaps other exports; profile only, never combined into totals."},
    "district_latest": {"path": ROOT / "backend/data/district_level_latest.csv", "date": "Last_Updated", "key": ["State", "District"], "kind": "district latest snapshot", "authority": "Snapshot has no populated update dates in this archive."},
    "national_daily": {"path": ROOT / "backend/data/nation_level_daily.csv", "date": "Date", "key": ["Date"], "kind": "national daily and cumulative series", "authority": "Authoritative source for national daily and cumulative counts."},
    "patients": {"path": ROOT / "backend/data/patients_data.csv", "date": "Date Announced", "key": ["Patient Number"], "kind": "individual line-list", "authority": "Profile only. Not a reliable aggregate source; contains person-level fields and reused patient numbers."},
    "state_daily": {"path": ROOT / "backend/data/state_level_daily.csv", "date": "Date", "key": ["Date", "State"], "kind": "state daily counts", "authority": "Overlapping API archive; use as a reconciliation source, not additive with state_wise_daily."},
    "state_latest": {"path": ROOT / "backend/data/state_level_latest.csv", "date": "Last_Updated_Time", "key": ["State"], "kind": "state latest snapshot", "authority": "Snapshot export; Total is an aggregate row."},
    "tests_daily": {"path": ROOT / "backend/data/tests_day_wise.csv", "date": "Tested As Of", "key": ["Tested As Of"], "kind": "national testing snapshots", "authority": "National testing source; repeated dates are revisions/snapshots, not independent increments."},
    "tests_state": {"path": ROOT / "backend/data/tests_state_wise.csv", "date": "Updated On", "key": ["Updated On", "State"], "kind": "state testing snapshots", "authority": "Short state testing archive; sparse fields and repeated keys may represent revisions."},
}

DATE_FORMATS = {
    "state_wise_daily": ("%Y-%m-%d",), "states": ("%Y-%m-%d",),
    "districts": ("%Y-%m-%d",), "statewise_tested": ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"),
    "complete": ("%Y-%m-%d",), "district_latest": ("%d-%m-%Y", "%Y-%m-%d"),
    "national_daily": (), "patients": ("%d/%m/%Y", "%Y-%m-%d"),
    "state_daily": ("%d-%b-%y", "%Y-%m-%d"), "state_latest": ("%d/%m/%Y %H:%M:%S",),
    "tests_daily": ("%d/%m/%Y", "%Y-%m-%d"), "tests_state": ("%d/%m/%Y", "%Y-%m-%d"),
}
NUMERIC_NAMES = re.compile(r"confirmed|recover|deceased|death|active|tested|positive|negative|cases|samples|individuals|population|migrated|other|rate|per million|per thousand|num cases", re.I)


def parse_yearless_dates(values: pd.Series, initial_year: int = 2020) -> pd.Series:
    """Parse ordered archive labels like `30 January`, inferring year rollover."""
    year, previous, out = initial_year, None, []
    for value in values:
        if pd.isna(value) or not str(value).strip():
            out.append(pd.NaT); continue
        raw = str(value).strip()
        parsed = pd.to_datetime(raw, errors="coerce", format="%d %B %Y")
        if pd.isna(parsed): parsed = pd.to_datetime(raw, errors="coerce", format="%d %b %Y")
        if pd.isna(parsed):
            md = pd.to_datetime(raw + " 2000", errors="coerce", format="%d %B %Y")
            if pd.isna(md): md = pd.to_datetime(raw + " 2000", errors="coerce", format="%d %b %Y")
            if not pd.isna(md):
                if previous and previous[0] == 12 and md.month == 1: year += 1
                try:
                    parsed = md.replace(year=year)
                except ValueError:
                    # A yearless leap day outside an inferred leap year is invalid.
                    parsed = pd.NaT
        if not pd.isna(parsed):
            year = parsed.year; previous = (parsed.month, parsed.day)
        out.append(parsed)
    return pd.Series(pd.to_datetime(out), index=values.index)


def parse_date_series(values: pd.Series, dataset: str | None = None) -> pd.Series:
    """Parse a known source date column without ambiguous day/month guessing."""
    if dataset == "national_daily": return parse_yearless_dates(values)
    if dataset == "state_daily":
        # In this source, the Date field is e.g. `01-Apr-20`; permit ISO exports too.
        parsed = pd.to_datetime(values, format="%d-%b-%y", errors="coerce")
        fallback = pd.to_datetime(values, format="%Y-%m-%d", errors="coerce")
        return parsed.fillna(fallback)
    formats = DATE_FORMATS.get(dataset or "", ())
    if not formats:
        return pd.to_datetime(values, errors="coerce", format="mixed", dayfirst=True)
    result = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    for fmt in formats:
        result = result.fillna(pd.to_datetime(values, errors="coerce", format=fmt))
    return result


def coerce_numeric(values: pd.Series) -> pd.Series:
    """Convert numeric strings safely; blanks/invalids stay NaN, negatives stay intact."""
    text = values.astype("string").str.replace(",", "", regex=False).str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(text, errors="coerce")


def normalize_label(value) -> str:
    """Comparison key that trims/collapses whitespace but does not alias names."""
    if value is None or pd.isna(value): return ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def clean_label_series(series: pd.Series) -> pd.DataFrame:
    """Return both the untouched source label and a whitespace-clean display label."""
    original = series.copy()
    display = series.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    return pd.DataFrame({"original": original, "display": display, "key": display.map(normalize_label)})


@lru_cache(maxsize=24)
def _read_csv_cached(name: str, modified_ns: int, size: int) -> pd.DataFrame:
    del modified_ns, size
    spec = DATASETS[name]
    return pd.read_csv(spec["path"], low_memory=False)


def load_dataset(name: str, *, clean: bool = True) -> pd.DataFrame:
    """Load one registered source; cached raw read, returned data is a safe copy."""
    if name not in DATASETS: raise ValueError(f"Unknown dataset {name!r}. Choose from {', '.join(DATASETS)}")
    path = DATASETS[name]["path"]
    if not path.exists(): raise FileNotFoundError(f"Dataset not found: {path}")
    stat = path.stat()
    frame = _read_csv_cached(name, stat.st_mtime_ns, stat.st_size).copy(deep=True)
    if not clean: return frame
    date_col = DATASETS[name].get("date")
    if date_col in frame: frame[date_col] = parse_date_series(frame[date_col], name)
    for column in frame.columns:
        if NUMERIC_NAMES.search(str(column)) and column != date_col:
            frame[column] = coerce_numeric(frame[column])
    for column in ("State", "State_Name", "Name of State / UT", "District"):
        if column in frame:
            frame[f"{column}_original"] = frame[column]
            frame[column] = frame[column].astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    return frame


def profile_dataset(name: str) -> dict:
    """Detailed profile including raw duplicate counts, parsed coverage and quality flags."""
    raw = load_dataset(name, clean=False)
    spec = DATASETS[name]
    frame = load_dataset(name)
    date_col = spec.get("date")
    dates = parse_date_series(raw[date_col], name).dropna() if date_col in raw else pd.Series(dtype="datetime64[ns]")
    missing = raw.isna().sum()
    numeric = {}
    for col in raw.columns:
        if NUMERIC_NAMES.search(str(col)):
            values = coerce_numeric(raw[col]); valid = values.dropna()
            numeric[col] = {"valid": int(valid.size), "invalid_or_missing": int(values.isna().sum()),
                            "min": float(valid.min()) if len(valid) else None,
                            "median": float(valid.median()) if len(valid) else None,
                            "max": float(valid.max()) if len(valid) else None,
                            "negative_count": int((valid < 0).sum())}
    key = spec.get("key", [])
    duplicate_key_rows = int(raw.duplicated(key, keep=False).sum()) if key and all(c in raw for c in key) else None
    labels = {}
    for col in ("State", "State_Name", "Name of State / UT", "District", "Status"):
        if col in raw:
            values = raw[col].dropna().astype(str)
            stripped = values.str.replace(r"\s+", " ", regex=True).str.strip()
            # Preserve original labels; report suspicious whitespace and case-only variants.
            distinct = sorted(stripped.unique().tolist())
            near_matches = []
            if col in {"State", "State_Name", "Name of State / UT"} and len(distinct) <= 100:
                for i, left in enumerate(distinct):
                    for right in distinct[i + 1:]:
                        score = SequenceMatcher(None, normalize_label(left), normalize_label(right)).ratio()
                        if 0.86 <= score < 1:
                            near_matches.append({"left": left, "right": right, "similarity": round(score, 3)})
            labels[col] = {"distinct": int(values.nunique()), "whitespace_variants": int((values != stripped).sum()),
                           "casefold_collisions": int(stripped.groupby(stripped.str.casefold()).nunique().gt(1).sum()),
                           "near_match_candidates": near_matches, "examples": sorted(values.unique().tolist())[:80]}
    return {"dataset": name, "path": str(spec["path"].relative_to(ROOT)), "authority": spec.get("authority"),
            "kind": spec.get("kind"), "shape": {"rows": int(raw.shape[0]), "columns": int(raw.shape[1])},
            "dtypes": {str(c): str(t) for c, t in raw.dtypes.items()},
            "missing": {str(c): {"count": int(n), "percent": round(float(n / max(1, len(raw)) * 100), 3)} for c, n in missing.items() if n},
            "exact_duplicate_rows": int(raw.duplicated().sum()), "duplicate_key_rows": duplicate_key_rows,
            "date_coverage": {"column": date_col, "invalid_or_missing": int(len(raw) - len(dates)),
                              "start": dates.min().strftime("%Y-%m-%d") if len(dates) else None,
                              "end": dates.max().strftime("%Y-%m-%d") if len(dates) else None},
            "numeric": numeric, "labels": labels}


def profile_all() -> dict:
    return {name: profile_dataset(name) for name in DATASETS}


def deduplicate(frame: pd.DataFrame, keys: list[str], keep: str = "last") -> tuple[pd.DataFrame, int]:
    """Explicit key de-duplication helper; caller chooses policy and receives count removed."""
    if keep not in {"first", "last"}: raise ValueError("keep must be 'first' or 'last'")
    absent = [c for c in keys if c not in frame]
    if absent: raise KeyError(f"Missing deduplication keys: {absent}")
    result = frame.drop_duplicates(keys, keep=keep).copy()
    return result, len(frame) - len(result)


def derive_daily_change(frame: pd.DataFrame, *, group_columns: list[str], date_column: str,
                        cumulative_column: str, output_column: str = "daily_change") -> pd.DataFrame:
    """Difference cumulative observations within each group; never fills missing dates.

    Negative changes are retained and marked as revisions/corrections. `gap_days`
    reports elapsed calendar days, so a change across a gap is not mislabeled daily.
    """
    needed = [*group_columns, date_column, cumulative_column]
    missing = [col for col in needed if col not in frame]
    if missing: raise KeyError(f"Missing columns: {missing}")
    out = frame.copy()
    out[date_column] = pd.to_datetime(out[date_column], errors="coerce")
    out[cumulative_column] = coerce_numeric(out[cumulative_column])
    out = out.sort_values([*group_columns, date_column], kind="stable")
    grouped = out.groupby(group_columns, dropna=False, sort=False)
    out[output_column] = grouped[cumulative_column].diff()
    previous_dates = grouped[date_column].shift()
    out["gap_days"] = (out[date_column] - previous_dates).dt.days.astype("Int64")
    out["is_first_observation"] = out["gap_days"].isna()
    out["is_observation_gap"] = out["gap_days"].gt(1).fillna(False)
    out["is_negative_correction"] = out[output_column].lt(0).fillna(False)
    return out.reset_index(drop=True)


def state_daily_long() -> pd.DataFrame:
    """Unpivot the wide official state daily source, retaining state codes and TT."""
    frame = load_dataset("state_wise_daily")
    id_vars = [c for c in ("Date_YMD", "Date", "Status") if c in frame]
    long = frame.melt(id_vars=id_vars, var_name="state_code", value_name="daily_count")
    long["daily_count"] = coerce_numeric(long["daily_count"])
    long["is_national_aggregate"] = long["state_code"].eq("TT")
    return long


def is_aggregate_label(value) -> bool:
    return normalize_label(value) in {"india", "total", "all india", "tt"}
