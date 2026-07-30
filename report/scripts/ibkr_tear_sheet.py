"""Run pyfolio on the IBKR account return series.

Prefers ../data/flex_returns.csv (flow-adjusted daily returns from the
Flex Web Service pipeline); falls back to ../data/ibkr_returns.csv
(Portfolio Analyst cumulative TWR paste).

Writes ../output/ibkr_tear_sheet.png
"""
import os

import matplotlib
import pandas as pd
import pyfolio as pf

matplotlib.use('Agg')

REPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

flex_path = os.path.join(REPORT, 'data', 'flex_returns.csv')
if os.path.exists(flex_path):
    df = pd.read_csv(flex_path, index_col=0, parse_dates=True)
    df.index = df.index.tz_localize('UTC')
    returns = df.daily_return
    print('using flow-adjusted Flex returns ({} days)'.format(len(returns)))
else:
    df = pd.read_csv(os.path.join(REPORT, 'data', 'ibkr_returns.csv'),
                     index_col=0, parse_dates=True)
    df.index = df.index.tz_localize('UTC')
    # IBKR reports cumulative TWR from period start; convert to daily.
    returns = (1 + df.cum_return).pct_change().fillna(df.cum_return.iloc[0])

# SPY as benchmark, so the tear sheet includes Alpha/Beta and rolling beta.
benchmark = None
bench_path = os.path.join(REPORT, 'data', 'benchmark_closes.csv')
if os.path.exists(bench_path):
    closes = pd.read_csv(bench_path, index_col=0, parse_dates=True)
    benchmark = closes.SPY.pct_change().dropna()
    benchmark.index = benchmark.index.tz_localize('UTC')
    common = returns.index.intersection(benchmark.index)
    benchmark = benchmark.loc[common]
    print('benchmark: SPY, {} aligned days'.format(len(common)))

# Clip to the aligned days so rolling beta gets equal-length windows.
if benchmark is not None:
    returns = returns.loc[benchmark.index]

stats = pf.timeseries.perf_stats(returns, factor_returns=benchmark)
print('\nperf stats:')
print(stats)

fig = pf.create_returns_tear_sheet(returns, benchmark_rets=benchmark,
                                   return_fig=True)
out = os.path.join(REPORT, 'output', 'ibkr_tear_sheet.png')
fig.savefig(out, dpi=80, bbox_inches='tight')
print('\ntear sheet saved to', out)
