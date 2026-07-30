"""Compute account returns two independent ways at full precision.

1. IBKR Portfolio Analyst cps series (cumulative TWR from period start).
2. NAV-based TWR: deposits inferred from NAV jumps (valid while the
   account has zero trades and zero positions, so every NAV change is a
   cash flow, not P&L; once trading starts, take flows from statements
   or a Flex Query instead).

Reads  ../data/ibkr_returns.csv
Writes ../data/ibkr_accurate.csv
"""
import os

import pandas as pd
import pyfolio as pf

REPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

df = pd.read_csv(os.path.join(REPORT, 'data', 'ibkr_returns.csv'),
                 index_col=0, parse_dates=True)
df.index = df.index.tz_localize('UTC')

# Method 1: from IBKR's cumulative TWR series
rets_cps = (1 + df.cum_return).pct_change().fillna(df.cum_return.iloc[0])

# Method 2: from NAV with external flows removed
nav = df.nav.astype(float)
flows = nav.diff().fillna(nav.iloc[0])
prev_nav = nav.shift(1)
rets_nav = ((nav - flows - prev_nav) / prev_nav).fillna(0.0)

comparison = pd.DataFrame({
    'nav': nav,
    'deposit': flows,
    'ret_ibkr_cps': rets_cps,
    'ret_nav_based': rets_nav,
})
pd.set_option('display.float_format', lambda x: f'{x:.10f}')
print(comparison.to_string())
print('\nmax abs difference between methods:',
      float((rets_cps - rets_nav).abs().max()))

stats = pf.timeseries.perf_stats(rets_nav)
print('\nperf stats (full precision):')
for k, v in stats.items():
    print(f'  {k}: {v!r}')

comparison.to_csv(os.path.join(REPORT, 'data', 'ibkr_accurate.csv'))
