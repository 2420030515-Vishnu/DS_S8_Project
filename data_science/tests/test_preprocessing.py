import pandas as pd
import pytest

from data_science.preprocessing import (
    coerce_numeric, derive_daily_change, is_aggregate_label, normalize_label,
    parse_date_series, parse_yearless_dates,
)


def test_yearless_date_year_rollover_and_leap_day():
    parsed = parse_yearless_dates(pd.Series(["29 February", "01 March", "31 December", "01 January"]))
    assert parsed.dt.strftime("%Y-%m-%d").tolist() == ["2020-02-29", "2020-03-01", "2020-12-31", "2021-01-01"]


def test_state_daily_dates_are_day_month_name():
    parsed = parse_date_series(pd.Series(["01-Apr-20", "bad"]), "state_daily")
    assert parsed.iloc[0] == pd.Timestamp("2020-04-01")
    assert pd.isna(parsed.iloc[1])


def test_state_testing_dates_use_day_month_year():
    parsed = parse_date_series(pd.Series(["17/04/2020", "bad"]), "statewise_tested")
    assert parsed.iloc[0] == pd.Timestamp("2020-04-17")
    assert pd.isna(parsed.iloc[1])


def test_numeric_invalids_stay_missing_and_negative_corrections_remain():
    values = coerce_numeric(pd.Series(["1,200", "", "-4", "bad"]))
    assert values.iloc[0] == 1200
    assert pd.isna(values.iloc[1]) and pd.isna(values.iloc[3])
    assert values.iloc[2] == -4


def test_cumulative_change_marks_gaps_and_negative_corrections():
    source = pd.DataFrame({"state": ["A"] * 4, "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-05", "2020-01-06"]), "total": [10, 15, 13, 20]})
    result = derive_daily_change(source, group_columns=["state"], date_column="date", cumulative_column="total")
    assert pd.isna(result.daily_change.iloc[0])  # first observation has no prior value
    assert result.daily_change.iloc[1] == 5
    assert bool(result.is_observation_gap.iloc[2])
    assert result.daily_change.iloc[2] == -2  # raw observed delta is retained with its gap flag
    assert bool(result.is_negative_correction.iloc[2])
    assert result.daily_change.iloc[3] == 7


def test_label_normalization_does_not_alias_names():
    assert normalize_label("  New   Delhi ") == "new delhi"
    assert normalize_label("Telengana") != normalize_label("Telangana")
    assert is_aggregate_label("India") and is_aggregate_label("Total")
