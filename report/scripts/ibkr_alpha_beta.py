"""Alpha/beta split of the IBKR account vs SPY, QQQ, SMH.

Reads ../data/flex_returns.csv (flow-adjusted daily returns from the
Flex pipeline; falls back to ../data/ibkr_returns.csv) and
../data/benchmark_closes.csv (daily closes via the Claude IBKR
connector — ask Claude to refresh it).

Benchmark returns are price-only (dividends not reinvested), so
benchmark period returns understate total return by the dividend
yield (~1% for SPY over a year).
"""
import os

import pandas as pd
import empyrical as ep
import pyfolio as pf

REPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPORT, 'data')

flex_path = os.path.join(DATA, 'flex_returns.csv')
if os.path.exists(flex_path):
    df = pd.read_csv(flex_path, index_col=0, parse_dates=True)
    portfolio = df.daily_return
else:
    df = pd.read_csv(os.path.join(DATA, 'ibkr_returns.csv'),
                     index_col=0, parse_dates=True)
    portfolio = (1 + df.cum_return).pct_change().fillna(df.cum_return.iloc[0])

closes = pd.read_csv(os.path.join(DATA, 'benchmark_closes.csv'),
                     index_col=0, parse_dates=True)
bench = closes.pct_change().dropna()

# Align on days both the account and the benchmarks traded.
common = portfolio.index.intersection(bench.index)
portfolio = portfolio.loc[common]
bench = bench.loc[common]
print('aligned {} common trading days: {} -> {}\n'.format(
    len(common), common[0].date(), common[-1].date()))

print(f"{'benchmark':<10}{'period return':>15}"
      f"{'beta':>10}{'alpha (ann.)':>14}")
for sym in bench.columns:
    rets = bench[sym]
    alpha, beta = ep.alpha_beta_aligned(portfolio, rets)
    cum = (1 + rets).prod() - 1
    print(f"{sym:<10}{cum:>14.4%}{beta:>10.4f}{alpha:>13.4%}")

port_cum = (1 + portfolio).prod() - 1
print(f"{'Portfolio':<10}{port_cum:>14.4%}")

stats = pf.timeseries.perf_stats(portfolio, factor_returns=bench['SPY'])
print('\npyfolio perf_stats with factor_returns=SPY:')
print(stats.loc[['Alpha', 'Beta']])

monthly = (1 + pd.DataFrame(bench).assign(Portfolio=portfolio)) \
    .resample('ME').prod() - 1
print('\nmonthly returns (%):')
print((monthly * 100).round(2).to_string())
