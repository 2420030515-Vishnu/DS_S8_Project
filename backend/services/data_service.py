"""Validated, cached data access for the archived India COVID-19 CSVs.

Authoritative sources are intentionally separated: national counts come from
nation_level_daily.csv; state time series from state_level_daily.csv; state and
district current snapshots from their *_latest.csv files; and testing from
tests_day_wise.csv / tests_state_wise.csv. The overlapping `complete.csv` and
root `datasets/` exports are not added to these totals.
"""
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import re

import numpy as np
import pandas as pd

try:
    from data_science.preprocessing import coerce_numeric, normalize_label, parse_date_series
except ImportError:  # running with backend/ as the import root
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from data_science.preprocessing import coerce_numeric, normalize_label, parse_date_series


class DataUnavailableError(RuntimeError):
    """A required source file is absent or cannot be decoded/processed."""


class QueryValidationError(ValueError):
    """A requested data filter or metric is invalid."""


DATASETS = {
    "national": {"file": "nation_level_daily.csv", "date": "Date", "source": "National daily archive"},
    "states": {"file": "state_level_daily.csv", "date": "Date", "source": "State daily archive"},
    "state_snapshot": {"file": "state_level_latest.csv", "date": "Last_Updated_Time", "source": "State latest snapshot"},
    "districts": {"file": "district_level_latest.csv", "date": "Last_Updated", "source": "District latest snapshot"},
    "testing": {"file": "tests_day_wise.csv", "date": "Tested As Of", "source": "National testing archive"},
    "testing_states": {"file": "tests_state_wise.csv", "date": "Updated On", "source": "State testing archive"},
}

EXPLORER_DATASETS = {key: key for key in ("national", "states", "districts", "testing", "testing_states")}
NUMERIC_COLUMNS = {
    "national": ("Daily Confirmed", "Total Confirmed", "Daily Recovered", "Total Recovered", "Daily Deceased", "Total Deceased"),
    "states": ("Confirmed", "Deceased", "Recovered"),
    "state_snapshot": ("Confirmed", "Recovered", "Deaths", "Active", "Migrated_Other", "Delta_Confirmed", "Delta_Recovered", "Delta_Deaths"),
    "districts": ("Confirmed", "Active", "Recovered", "Deceased", "Migrated_Other", "Delta_Confirmed", "Delta_Active", "Delta_Recovered", "Delta_Deceased"),
    "testing": ("Total Samples Tested", "Total Individuals Tested", "Total Positive Cases", "Sample Reported today", "Positive cases from samples reported", "Test positivity rate", "Tests per million"),
    "testing_states": ("Total Tested", "Positive", "Negative", "Unconfirmed", "Test positivity rate", "Tests per thousand", "Tests per million", "Population NCP 2019 Projection"),
}


def _normal_path(data_dir, filename):
    return (Path(data_dir) / filename).resolve()


