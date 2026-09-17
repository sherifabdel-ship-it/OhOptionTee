"""
Pulls option chains from Yahoo Finance (via yfinance) and filters
them down to "active" contracts only, per the thresholds in config.py.
"""

import yfinance as yf
import pandas as pd
from config import (
    MIN_OPEN_INTEREST,
    MIN_VOLUME,
    MAX_MATURITIES,
    REQUIRE_BID_ASK,
    MONEYNESS_RANGE,
)


def _filter_active(df: pd.DataFrame, spot: float) -> pd.DataFrame:
    """Keep only contracts that look genuinely tradeable right now."""
    out = df.copy()

    oi = out["openInterest"].fillna(0)
    vol = out["volume"].fillna(0)
    out = out[(oi >= MIN_OPEN_INTEREST) | (vol >= MIN_VOLUME)]

    if REQUIRE_BID_ASK:
        bid = out["bid"].fillna(0)
        ask = out["ask"].fillna(0)
        # Outside trading hours Yahoo often shows bid=0 or ask=0 on strikes
        # that still have real open interest, so require just one side
        # (not both) to avoid wiping out liquid names when markets are closed.
        out = out[(bid > 0) | (ask > 0)]

    if MONEYNESS_RANGE:
        lo, hi = spot * (1 - MONEYNESS_RANGE), spot * (1 + MONEYNESS_RANGE)
        out = out[(out["strike"] >= lo) & (out["strike"] <= hi)]

    return out.copy()


def get_option_chains(ticker: str) -> dict:
    """
    Returns { expiration_date_str: {"calls": df, "puts": df, "spot": float} }
    for each maturity, active contracts only.
    """
    tk = yf.Ticker(ticker)
    expirations = tk.options
    if MAX_MATURITIES:
        expirations = expirations[:MAX_MATURITIES]

    spot = tk.history(period="1d")["Close"].iloc[-1]

    chains = {}
    for exp in expirations:
        try:
            chain = tk.option_chain(exp)
        except Exception as e:
            print(f"  skipping {ticker} {exp}: {e}")
            continue

        calls = _filter_active(chain.calls, spot)
        puts = _filter_active(chain.puts, spot)

        if calls.empty and puts.empty:
            continue

        chains[exp] = {"calls": calls, "puts": puts, "spot": spot}

    return chains
