"""
Entry point. Run this file (e.g. `python main.py`) or trigger it
from your GitHub Actions workflow.

To change what runs: edit config.py — TICKERS and FEATURES.
Nothing in this file needs to change for day-to-day use.
"""

from config import TICKERS, FEATURES
from fetch_data import get_option_chains
from plots import plot_term_structure, plot_3d_surface, plot_gamma_wall, plot_skew
from iv_history import save_snapshot_and_plot


def run_for_ticker(ticker: str):
    print(f"\n=== {ticker} ===")
    chains = get_option_chains(ticker)
    if not chains:
        print("  no active contracts found, skipping.")
        return

    print(f"  {len(chains)} maturities with active contracts")

    if FEATURES["term_structure"]:
        path = plot_term_structure(ticker, chains)
        print(f"  term structure -> {path}")

    if FEATURES["surface_3d"]:
        path = plot_3d_surface(ticker, chains)
        print(f"  3D surface -> {path}")

    if FEATURES["gamma_wall"]:
        path = plot_gamma_wall(ticker, chains)
        print(f"  gamma wall -> {path}")

    if FEATURES["skew"]:
        path = plot_skew(ticker, chains)
        print(f"  skew -> {path}")

    if FEATURES["iv_history"]:
        path = save_snapshot_and_plot(ticker, chains)
        print(f"  IV now vs before -> {path or '(saved snapshot, no prior run yet)'}")


def main():
    for ticker in TICKERS:
        run_for_ticker(ticker)


if __name__ == "__main__":
    main()