@lru_cache(maxsize=32)
def _read_csv_cached(path_text, modified_ns, size):
    """Cache immutable raw reads by path and file fingerprint."""
    del modified_ns, size
    try:
        return pd.read_csv(path_text, low_memory=False)
    except (OSError, UnicodeError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DataUnavailableError(f"Dataset could not be read: {Path(path_text).name}") from exc


@lru_cache(maxsize=32)
def _prepared_cached(key, path_text, modified_ns, size):
    raw = _read_csv_cached(path_text, modified_ns, size).copy()
    try:
        frame = _prepare(key, raw)
    except (KeyError, TypeError, ValueError, pd.errors.ParserError) as exc:
        raise DataUnavailableError(f"Dataset has an unsupported or malformed schema: {Path(path_text).name}") from exc
    return frame


def _date_without_year(values, initial_year=2020):
    """Compatibility wrapper around the shared archive date parser."""
    from data_science.preprocessing import parse_yearless_dates
    return parse_yearless_dates(values, initial_year=initial_year)


def _parse_dates(values, sequential=False):
    if sequential:
        return parse_date_series(values, "national_daily")
    return pd.to_datetime(values, errors="coerce", format="mixed", dayfirst=True)


def normalize_state(value):
    """Comparison key only; callers retain and return the original source label."""
    return normalize_label(value)


def _prepare(key, frame):
    date_column = DATASETS[key]["date"]
    if date_column not in frame.columns:
        raise KeyError(date_column)
    frame[date_column] = _parse_dates(frame[date_column], sequential=(key == "national"))
    for column in NUMERIC_COLUMNS.get(key, ()):
        if column in frame.columns:
            frame[column] = coerce_numeric(frame[column])
    if key == "states":
        if "State_Name" not in frame.columns:
            raise KeyError("State_Name")
        frame["_state_key"] = frame["State_Name"].map(normalize_state)
        frame = frame.dropna(subset=[date_column]).drop_duplicates([date_column, "_state_key"], keep="last")
    elif key == "national":
        frame = frame.dropna(subset=[date_column]).drop_duplicates([date_column], keep="last")
    elif key == "state_snapshot":
        if "State" not in frame.columns:
            raise KeyError("State")
        frame["_state_key"] = frame["State"].map(normalize_state)
        frame = frame[frame["_state_key"] != "total"]
        frame = frame.drop_duplicates(["_state_key"], keep="last")
    elif key == "districts":
        if not {"State", "District"}.issubset(frame.columns):
            raise KeyError("State/District")
        frame["_state_key"] = frame["State"].map(normalize_state)
        frame["_district_key"] = frame["District"].map(normalize_state)
        frame = frame.drop_duplicates(["_state_key", "_district_key"], keep="last")
    elif key == "testing_states":
        if "State" not in frame.columns:
            raise KeyError("State")
        frame["_state_key"] = frame["State"].map(normalize_state)
        frame = frame.dropna(subset=[date_column]).drop_duplicates(["_state_key", date_column], keep="last")
    elif key == "testing":
        frame = frame.dropna(subset=[date_column]).drop_duplicates([date_column], keep="last")
    return frame.sort_values(date_column, kind="stable", na_position="last").reset_index(drop=True)


def load_table(key, data_dir):
    if key not in DATASETS:
        raise QueryValidationError("Unknown dataset.")
    path = _normal_path(data_dir, DATASETS[key]["file"])
    try:
        stat = path.stat()
    except OSError as exc:
        raise DataUnavailableError(f"Required dataset is unavailable: {path.name}") from exc
    frame = _prepared_cached(key, str(path), stat.st_mtime_ns, stat.st_size)
    return frame.copy(deep=False)


def _python_value(value):
    if value is None or value is pd.NaT or pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def records(frame):
    return [{str(key): _python_value(value) for key, value in row.items()} for row in frame.to_dict(orient="records")]


def _without_internal(frame):
    return frame.drop(columns=["_state_key", "_district_key"], errors="ignore")


def _date_string(value):
    return value.strftime("%Y-%m-%d") if value is not None and not pd.isna(value) else None


def date_range(frame, column):
    if column not in frame or frame.empty:
        return {"start": None, "end": None}
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    if values.empty:
        return {"start": None, "end": None}
    return {"start": _date_string(values.min()), "end": _date_string(values.max())}


def _filter_dates(frame, column, start=None, end=None):
    if start is not None:
        frame = frame[frame[column] >= pd.Timestamp(start)]
    if end is not None:
        frame = frame[frame[column] <= pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)]
    return frame


def _filter_state(frame, column, state):
    if not state:
        return frame
    key_col = "_state_key" if "_state_key" in frame else None
    if key_col:
        wanted = normalize_state(state)
        return frame[frame[key_col] == wanted]
    if column not in frame:
        return frame.iloc[0:0]
    return frame[frame[column].map(normalize_state) == normalize_state(state)]


def _date_meta(key, frame):
    column = DATASETS[key]["date"]
    return date_range(frame, column)


