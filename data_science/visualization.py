"""Reproducible Matplotlib/Seaborn figures built from repository data."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

try:
    from .preprocessing import coerce_numeric, is_aggregate_label, load_dataset, state_daily_long
except ImportError:
    from preprocessing import coerce_numeric, is_aggregate_label, load_dataset, state_daily_long

sns.set_theme(style="whitegrid", context="notebook", palette="deep")


def national_time_series(output: str | Path, metric: str = "Daily Confirmed") -> Path:
    df = load_dataset("national_daily").dropna(subset=["Date"]).sort_values("Date")
    if metric not in df: raise ValueError(f"Metric unavailable: {metric}")
    df[metric] = coerce_numeric(df[metric]); df = df.dropna(subset=[metric])
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df.Date, df[metric], color="#147d83", linewidth=1.6, label=metric)
    ax.set(title=f"India COVID-19 {metric} (historical archive)", xlabel="Date", ylabel="Cases (count)")
    ax.legend(title="Metric"); fig.autofmt_xdate(); fig.tight_layout()
    path = Path(output); fig.savefig(path, dpi=160); plt.close(fig); return path


def state_comparison_chart(output: str | Path, metric: str = "Confirmed", limit: int = 15) -> Path:
    df = load_dataset("states").dropna(subset=["Date", "State"])
    df = df[~df.State.map(is_aggregate_label)]
    if metric not in df: raise ValueError(f"Metric unavailable: {metric}")
    df[metric] = coerce_numeric(df[metric])
    latest = df.sort_values("Date").groupby(df.State.str.casefold(), sort=False).tail(1).dropna(subset=[metric])
    latest = latest.nlargest(max(0, limit), metric).sort_values(metric)
    fig, ax = plt.subplots(figsize=(10, max(4, len(latest) * .34)))
    ax.barh(latest.State, latest[metric], color="#3978a8")
    ax.set(title=f"State comparison: {metric} (latest available observation per state)", xlabel=f"{metric} (count)", ylabel="State / UT")
    fig.tight_layout(); path = Path(output); fig.savefig(path, dpi=160); plt.close(fig); return path


def state_daily_heatmap(output: str | Path, status: str = "Confirmed", top_n: int = 20) -> Path:
    """Monthly sums of reported daily incidence; no cumulative series or TT aggregate."""
    df = state_daily_long()
    df = df[(df.Status == status) & (~df.is_national_aggregate) & df.Date_YMD.notna()].copy()
    df["daily_count"] = coerce_numeric(df.daily_count)
    df = df.dropna(subset=["daily_count"])
    rank = df.groupby("state_code").daily_count.sum().nlargest(top_n).index
    df = df[df.state_code.isin(rank)]
    df["month"] = df.Date_YMD.dt.to_period("M").astype(str)
    pivot = df.pivot_table(index="state_code", columns="month", values="daily_count", aggfunc="sum", fill_value=0)
    pivot = pivot.apply(pd.to_numeric, errors="coerce").fillna(0).astype(float)
    fig, ax = plt.subplots(figsize=(max(12, pivot.shape[1] * .42), max(5, pivot.shape[0] * .3)))
    sns.heatmap(pivot, cmap="YlGnBu", ax=ax, cbar_kws={"label": f"Reported {status.lower()} incidence (count/month)"})
    ax.set(title=f"Monthly reported {status.lower()} by state code", xlabel="Month", ylabel="State / UT code")
    fig.tight_layout(); path = Path(output); fig.savefig(path, dpi=160); plt.close(fig); return path


def testing_time_series(output: str | Path) -> Path:
    df = load_dataset("tests_daily").dropna(subset=["Tested As Of"]).sort_values("Tested As Of")
    fig, ax = plt.subplots(figsize=(12, 5))
    plotted = 0
    for col, label, color in (("Total Samples Tested", "Samples tested (cumulative snapshot)", "#3978a8"),
                              ("Total Individuals Tested", "Individuals tested (cumulative snapshot)", "#147d83")):
        if col in df:
            values = coerce_numeric(df[col]); valid = values.notna()
            if valid.any(): ax.plot(df.loc[valid, "Tested As Of"], values[valid], label=label, color=color); plotted += 1
    ax.set(title="India testing archive (historical cumulative snapshots)", xlabel="Tested as of", ylabel="Reported cumulative count")
    if plotted: ax.legend()
    fig.autofmt_xdate(); fig.tight_layout(); path = Path(output); fig.savefig(path, dpi=160); plt.close(fig); return path


def create_all_figures(output_dir: str | Path) -> list[Path]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    return [national_time_series(out / "national_daily_confirmed.png"),
            state_comparison_chart(out / "state_confirmed_latest.png"),
            state_daily_heatmap(out / "state_confirmed_monthly_heatmap.png"),
            testing_time_series(out / "national_testing_snapshots.png")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("view", choices=("national", "states", "heatmap", "testing"))
    parser.add_argument("--output", type=Path, default=Path("data_science/outputs"))
    parser.add_argument("--metric", default="Confirmed")
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()
    funcs = {"national": lambda: national_time_series(args.output, "Daily Confirmed" if args.metric == "Confirmed" else args.metric),
             "states": lambda: state_comparison_chart(args.output, args.metric, args.limit),
             "heatmap": lambda: state_daily_heatmap(args.output), "testing": lambda: testing_time_series(args.output)}
    print(funcs[args.view]())


if __name__ == "__main__": main()
