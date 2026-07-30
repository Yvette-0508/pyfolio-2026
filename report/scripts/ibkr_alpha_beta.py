"""Alpha/beta split of the IBKR account vs SPY, QQQ, SMH.

Benchmark closes were pulled from IBKR (daily bars through 2026-07-29)
via the Claude IBKR connector; paste refreshed closes into CLOSES to
update. The close before inception seeds the first day's return so the
benchmark series covers every day the account has existed.

Reads ../data/ibkr_returns.csv for the portfolio return series.
"""
import os

import pandas as pd
import empyrical as ep
import pyfolio as pf

REPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLOSES = {  # last pre-inception close first, then one per account day
    'SPY': [743.29, 742.09, 748.28, 747.41, 738.18, 738.93, 739.09,
            740.86, 729.46],
    'QQQ': [695.33, 696.06, 708.97, 705.35, 691.96, 684.23, 682.12,
            675.49, 661.73],
    'SMH': [556.53, 558.83, 584.08, 586.91, 580.17, 561.19, 548.55,
            529.60, 504.22],
}

df = pd.read_csv(os.path.join(REPORT, 'data', 'ibkr_returns.csv'),
                 index_col=0, parse_dates=True)
df.index = df.index.tz_localize('UTC')
portfolio = (1 + df.cum_return).pct_change().fillna(df.cum_return.iloc[0])

print(f"{'benchmark':<10}{'period return':>15}"
      f"{'beta':>10}{'alpha (ann.)':>14}")
rows = {}
for sym, closes in CLOSES.items():
    px = pd.Series(closes)
    rets = px.pct_change().dropna()
    rets.index = portfolio.index
    alpha, beta = ep.alpha_beta_aligned(portfolio, rets)
    cum = (1 + rets).prod() - 1
    rows[sym] = rets
    print(f"{sym:<10}{cum:>14.4%}{beta:>10.4f}{alpha:>13.4%}")

stats = pf.timeseries.perf_stats(portfolio, factor_returns=rows['SPY'])
print('\npyfolio perf_stats with factor_returns=SPY:')
print(stats.loc[['Alpha', 'Beta']])

daily = pd.DataFrame(rows).assign(Portfolio=portfolio)
cumidx = (1 + daily).cumprod() - 1
print('\ncumulative returns since account inception:')
print((cumidx * 100).round(2).to_string())