def _public_frame(frame, key):
    date_col = DATASETS[key]["date"]
    result = _without_internal(frame).copy()
    if date_col in result:
        result[date_col] = result[date_col].map(_date_string)
    return result


def metadata(data_dir):
    datasets = {}
    for key, info in DATASETS.items():
        try:
            frame = load_table(key, data_dir)
            datasets[key] = {"file": info["file"], "source": info["source"], "available": True,
                             "rows": int(len(frame)), "date_range": _date_meta(key, frame),
                             "columns": list(frame.columns.drop(["_state_key", "_district_key"], errors="ignore"))}
        except DataUnavailableError as exc:
            datasets[key] = {"file": info["file"], "source": info["source"], "available": False, "error": str(exc)}
    national_info = datasets.get("national", {})
    return {"source": "COVID19India.org archive (community-maintained)", "historical": True,
            "date_range": national_info.get("date_range", {"start": None, "end": None}),
            "datasets": datasets,
            "limitations": ["These are historical archived reports, not live statistics.",
                            "District counts are supplied as a latest snapshot only.",
                            "National and state sources can have different reporting cut-offs.",
                            "Duplicate observations retain the last source row for the same date and geography."]}


def national_summary(data_dir):
    frame = load_table("national", data_dir)
    latest = frame.iloc[-1] if not frame.empty else None
    return {"source": DATASETS["national"]["source"], "date_range": _date_meta("national", frame),
            "latest": records(pd.DataFrame([latest]))[0] if latest is not None else None,
            "metrics": {"confirmed": _python_value(latest.get("Total Confirmed")) if latest is not None else None,
                        "recovered": _python_value(latest.get("Total Recovered")) if latest is not None else None,
                        "deceased": _python_value(latest.get("Total Deceased")) if latest is not None else None,
                        "daily_confirmed": _python_value(latest.get("Daily Confirmed")) if latest is not None else None,
                        "daily_recovered": _python_value(latest.get("Daily Recovered")) if latest is not None else None,
                        "daily_deceased": _python_value(latest.get("Daily Deceased")) if latest is not None else None}}


def national_trends(data_dir, start=None, end=None, metric=None):
    frame = load_table("national", data_dir)
    allowed = {"Daily Confirmed", "Total Confirmed", "Daily Recovered", "Total Recovered", "Daily Deceased", "Total Deceased"}
    if metric and metric not in allowed:
        raise QueryValidationError(f"Unsupported national metric. Choose from: {', '.join(sorted(allowed))}.")
    frame = _filter_dates(frame, "Date", start, end)
    columns = ["Date", *([metric] if metric else sorted(allowed))]
    columns = [column for column in columns if column in frame]
    window = frame[columns].tail(500)
    output = _public_frame(window, "national")
    return {"source": DATASETS["national"]["source"], "date_range": _date_meta("national", frame),
            "returned_range": {"start": output["Date"].iloc[0] if not output.empty else None,
                               "end": output["Date"].iloc[-1] if not output.empty else None},
            "limit": 500, "truncated": len(frame) > len(window), "metric_type": "daily_and_cumulative_source_values",
            "rows": records(output)}


