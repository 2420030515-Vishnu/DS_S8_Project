import csv

import pytest

from backend.app import create_app


def _write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


@pytest.fixture
def data_dir(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    _write_csv(root / "nation_level_daily.csv",
        ["Date", "Daily Confirmed", "Total Confirmed", "Daily Recovered", "Total Recovered", "Daily Deceased", "Total Deceased"],
        [["30 January ", 1, 1, 0, 0, 0, 0], ["31 January ", 3, 4, 0, 0, 0, 0],
         ["1 February ", 4, 8, 1, 1, 0, 0], ["2 February ", 2, 10, 2, 3, 1, 1]])
    _write_csv(root / "state_level_daily.csv",
        ["", "Date", "State", "Confirmed", "Deceased", "Recovered", "State_Name"],
        [[0, "30-Jan-20", "KA", 10, 1, 3, "Karnataka"], [1, "31-Jan-20", "KA", 15, 1, 4, "Karnataka"],
         [2, "31-Jan-20", "KA", 16, 1, 4, "Karnataka"], [3, "30-Jan-20", "MH", 20, 1, 5, "Maharashtra"],
         [4, "31-Jan-20", "MH", 24, 2, 8, "Maharashtra"]])
    _write_csv(root / "state_level_latest.csv",
        ["State", "Confirmed", "Recovered", "Deaths", "Active", "Last_Updated_Time"],
        [["Total", 40, 20, 3, 17, "31/01/2020 20:00:00"],
         ["Karnataka", 16, 4, 1, 11, "31/01/2020 20:00:00"],
         ["Maharashtra", 24, 8, 2, 14, "31/01/2020 20:00:00"]])
    _write_csv(root / "district_level_latest.csv",
        ["State", "District", "Confirmed", "Active", "Recovered", "Deceased", "Last_Updated"],
        [["Karnataka", "Bengaluru Urban", 12, 8, 3, 1, "31/01/2020"],
         ["Maharashtra", "Mumbai", 20, 12, 6, 2, "31/01/2020"]])
    _write_csv(root / "tests_day_wise.csv",
        ["Tested As Of", "Total Samples Tested", "Total Individuals Tested", "Total Positive Cases", "Test positivity rate"],
        [["30/01/2020", 100, 90, 10, "11.11%"], ["31/01/2020", 200, 180, 20, "11.11%"]])
    _write_csv(root / "tests_state_wise.csv",
        ["Updated On", "State", "Total Tested", "Positive", "Test positivity rate", "Tests per million"],
        [["30/01/2020", "Karnataka", 50, 5, "10.00%", 1],
         ["31/01/2020", "Karnataka", 60, 6, "10.00%", 2],
         ["31/01/2020", "Maharashtra", 70, 7, "10.00%", 3]])
    return root


@pytest.fixture
def app(tmp_path, data_dir):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "pytest-only-not-a-production-secret",
        "DATABASE": str(tmp_path / "accounts.sqlite3"),
        "DATA_DIR": str(data_dir),
        "FRONTEND_ORIGINS": ["http://localhost:5173"],
        "SESSION_COOKIE_SECURE": False,
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.get_json()["csrf_token"]}
