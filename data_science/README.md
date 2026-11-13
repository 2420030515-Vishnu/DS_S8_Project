# Data science pipeline

This directory contains read-only preprocessing, exploratory analysis and chart generation for the historical project archives. The source CSV files and notebooks are not modified. The original `api.ipynb` and `web_scraping.ipynb` reference retired endpoints and one notebook writes `complete.csv`; neither is run by this pipeline.

## Reproduce

From the repository root, with the packages in `backend/requirements.txt` installed:

```powershell
python -m data_science.eda --output data_science/outputs
python -m pytest data_science/tests
```

The first command profiles all registered CSVs, computes EDA from the selected primary sources, and writes `profile_and_eda.json` plus PNG charts under the output directory. It never writes into `datasets/` or `backend/data/`. Use `--profiles-only` to print profiles without generating artifacts. Figures use Matplotlib and Seaborn; machine-readable calculations are implemented in `preprocessing.py` and `eda.py` so API services can reuse them.

## Source register and archive coverage

Coverage below is parsed from the repository files, not inferred from the present day. Exact row counts, column types, invalid dates, missingness, duplicate keys, negative-value counts, label variants, and numeric summaries are written per source to the generated profile report.

| Source | Rows × columns | Parsed date coverage | Role and limitations |
|---|---:|---|---|
| `datasets/state_wise_daily.csv` | 1,791 × 42 | 2020-03-14–2021-10-31 | Wide daily counts by status/state code. `TT` is a national aggregate and is excluded from state comparisons. Negative corrections are preserved. |
| `datasets/states.csv` | 21,675 × 7 | 2020-01-30–2021-10-31 | Dated state cumulative counts; includes `India`, excluded from state rankings. `Tested` has 763 missing values. |
| `datasets/districts.csv` | 358,633 × 8 | 2020-04-26–2021-10-31 | Dated district cumulative snapshots. Testing is sparse (87,935 missing); some correction values are negative. Date gaps are not treated as zero. |
| `datasets/statewise_tested_numbers_data.csv` | 19,211 × 53 | 2020-04-01–2021-10-31 | Irregular state testing snapshots; several fields are sparse and a state/date key repeats. |
| `backend/data/complete.csv` | 4,692 × 10 | 2020-01-30–2020-08-06 | Overlapping state export; profiling/reconciliation only, never added to other totals. |
| `backend/data/district_level_latest.csv` | 800 × 16 | No populated date field | District snapshot; `Last_Updated` is blank for all rows. |
| `backend/data/nation_level_daily.csv` | 190 × 7 | 2020-01-30–2020-08-06 | Primary national daily and cumulative series. The source stores both separately; totals are never summed across dates. |
| `backend/data/patients_data.csv` | 247,236 × 22 | 2020-01-30–2020-08-06 (2 invalid) | Individual line-list with personal fields, reused identifiers, duplicates and inconsistent `Num Cases`; profile only, never used for dashboard totals or plots. |
| `backend/data/state_level_daily.csv` | 5,694 × 7 | 2020-03-14–2020-08-06 | Overlapping state daily archive; used only for overlap reconciliation against the wide source. |
| `backend/data/state_level_latest.csv` | 38 × 12 | 2020-03-26–2020-08-06 | Latest snapshot; `Total` is an aggregate row. |
| `backend/data/tests_day_wise.csv` | 149 × 14 | 2020-03-13–2020-08-05 (1 invalid) | National testing snapshots. Repeated dates are revisions, not daily increments; source positivity is retained as reported. |
| `backend/data/tests_state_wise.csv` | 3,938 × 28 | 2020-04-01–2020-08-07 | Short state testing snapshot archive with sparse measures and a repeated state/date key. |

## Authority, cleaning and calculations

- National time series uses `backend/data/nation_level_daily.csv`, because it explicitly distinguishes daily (`Daily ...`) from cumulative (`Total ...`) measures. Its yearless dates are parsed in source order and year rollover is inferred only at December-to-January transitions.
- State daily incidence uses `datasets/state_wise_daily.csv`. The API daily state export is cross-checked but is not merged with it. Its wide status rows are unpivoted in memory; `TT` remains identifiable as an aggregate.
- Long-run state cumulative analysis uses `datasets/states.csv`; district cumulative analysis uses `datasets/districts.csv`. These are snapshot observations. Differencing is performed only after sorting within region. `gap_days` and `is_observation_gap` identify non-consecutive observations; the derived change for a gap is withheld rather than represented as a daily value. Negative differences are retained and flagged as revisions/corrections.
- Testing uses `backend/data/tests_day_wise.csv` for national trends. Positivity is source-reported. The pipeline does not recompute positivity because case and testing definitions and observed dates are not consistently aligned. State testing sources stay separate and are not added to national totals.
- Empty strings and malformed numerics become missing values. No generic zero filling or imputation is performed. Labels are whitespace-cleaned for display while original labels are preserved in companion columns; comparison keys only trim/collapse whitespace and case-fold. Known spelling variants are reported, not silently aliased.
- Duplicate rows and domain-key collisions are profiled. The analysis does not silently deduplicate sources. The API can call the explicit `deduplicate()` helper where a consumer chooses a keep policy and can capture the removed row count.
- State/district aggregate rows (`India`, `Total`, etc.) are excluded from region rankings. No correlation is presented as causal evidence.

## Notebook notes

The notebooks are historical research artifacts, not pipeline inputs. Their old remote URLs may no longer work. `web_scraping.ipynb` contains a `to_csv('complete.csv')` cell that can overwrite an archive, so this workflow deliberately does not execute notebooks. For future reproducibility, export cleaned outputs only to a separate output directory and record source URLs/access dates there.