def trend_series(data_dir, start=None, end=None, state=None, district=None, metric=None):
    if district:
        raise QueryValidationError("District time series are unavailable: the district dataset contains a latest snapshot only.")
    if not state:
        return national_trends(data_dir, start=start, end=end, metric=metric)
    aliases = {"confirmed": "Confirmed", "recovered": "Recovered", "deceased": "Deceased",
               "daily confirmed": "daily_confirmed", "daily_confirmed": "daily_confirmed",
               "daily recovered": "daily_recovered", "daily_recovered": "daily_recovered",
               "daily deceased": "daily_deceased", "daily_deceased": "daily_deceased"}
    normalized_metric = aliases.get(str(metric or "Confirmed").casefold())
    if normalized_metric is None:
        raise QueryValidationError("State trends support Confirmed, Recovered, Deceased, and their derived daily differences.")
    frame = load_table("states", data_dir)
    frame = _filter_state(frame, "State_Name", state)
    frame = _filter_dates(frame, "Date", start, end)
    value_column = normalized_metric.removeprefix("daily_").capitalize() if normalized_metric.startswith("daily_") else normalized_metric
    if value_column not in frame:
        raise QueryValidationError("The requested state metric is not present in the state daily dataset.")
    frame = frame.sort_values("Date", kind="stable")
    if normalized_metric.startswith("daily_"):
        # Negative differences are retained as source revisions, not clamped.
        frame["derived_daily_value"] = frame.groupby("_state_key")[value_column].diff()
        value_column = "derived_daily_value"
    output = frame[["State_Name", "Date", value_column]].rename(columns={"State_Name": "State", value_column: "value"}).copy()
    output["Date"] = output["Date"].map(_date_string)
    return {"source": DATASETS["states"]["source"], "state": frame["State_Name"].iloc[0] if not frame.empty else state,
            "metric": normalized_metric, "metric_type": "daily_difference_of_cumulative_values" if normalized_metric.startswith("daily_") else "cumulative_source_value",
            "negative_corrections": "Retained as negative differences; missing prior-day observations remain null.",
            "date_range": _date_meta("states", frame), "rows": records(output)}


def state_analytics(data_dir, start=None, end=None, state=None, metric="Confirmed", sort_by=None, sort_order="desc"):
    allowed = {"Confirmed", "Recovered", "Deceased", "Active", "Deaths"}
    if metric not in allowed:
        raise QueryValidationError(f"Unsupported state metric. Choose from: {', '.join(sorted(allowed))}.")
    if start or end:
        frame = load_table("states", data_dir)
        if metric == "Active" or metric == "Deaths":
            raise QueryValidationError("The state daily file contains Confirmed, Recovered, and Deceased only; Active/Deaths are available only in the latest snapshot.")
        frame = _filter_dates(frame, "Date", start, end)
        frame = _filter_state(frame, "State_Name", state)
        if not frame.empty:
            frame = frame.sort_values("Date").groupby("_state_key", as_index=False, sort=False).tail(1)
            frame = frame.rename(columns={"State": "State_Code", "State_Name": "State"})
            frame["observation_date"] = frame["Date"].map(_date_string)
        source_key = "states"
    else:
        frame = load_table("state_snapshot", data_dir)
        frame = _filter_state(frame, "State", state)
        source_key = "state_snapshot"
    if sort_by is None:
        sort_by = "Deaths" if source_key == "state_snapshot" and metric == "Deceased" else metric
    columns = set(frame.columns)
    if sort_by.startswith("_") or sort_by not in columns:
        raise QueryValidationError(f"sort_by must be one of: {', '.join(sorted(columns - {'_state_key'}))}.")
    frame = frame.sort_values(sort_by, ascending=(sort_order == "asc"), na_position="last", kind="stable")
    result = _public_frame(frame, source_key)
    return {"source": DATASETS[source_key]["source"], "metric": metric, "metric_type": "cumulative_snapshot",
            "date_range": _date_meta(source_key, load_table(source_key, data_dir)),
            "selected_range": {"start": start, "end": end}, "regions": records(result)}


