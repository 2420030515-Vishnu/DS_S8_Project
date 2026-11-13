"""Reproducible exploratory analytics for the archived COVID-19 data.

Functions return ordinary Python values/DataFrames that can be consumed by
Flask services. They calculate from source rows and never embed findings.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .preprocessing import (DATASETS, coerce_numeric, derive_daily_change,
        is_aggregate_label, load_dataset, normalize_label, profile_all, state_daily_long)
except ImportError:  # `python data_science/eda.py ...`
    from preprocessing import (DATASETS, coerce_numeric, derive_daily_change,
        is_aggregate_label, load_dataset, normalize_label, profile_all, state_daily_long)


def _records(frame: pd.DataFrame) -> list[dict]:
    values = frame.replace({np.nan: None}).to_dict(orient="records")
    result = []
    for row in values:
        result.append({str(k): (v.strftime("%Y-%m-%d") if isinstance(v, (pd.Timestamp,)) else (v.item() if isinstance(v, np.generic) else v)) for k, v in row.items()})
    return result


def national_trends() -> dict:
    """National daily and cumulative series from the single national archive."""
    df = load_dataset("national_daily").dropna(subset=["Date"]).sort_values("Date")
    metric_cols = [c for c in df if c.startswith(("Daily ", "Total "))]
    for col in metric_cols: df[col] = coerce_numeric(df[col])
    return {"source": "backend/data/nation_level_daily.csv", "date_range": {
        "start": df.Date.min().strftime("%Y-%m-%d") if len(df) else None,
        "end": df.Date.max().strftime("%Y-%m-%d") if len(df) else None},
        "rows": _records(df[["Date", *metric_cols]])}


def state_comparison(metric: str = "Confirmed", as_of: str | None = None, limit: int | None = None) -> list[dict]:
    """Latest observed state cumulative values, excluding aggregate India rows."""
    df = load_dataset("states")
    if metric not in {"Confirmed", "Recovered", "Deceased", "Tested", "Other"}:
        raise ValueError("Unsupported state metric")
    df = df.dropna(subset=["Date", "State"])
    df = df[~df.State.map(is_aggregate_label)]
    if as_of:
        df = df[df.Date <= pd.Timestamp(as_of)]
    df[metric] = coerce_numeric(df[metric])
    latest = df.sort_values("Date", kind="stable").groupby(df.State.map(normalize_label), sort=False).tail(1)
    latest = latest.dropna(subset=[metric]).sort_values(metric, ascending=False, kind="stable")
    if limit is not None: latest = latest.head(max(0, int(limit)))
    return [{"state": str(r.State), "date": r.Date.strftime("%Y-%m-%d"), "metric": metric,
             "value": float(getattr(r, metric))} for r in latest.itertuples()]


def state_trends(metric: str = "Confirmed", states: list[str] | None = None) -> list[dict]:
    """Cumulative state source plus derived observed-row changes and gap flags."""
    if metric not in {"Confirmed", "Recovered", "Deceased", "Tested", "Other"}: raise ValueError("Unsupported state metric")
    df = load_dataset("states").dropna(subset=["Date", "State"])
    df = df[~df.State.map(is_aggregate_label)]
    if states:
        keys = {normalize_label(x) for x in states}
        df = df[df.State.map(normalize_label).isin(keys)]
    df[metric] = coerce_numeric(df[metric])
    changed = derive_daily_change(df.dropna(subset=[metric]), group_columns=["State"], date_column="Date", cumulative_column=metric)
    changed = changed.rename(columns={metric: "cumulative_value"})
    changed["daily_change"] = changed["daily_change"].where(~changed["is_observation_gap"])
    cols = ["Date", "State", "cumulative_value", "daily_change", "gap_days", "is_observation_gap", "is_negative_correction"]
    return _records(changed[cols])


def district_comparison(state: str | None = None, metric: str = "Confirmed", as_of: str | None = None) -> dict:
    """District cumulative observations; derived change is valid only between observations."""
    if metric not in {"Confirmed", "Recovered", "Deceased", "Tested", "Other"}: raise ValueError("Unsupported district metric")
    df = load_dataset("districts").dropna(subset=["Date", "State", "District"])
    if state: df = df[df.State.map(normalize_label) == normalize_label(state)]
    if as_of: df = df[df.Date <= pd.Timestamp(as_of)]
    if df.empty:
        return {"available": False, "reason": "No district observations match the selected filters.", "rows": []}
    df[metric] = coerce_numeric(df[metric])
    changed = derive_daily_change(df.dropna(subset=[metric]), group_columns=["State", "District"], date_column="Date", cumulative_column=metric)
    changed = changed.rename(columns={metric: "cumulative_value"})
    changed["daily_change"] = changed["daily_change"].where(~changed["is_observation_gap"])
    return {"available": True, "metric": metric, "interpretation": "Counts are cumulative snapshots. Daily change is returned only for consecutive calendar-day observations; gaps are explicitly flagged.",
            "rows": _records(changed[["Date", "State", "District", "cumulative_value", "daily_change", "gap_days", "is_observation_gap", "is_negative_correction"]])}


def testing_trends() -> dict:
    """National testing snapshots and source-reported positivity.

    No recalculated positivity is published: available case/testing totals have
    differing definitions and sparse/misaligned observation dates.
    """
    df = load_dataset("tests_daily").dropna(subset=["Tested As Of"]).sort_values("Tested As Of")
    cols = [c for c in ("Total Samples Tested", "Total Individuals Tested", "Total Positive Cases", "Test positivity rate") if c in df]
    for col in cols: df[col] = coerce_numeric(df[col])
    return {"source": "backend/data/tests_day_wise.csv", "date_range": {
        "start": df["Tested As Of"].min().strftime("%Y-%m-%d") if len(df) else None,
        "end": df["Tested As Of"].max().strftime("%Y-%m-%d") if len(df) else None},
        "positivity": {"field": "source-reported Test positivity rate", "recalculated": False,
                       "reason": "Case and testing series do not provide consistently compatible definitions and aligned observations."},
        "rows": _records(df[["Tested As Of", *cols]])}


def quality_report() -> dict:
    return profile_all()


def descriptive_statistics() -> dict:
    """Descriptive distributions for numeric measures, without imputing blanks."""
    result = {}
    for name in DATASETS:
        frame = load_dataset(name)
        measures = {}
        for col in frame.columns:
            if any(word in str(col).lower() for word in ("confirmed", "recovered", "deceased", "death", "tested", "positive", "negative", "cases", "samples", "active")):
                values = coerce_numeric(frame[col]).dropna()
                if len(values):
                    std = values.std()
                    measures[col] = {"count": int(len(values)), "mean": float(values.mean()), "std": None if pd.isna(std) else float(std),
                    "min": float(values.min()), "25%": float(values.quantile(.25)), "median": float(values.median()),
                    "75%": float(values.quantile(.75)), "max": float(values.max())}
        result[name] = measures
    return result


def data_quality_summary() -> dict:
    """Cross-source reconciliation counts; sources remain separate."""
    wide = state_daily_long()
    state_totals = wide[wide.state_code.eq("TT")].groupby(["Date_YMD", "Status"], dropna=False).daily_count.sum(min_count=1)
    backend = load_dataset("state_daily")
    status_map = {"Confirmed": "Confirmed", "Recovered": "Recovered", "Deceased": "Deceased"}
    checked = equal = 0
    # Verify matched dates/state codes where the format overlaps, without summing sources.
    for code in backend.State.dropna().unique():
        if code not in set(wide.state_code): continue
        sub = backend[backend.State.eq(code)]
        for _, row in sub.iterrows():
            rows = wide[(wide.state_code == code) & (wide.Date_YMD == row.Date)]
            for source_status, backend_col in status_map.items():
                a = rows.loc[rows.Status == source_status, "daily_count"]
                b = row.get(backend_col)
                if len(a) and pd.notna(b):
                    checked += 1; equal += int(float(a.iloc[0]) == float(b))
    return {"state_daily_overlap": {"compared_observations": checked, "exact_matches": equal,
        "mismatches": checked - equal, "note": "Comparison is a reconciliation check, not an additive merge."},
        "national_aggregate_observations": int(state_totals.notna().sum())}


def run_analysis(output_dir: str | Path) -> dict:
    """Write reproducible reports and plots into output_dir, never into sources."""
    try:
        from .visualization import create_all_figures
    except ImportError:
        from visualization import create_all_figures
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    report = {"profiles": quality_report(), "national": national_trends(),
              "state_comparison_confirmed": state_comparison("Confirmed", limit=15),
              "testing": testing_trends(), "reconciliation": data_quality_summary(),
              "descriptive_statistics": descriptive_statistics()}
    (out / "profile_and_eda.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    create_all_figures(out)
    return {"output_dir": str(out), "report": str(out / "profile_and_eda.json"), "figures": sorted(p.name for p in out.glob("*.png"))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "outputs")
    parser.add_argument("--profiles-only", action="store_true")
    args = parser.parse_args()
    if args.profiles_only:
        print(json.dumps(quality_report(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(run_analysis(args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__": main()
