"""Run pyfolio on IBKR Portfolio Analyst data (TWR cumulative returns).

Reads  ../data/ibkr_returns.csv   (date, cum_return, nav)
Writes ../output/ibkr_tear_sheet.png
"""
import os

import matplotlib
matplotlib.use('Agg')

import pandas as pd
import pyfolio as pf

REPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

df = pd.read_csv(os.path.join(REPORT, 'data', 'ibkr_returns.csv'),
                 index_col=0, parse_dates=True)
df.index = df.index.tz_localize('UTC')

# IBKR reports cumulative TWR from period start; convert to daily returns.
returns = (1 + df.cum_return).pct_change().fillna(df.cum_return.iloc[0])

print('daily returns:')
print(returns)

stats = pf.timeseries.perf_stats(returns)
print('\nperf stats:')
print(stats)

fig = pf.create_returns_tear_sheet(returns, return_fig=True)
out = os.path.join(REPORT, 'output', 'ibkr_tear_sheet.png')
fig.savefig(out, dpi=80, bbox_inches='tight')
print('\ntear sheet saved to', out)