def state_comparison(data_dir, states=None, start=None, end=None, metric="Confirmed"):
    allowed = {"Confirmed", "Recovered", "Deceased"}
    if metric not in allowed:
        raise QueryValidationError("State comparison metric must be Confirmed, Recovered, or Deceased; these are cumulative values from the same state daily source.")
    frame = load_table("states", data_dir)
    frame = _filter_dates(frame, "Date", start, end)
    requested = [normalize_state(value) for value in (states or []) if normalize_state(value)]
    if len(requested) > 10:
        raise QueryValidationError("Compare no more than 10 states at once.")
    if requested:
        frame = frame[frame["_state_key"].isin(requested)]
    if not frame.empty:
        frame = frame.sort_values("Date", kind="stable").groupby("_state_key", as_index=False, sort=False).tail(1)
        frame = frame.rename(columns={"State": "State_Code", "State_Name": "State", metric: "value"})
        frame["observation_date"] = frame["Date"].map(_date_string)
        frame = frame[["State", "observation_date", "value"]].sort_values("value", ascending=False, na_position="last")
    else:
        frame = pd.DataFrame(columns=["State", "observation_date", "value"])
    return {"source": DATASETS["states"]["source"], "metric": metric, "metric_type": "cumulative",
            "requested_states": states or [], "date_range": _date_meta("states", load_table("states", data_dir)),
            "selected_range": {"start": start, "end": end},
            "rows": records(frame)}


def district_analytics(data_dir, state=None, district=None, start=None, end=None, metric="Confirmed", sort_by=None, sort_order="desc"):
    allowed = {"Confirmed", "Active", "Recovered", "Deceased"}
    if metric not in allowed:
        raise QueryValidationError(f"Unsupported district metric. Choose from: {', '.join(sorted(allowed))}.")
    frame = load_table("districts", data_dir)
    state_names = sorted(frame["State"].dropna().astype(str).unique().tolist())
    frame = _filter_state(frame, "State", state)
    if district:
        frame = frame[frame["_district_key"] == normalize_state(district)]
    if start or end:
        frame = _filter_dates(frame, "Last_Updated", start, end)
    sort_by = sort_by or metric
    if sort_by not in frame.columns:
        raise QueryValidationError("sort_by must be a column in the district dataset.")
    frame = frame.sort_values(sort_by, ascending=(sort_order == "asc"), na_position="last", kind="stable")
    output = _public_frame(frame, "districts")
    return {"source": DATASETS["districts"]["source"], "metric": metric, "metric_type": "latest_snapshot",
            "historical_trends_available": False, "date_range": _date_meta("districts", load_table("districts", data_dir)),
            "selected_range": {"start": start, "end": end},
            "states": state_names, "regions": records(output)}


def testing_analytics(data_dir, start=None, end=None, state=None, metric=None, level="national"):
    if state or level == "state":
        frame = load_table("testing_states", data_dir)
        frame = _filter_state(frame, "State", state)
        frame = _filter_dates(frame, "Updated On", start, end)
        if not frame.empty:
            frame = frame.sort_values("Updated On").groupby("_state_key", as_index=False, sort=False).tail(1)
        source_key = "testing_states"
        allowed = {"Total Tested", "Positive", "Negative", "Unconfirmed", "Test positivity rate", "Tests per thousand", "Tests per million"}
        if metric and metric not in allowed:
            raise QueryValidationError(f"Unsupported state testing metric. Choose from: {', '.join(sorted(allowed))}.")
        output = _public_frame(frame, source_key)
        return {"source": DATASETS[source_key]["source"], "metric": metric, "metric_type": "source_reported_snapshot",
                "date_range": _date_meta(source_key, load_table(source_key, data_dir)), "regions": records(output),
                "positivity_method": "The source-reported Test positivity rate is returned without recalculation."}
    frame = load_table("testing", data_dir)
    frame = _filter_dates(frame, "Tested As Of", start, end)
    allowed = {column for column in NUMERIC_COLUMNS["testing"] if column in frame.columns} | {"Test positivity rate"}
    if metric and metric not in allowed:
        raise QueryValidationError(f"Unsupported testing metric. Choose from: {', '.join(sorted(allowed))}.")
    output = _public_frame(frame, "testing")
    return {"source": DATASETS["testing"]["source"], "metric": metric, "metric_type": "source_reported_daily_or_cumulative",
            "date_range": _date_meta("testing", load_table("testing", data_dir)), "trend": records(output.tail(500)),
            "positivity_method": "Positivity is only returned as recorded by the testing source; no cross-file denominator is computed."}


