"""Public, read-only analytics API with strict query validation."""
import math

from flask import Blueprint, current_app, jsonify, request

try:
    from ..services import data_service
except ImportError:  # `python backend/app.py`
    from services import data_service


data_bp = Blueprint("data", __name__, url_prefix="/api")


def _date_arg(name):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    from datetime import datetime
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:
        raise data_service.QueryValidationError(f"{name} must use YYYY-MM-DD format.") from exc
    if parsed.strftime("%Y-%m-%d") != raw:
        raise data_service.QueryValidationError(f"{name} must use YYYY-MM-DD format.")
    return parsed.date().isoformat()


def _date_range():
    start, end = _date_arg("start"), _date_arg("end")
    if start and end and start > end:
        raise data_service.QueryValidationError("start must be on or before end.")
    return start, end


def _text_arg(name, max_length=120):
    value = request.args.get(name)
    if value is None:
        return None
    value = value.strip()
    if len(value) > max_length:
        raise data_service.QueryValidationError(f"{name} must be {max_length} characters or fewer.")
    return value or None


def _page_args():
    raw_limit, raw_offset = request.args.get("limit", "100"), request.args.get("offset", "0")
    try:
        limit, offset = int(raw_limit), int(raw_offset)
    except (TypeError, ValueError) as exc:
        raise data_service.QueryValidationError("limit and offset must be integers.") from exc
    if not 1 <= limit <= 500:
        raise data_service.QueryValidationError("limit must be between 1 and 500.")
    if not 0 <= offset <= 1_000_000:
        raise data_service.QueryValidationError("offset must be between 0 and 1000000.")
    return limit, offset


def _sort_args():
    sort_order = request.args.get("sort_order", "desc").lower()
    if sort_order not in ("asc", "desc"):
        raise data_service.QueryValidationError("sort_order must be asc or desc.")
    return _text_arg("sort_by", 80), sort_order


def _numeric_arg(name):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise data_service.QueryValidationError(f"{name} must be numeric.") from exc
    if not math.isfinite(value):
        raise data_service.QueryValidationError(f"{name} must be finite.")
    return value


def _run(fn):
    try:
        return jsonify(fn())
    except data_service.QueryValidationError as exc:
        return jsonify({"error": str(exc), "code": "invalid_query"}), 400
    except data_service.DataUnavailableError as exc:
        current_app.logger.warning("Data unavailable: %s", exc)
        return jsonify({"error": str(exc), "code": "data_unavailable"}), 503


@data_bp.get("/metadata")
@data_bp.get("/meta")  # backwards-compatible alias used by the current frontend
def metadata():
    return _run(lambda: data_service.metadata(current_app.config["DATA_DIR"]))


@data_bp.get("/dashboard/summary")
def dashboard_summary():
    return _run(lambda: data_service.national_summary(current_app.config["DATA_DIR"]))


@data_bp.get("/national")  # backwards-compatible combined summary and trend
def national_legacy():
    def response():
        summary = data_service.national_summary(current_app.config["DATA_DIR"])
        trends = data_service.national_trends(current_app.config["DATA_DIR"])
        summary["trend"] = trends["rows"]
        summary["date_range"] = trends["date_range"]
        return summary
    return _run(response)


@data_bp.get("/dashboard/trends")
def dashboard_trends():
    def response():
        start, end = _date_range()
        return data_service.trend_series(current_app.config["DATA_DIR"], start=start, end=end,
                                          state=_text_arg("state"), district=_text_arg("district"),
                                          metric=_text_arg("metric", 80))
    return _run(response)


@data_bp.get("/analytics/states")
@data_bp.get("/states")  # current frontend compatibility
def states():
    def response():
        start, end = _date_range()
        sort_by, sort_order = _sort_args()
        return data_service.state_analytics(current_app.config["DATA_DIR"], start=start, end=end,
                                            state=_text_arg("state"), metric=_text_arg("metric", 80) or "Confirmed",
                                            sort_by=sort_by, sort_order=sort_order)
    return _run(response)


@data_bp.get("/analytics/state-comparison")
def state_comparison():
    def response():
        start, end = _date_range()
        selected = request.args.getlist("state")
        selected.extend(value.strip() for values in request.args.getlist("states") for value in values.split(",") if value.strip())
        return data_service.state_comparison(current_app.config["DATA_DIR"], states=selected, start=start, end=end,
                                             metric=_text_arg("metric", 80) or "Confirmed")
    return _run(response)


@data_bp.get("/analytics/districts")
@data_bp.get("/districts")  # current frontend compatibility
def districts():
    def response():
        start, end = _date_range()
        sort_by, sort_order = _sort_args()
        return data_service.district_analytics(current_app.config["DATA_DIR"], state=_text_arg("state"),
                                              district=_text_arg("district"), start=start, end=end,
                                              metric=_text_arg("metric", 80) or "Confirmed",
                                              sort_by=sort_by, sort_order=sort_order)
    return _run(response)


@data_bp.get("/analytics/testing")
@data_bp.get("/testing")  # current frontend compatibility
def testing():
    def response():
        start, end = _date_range()
        level = request.args.get("level", "state" if request.args.get("state") else "national").lower()
        if level not in ("national", "state"):
            raise data_service.QueryValidationError("level must be national or state.")
        return data_service.testing_analytics(current_app.config["DATA_DIR"], start=start, end=end,
                                              state=_text_arg("state"), metric=_text_arg("metric", 80), level=level)
    return _run(response)


@data_bp.get("/testing/states")
def testing_states_legacy():
    def response():
        start, end = _date_range()
        return data_service.testing_analytics(current_app.config["DATA_DIR"], start=start, end=end,
                                              state=_text_arg("state"), metric=_text_arg("metric", 80), level="state")
    return _run(response)


@data_bp.get("/data/explorer")
@data_bp.get("/explore")  # current frontend compatibility
def explorer():
    def response():
        start, end = _date_range()
        limit, offset = _page_args()
        sort_by, sort_order = _sort_args()
        min_value, max_value = _numeric_arg("min_value"), _numeric_arg("max_value")
        if min_value is not None and max_value is not None and min_value > max_value:
            raise data_service.QueryValidationError("min_value must not exceed max_value.")
        result = data_service.explore(current_app.config["DATA_DIR"],
                                      dataset=_text_arg("dataset", 40) or "national", limit=limit, offset=offset,
                                      search=_text_arg("q", 200), state=_text_arg("state"), district=_text_arg("district"),
                                      start=start, end=end, metric=_text_arg("metric", 80), min_value=min_value,
                                      max_value=max_value, sort_by=sort_by, sort_order=sort_order)
        result["pagination"] = {"limit": limit, "offset": offset, "total": result["total_rows"]}
        return result
    return _run(response)


@data_bp.get("/insights")
def insights():
    def response():
        start, end = _date_range()
        return data_service.calculate_insights(current_app.config["DATA_DIR"], start=start, end=end)
    return _run(response)
