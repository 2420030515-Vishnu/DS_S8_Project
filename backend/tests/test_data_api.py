import pandas as pd

from backend.services.data_service import _date_without_year


def test_health_and_metadata(client):
    assert client.get("/api/health").get_json()["historical_data"] is True
    metadata = client.get("/api/metadata").get_json()
    assert metadata["historical"] is True
    assert metadata["date_range"] == {"start": "2020-01-30", "end": "2020-02-02"}
    assert metadata["datasets"]["districts"]["available"] is True


def test_yearless_national_dates_handle_leap_day_and_year_rollover():
    leap = _date_without_year(pd.Series(["28 February", "29 February", "1 March"]))
    rollover = _date_without_year(pd.Series(["31 December", "1 January"]))
    assert [value.strftime("%Y-%m-%d") for value in leap] == ["2020-02-28", "2020-02-29", "2020-03-01"]
    assert [value.strftime("%Y-%m-%d") for value in rollover] == ["2020-12-31", "2021-01-01"]


def test_summary_uses_latest_cumulative_not_sum_of_rows(client):
    result = client.get("/api/dashboard/summary").get_json()
    assert result["metrics"]["confirmed"] == 10
    assert result["metrics"]["confirmed"] != 1 + 4 + 8 + 10
    assert result["metrics"]["daily_confirmed"] == 2


def test_legacy_frontend_endpoints_remain_compatible(client):
    national = client.get("/api/national").get_json()
    assert national["latest"]["Total Confirmed"] == 10
    assert len(national["trend"]) == 4
    states = client.get("/api/states").get_json()
    assert all(row["State"] != "Total" for row in states["regions"])


def test_national_trend_date_filters_and_bad_ranges(client):
    result = client.get("/api/dashboard/trends?start=2020-01-31&end=2020-02-01&metric=Daily%20Confirmed").get_json()
    assert [row["Date"] for row in result["rows"]] == ["2020-01-31", "2020-02-01"]
    assert [row["Daily Confirmed"] for row in result["rows"]] == [3, 4]
    assert client.get("/api/dashboard/trends?start=2020-02-02&end=2020-01-30").status_code == 400
    assert client.get("/api/dashboard/trends?start=bad-date").status_code == 400


def test_state_comparison_deduplicates_and_uses_same_cumulative_metric(client):
    result = client.get("/api/analytics/state-comparison?states=Karnataka%2CMaharashtra&start=2020-01-31&metric=Confirmed").get_json()
    assert result["metric_type"] == "cumulative"
    assert {row["State"]: row["value"] for row in result["rows"]} == {"Karnataka": 16, "Maharashtra": 24}
    assert client.get("/api/analytics/state-comparison?metric=Active").status_code == 400


def test_state_analytics_filters_by_date_without_inventing_active_history(client):
    filtered = client.get("/api/analytics/states?state=karnataka&start=2020-01-31&metric=Confirmed").get_json()
    assert len(filtered["regions"]) == 1
    assert filtered["regions"][0]["State"] == "Karnataka"
    assert filtered["regions"][0]["Confirmed"] == 16
    unsupported = client.get("/api/analytics/states?start=2020-01-31&metric=Active")
    assert unsupported.status_code == 400


def test_district_filters_and_snapshot_limitations(client):
    response = client.get("/api/analytics/districts?state=KARNATAKA&district=Bengaluru%20Urban").get_json()
    assert response["historical_trends_available"] is False
    assert len(response["regions"]) == 1
    assert response["regions"][0]["Confirmed"] == 12
    assert client.get("/api/dashboard/trends?district=Bengaluru").status_code == 400


def test_testing_returns_reported_rate_and_state_snapshot(client):
    daily = client.get("/api/analytics/testing?start=2020-01-31").get_json()
    assert len(daily["trend"]) == 1
    assert daily["trend"][0]["Test positivity rate"] == 11.11
    state = client.get("/api/analytics/testing?level=state&state=Karnataka").get_json()
    assert state["regions"][0]["Total Tested"] == 60
    assert state["positivity_method"].startswith("The source-reported")


def test_explorer_filters_sorts_and_paginates(client):
    response = client.get("/api/data/explorer?dataset=states&limit=1&offset=1&state=karnataka&sort_by=Confirmed&sort_order=desc").get_json()
    assert response["pagination"]["total"] == 2
    # The duplicate Jan 31 snapshot retains the last source row (16); the
    # second paginated result is then the Jan 30 value (10).
    assert response["rows"][0]["Confirmed"] == 10
    assert response["pagination"]["limit"] == 1
    assert client.get("/api/data/explorer?dataset=states&limit=501").status_code == 400
    assert client.get("/api/data/explorer?dataset=states&sort_by=not-a-column").status_code == 400


def test_insights_are_calculated_from_the_selected_real_records(client):
    result = client.get("/api/insights?start=2020-01-31&end=2020-02-02").get_json()
    peak = next(item for item in result["insights"] if item["type"] == "peak")
    change = next(item for item in result["insights"] if item["type"] == "first_to_last_difference")
    assert peak["metric"] == "Daily Confirmed"
    assert peak["value"] == 4
    assert change["value"] == -1


def test_missing_source_has_consistent_service_unavailable_error(client, app, tmp_path):
    app.config["DATA_DIR"] = str(tmp_path / "missing")
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 503
    assert response.get_json()["code"] == "data_unavailable"
    assert "stack" not in response.get_json()
