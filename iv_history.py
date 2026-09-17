"""
Keeps a running CSV of ATM implied volatility per maturity, one row
per run, so "IV now vs before" has something to compare against.
First run just saves a snapshot (nothing to compare yet).
"""

import os
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from config import OUTPUT_DIR, IV_RANK_LOOKBACK, IV_RANK_MIN_ROWS


def _csv_path(ticker: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, f"{ticker}_iv_history.csv")


def _atm_iv_by_maturity(chains: dict) -> dict:
    """For each maturity, find the call strike closest to spot and take its IV."""
    result = {}
    for exp, data in chains.items():
        calls = data["calls"]
        if calls.empty:
            continue
        spot = data["spot"]
        idx = (calls["strike"] - spot).abs().idxmin()
        result[exp] = calls.loc[idx, "impliedVolatility"]
    return result


def save_snapshot_and_plot(ticker: str, chains: dict):
    """
    Appends today's ATM IV curve to the CSV, then:
      - if enough history exists (IV_RANK_LOOKBACK rows), plots IV rank
        and IV percentile per maturity — the industry-standard "IV now
        vs history" comparison, over a rolling lookback window.
      - otherwise falls back to a simple latest-vs-previous-run plot.
    """
    atm = _atm_iv_by_maturity(chains)
    if not atm:
        return None

    row = {"timestamp": datetime.now().isoformat(timespec="seconds")}
    row.update(atm)

    path = _csv_path(ticker)
    if os.path.exists(path):
        history = pd.read_csv(path)
        history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
    else:
        history = pd.DataFrame([row])
    history.to_csv(path, index=False)

    if len(history) < 2:
        print(f"  {ticker}: first snapshot saved, nothing to compare yet.")
        return None

    maturities = [c for c in history.columns if c != "timestamp"]
    window = history.tail(IV_RANK_LOOKBACK)

    if len(window) >= IV_RANK_MIN_ROWS:
        return _plot_iv_rank(ticker, window, maturities)
    return _plot_latest_vs_previous(ticker, history, maturities)


def _plot_iv_rank(ticker: str, window: pd.DataFrame, maturities: list):
    """IV rank (0-100) per maturity: where today's IV sits vs the lookback range."""
    latest = window.iloc[-1]
    ranks, percentiles = {}, {}
    for m in maturities:
        series = window[m].dropna()
        if series.empty or m not in latest or pd.isna(latest[m]):
            continue
        lo, hi = series.min(), series.max()
        ranks[m] = 0.0 if hi == lo else (latest[m] - lo) / (hi - lo) * 100
        percentiles[m] = (series < latest[m]).mean() * 100

    if not ranks:
        return None

    fig, ax = plt.subplots(figsize=(9, 6))
    x = list(ranks.keys())
    ax.bar(x, [ranks[m] for m in x], alpha=0.7, label="IV rank")
    ax.plot(x, [percentiles[m] for m in x], color="black", marker="o", label="IV percentile")
    ax.set_ylabel("0-100")
    ax.set_title(f"{ticker} — IV rank / percentile ({len(window)}-run lookback)")
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    out = os.path.join(OUTPUT_DIR, f"{ticker}_iv_rank.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def _plot_latest_vs_previous(ticker: str, history: pd.DataFrame, maturities: list):
    """Fallback while history is too short for a real IV rank: latest run vs prior run."""
    latest, previous = history.iloc[-1], history.iloc[-2]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(maturities, [previous.get(m) for m in maturities], marker="o", label=f"previous ({previous['timestamp']})")
    ax.plot(maturities, [latest.get(m) for m in maturities], marker="o", label=f"now ({latest['timestamp']})")
    ax.set_xlabel("Maturity")
    ax.set_ylabel("ATM implied volatility")
    ax.set_title(f"{ticker} — ATM IV now vs. previous run (need {IV_RANK_MIN_ROWS}+ runs for IV rank)")
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    out = os.path.join(OUTPUT_DIR, f"{ticker}_iv_now_vs_before.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