def calculate_insights(data_dir, start=None, end=None):
    trends = national_trends(data_dir, start, end)
    rows = trends["rows"]
    valid = [row for row in rows if row.get("Daily Confirmed") is not None]
    insights = []
    if valid:
        peak = max(valid, key=lambda row: row["Daily Confirmed"])
        insights.append({"type": "peak", "metric": "Daily Confirmed", "value": peak["Daily Confirmed"],
                         "date": peak["Date"], "calculation": f"Maximum Daily Confirmed across {len(valid)} returned national records."})
        first, last = valid[0], valid[-1]
        insights.append({"type": "first_to_last_difference", "metric": "Daily Confirmed",
                         "value": last["Daily Confirmed"] - first["Daily Confirmed"],
                         "period": {"start": first["Date"], "end": last["Date"]},
                         "calculation": "Last available Daily Confirmed minus first available Daily Confirmed in the selected returned window."})
    try:
        states = state_analytics(data_dir, metric="Confirmed")["regions"]
    except DataUnavailableError:
        states = []
    if states:
        leading = states[0]
        insights.append({"type": "largest_state_snapshot", "metric": "Confirmed", "value": leading.get("Confirmed"),
                         "state": leading.get("State"), "date": leading.get("Last_Updated_Time"),
                         "calculation": "Maximum Confirmed value from the state latest snapshot; this date is not aligned to every national observation."})
    return {"source": DATASETS["national"]["source"], "date_range": trends["returned_range"],
            "observation_count": len(valid), "historical": True, "insights": insights}


def explore(data_dir, dataset="national", limit=100, offset=0, search=None, state=None, district=None,
            start=None, end=None, metric=None, min_value=None, max_value=None, sort_by=None, sort_order="asc"):
    key = EXPLORER_DATASETS.get(dataset)
    if key is None:
        raise QueryValidationError(f"Unknown dataset. Choose from: {', '.join(EXPLORER_DATASETS)}.")
    frame = load_table(key, data_dir)
    date_col = DATASETS[key]["date"]
    if key in ("states", "state_snapshot", "testing_states"):
        state_col = "State_Name" if key == "states" else "State"
        frame = _filter_state(frame, state_col, state)
    elif state:
        if "State" not in frame:
            raise QueryValidationError(f"State filtering is not supported for the {dataset} dataset.")
        frame = _filter_state(frame, "State", state)
    if district:
        if "_district_key" not in frame:
            raise QueryValidationError(f"District filtering is not supported for the {dataset} dataset.")
        frame = frame[frame["_district_key"] == normalize_state(district)]
    frame = _filter_dates(frame, date_col, start, end)
    if search:
        needle = search.casefold()
        visible = [column for column in frame.columns if not column.startswith("_")]
        mask = frame[visible].astype("string").apply(lambda column: column.str.casefold().str.contains(needle, regex=False, na=False)).any(axis=1)
        frame = frame[mask]
    if metric:
        if metric not in frame.columns or metric not in NUMERIC_COLUMNS.get(key, ()):
            raise QueryValidationError("metric must be a supported numeric column in the selected dataset.")
        if min_value is not None:
            frame = frame[frame[metric] >= min_value]
        if max_value is not None:
            frame = frame[frame[metric] <= max_value]
    elif min_value is not None or max_value is not None:
        raise QueryValidationError("min_value and max_value require a valid metric parameter.")
    total = int(len(frame))
    if sort_by:
        if sort_by not in frame.columns or sort_by.startswith("_"):
            raise QueryValidationError("sort_by must be a visible column in the selected dataset.")
        frame = frame.sort_values(sort_by, ascending=(sort_order == "asc"), na_position="last", kind="stable")
    selected = frame.iloc[offset:offset + limit]
    result = _public_frame(selected, key)
    return {"dataset": dataset, "source": DATASETS[key]["source"], "columns": list(result.columns),
            "total_rows": total, "rows": records(result), "limit": limit, "offset": offset,
            "sort_by": sort_by, "sort_order": sort_order}
