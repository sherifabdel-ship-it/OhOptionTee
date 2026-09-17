# ---------------------------------------------------------------
# EDIT THIS FILE to change tickers or turn features on/off.
# Nothing else in the project needs to change.
# ---------------------------------------------------------------

# Tickers to run the whole pipeline on
TICKERS = ["ETHU", "USO", "SPY"]

# Turn each feature on (True) or off (False)
FEATURES = {
    "term_structure": True,   # one plot per maturity (active contracts only)
    "surface_3d": True,       # 3D surface across all maturities
    "gamma_wall": True,       # net gamma exposure by strike
    "skew": True,             # IV skew (put/call by strike) per maturity
    "iv_history": True,       # ATM IV now vs. last saved snapshot
}

# A contract counts as "active" if it has at least this much
# open interest OR volume. Raise these to cut out dead strikes.
MIN_OPEN_INTEREST = 10
MIN_VOLUME = 1

# Require a real, non-zero bid or ask (at least one side quoted).
# Requiring both can wipe out liquid names when markets are closed,
# since Yahoo often shows one side as 0 outside trading hours.
REQUIRE_BID_ASK = True

# Only keep strikes within this % of spot (0.20 = strikes from
# 80% to 120% of spot). Cuts out deep OTM/ITM strikes nobody trades.
MONEYNESS_RANGE = 0.20

# How many maturities (expirations) to include, nearest-first.
# None = use all available expirations.
MAX_MATURITIES = None

# IV rank / percentile settings — the standard is a 252-trading-day
# (1yr) lookback, but this tool's "days" are however often you run
# it (e.g. daily via your GitHub workflow), not calendar days.
IV_RANK_LOOKBACK = 252       # max runs to look back over
IV_RANK_MIN_ROWS = 20        # need at least this many runs before showing rank

# Where output PNGs and the IV history CSV get written
OUTPUT_DIR = "outputs"
