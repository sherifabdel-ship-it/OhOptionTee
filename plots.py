"""
All the chart-drawing functions. Each one saves a PNG into
config.OUTPUT_DIR and returns the file path.
"""

import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 (registers 3D projection)
from config import OUTPUT_DIR

RISK_FREE_RATE = 0.045  # rough constant; good enough for gamma, not meant to be precise


def _bs_gamma(spot: float, strike: float, days_to_expiry: float, iv: float) -> float:
    """
    Black-Scholes gamma. We compute this ourselves because Yahoo's free
    option chain (via yfinance) does NOT include greeks at all -- only
    price/bid/ask/IV/OI/volume. Uses the IV Yahoo does give us.
    """
    if iv is None or iv <= 0 or days_to_expiry <= 0 or spot <= 0 or strike <= 0:
        return float("nan")
    t = days_to_expiry / 365
    d1 = (math.log(spot / strike) + (RISK_FREE_RATE + 0.5 * iv ** 2) * t) / (iv * math.sqrt(t))
    pdf = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
    return pdf / (spot * iv * math.sqrt(t))


def _outpath(name: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, name)


def plot_term_structure(ticker: str, chains: dict):
    """One IV-by-strike curve per maturity, all on one chart."""
    fig, ax = plt.subplots(figsize=(9, 6))
    for exp, data in chains.items():
        calls = data["calls"]
        if calls.empty:
            continue
        c = calls.sort_values("strike")
        ax.plot(c["strike"], c["impliedVolatility"], marker="o", markersize=3, label=exp)

    ax.set_xlabel("Strike")
    ax.set_ylabel("Implied volatility")
    ax.set_title(f"{ticker} — IV by strike, per maturity (calls, active contracts)")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    path = _outpath(f"{ticker}_term_structure.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_3d_surface(ticker: str, chains: dict):
    """IV surface: strike x days-to-expiry x IV."""
    xs, ys, zs = [], [], []
    today = pd.Timestamp.today()

    for exp, data in chains.items():
        calls = data["calls"]
        if calls.empty:
            continue
        dte = (pd.Timestamp(exp) - today).days
        for _, row in calls.iterrows():
            xs.append(row["strike"])
            ys.append(dte)
            zs.append(row["impliedVolatility"])

    if len(xs) < 4:
        return None

    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_trisurf(xs, ys, zs, cmap="viridis", edgecolor="none", alpha=0.9)
    ax.set_xlabel("Strike")
    ax.set_ylabel("Days to expiry")
    ax.set_zlabel("Implied volatility")
    ax.set_title(f"{ticker} — IV surface across maturities")
    fig.tight_layout()
    path = _outpath(f"{ticker}_iv_surface_3d.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_gamma_wall(ticker: str, chains: dict, nearest_only: bool = True):
    """
    Net dealer gamma exposure (GEX) by strike, industry-standard formula:
        GEX = gamma x OI x 100 (contract multiplier) x spot^2 x 0.01
    Calls positive, puts negative — this assumes dealers are net long
    calls / short puts (the common retail-flow assumption; some vendors
    use the opposite sign convention). Units: $ dealer gamma P&L per 1%
    move in spot. Uses nearest maturity by default — that's the one
    dealers are usually hedging hardest.
    """
    if not chains:
        return None

    exp = sorted(chains.keys())[0] if nearest_only else None
    exps = [exp] if nearest_only else chains.keys()
    spot = list(chains.values())[0]["spot"]
    multiplier = 100 * (spot ** 2) * 0.01
    today = pd.Timestamp.today()

    gamma_by_strike = {}
    for e in exps:
        data = chains[e]
        dte = (pd.Timestamp(e) - today).days
        for side, sign in [("calls", 1), ("puts", -1)]:
            df = data[side]
            for _, row in df.iterrows():
                iv = row.get("impliedVolatility", np.nan)
                oi = row.get("openInterest", 0) or 0
                g = _bs_gamma(spot, row["strike"], dte, iv)
                if math.isnan(g):
                    continue
                gex = sign * g * oi * multiplier
                gamma_by_strike[row["strike"]] = gamma_by_strike.get(row["strike"], 0) + gex

    if not gamma_by_strike:
        return None

    strikes = sorted(gamma_by_strike)
    values = [gamma_by_strike[s] for s in strikes]

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#1d9e75" if v >= 0 else "#e24b4a" for v in values]
    ax.bar(strikes, values, color=colors, width=(strikes[-1] - strikes[0]) / max(len(strikes), 1) * 0.8)
    ax.axvline(spot, color="black", linestyle="--", linewidth=1, label=f"spot {spot:.2f}")
    ax.set_xlabel("Strike")
    ax.set_ylabel("Dealer GEX ($ per 1% move)")
    ax.set_title(f"{ticker} — gamma wall ({exp if nearest_only else 'all maturities'})")
    ax.legend()
    fig.tight_layout()
    path = _outpath(f"{ticker}_gamma_wall.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_skew(ticker: str, chains: dict):
    """Put vs call IV by strike for the nearest maturity."""
    if not chains:
        return None
    exp = sorted(chains.keys())[0]
    data = chains[exp]
    calls, puts = data["calls"], data["puts"]

    fig, ax = plt.subplots(figsize=(9, 6))
    if not calls.empty:
        c = calls.sort_values("strike")
        ax.plot(c["strike"], c["impliedVolatility"], label="calls", marker="o", markersize=3)
    if not puts.empty:
        p = puts.sort_values("strike")
        ax.plot(p["strike"], p["impliedVolatility"], label="puts", marker="o", markersize=3)

    spot = data["spot"]
    ax.axvline(spot, color="black", linestyle="--", linewidth=1, label=f"spot {spot:.2f}")
    ax.set_xlabel("Strike")
    ax.set_ylabel("Implied volatility")
    ax.set_title(f"{ticker} — skew ({exp})")
    ax.legend()
    fig.tight_layout()
    path = _outpath(f"{ticker}_skew.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
