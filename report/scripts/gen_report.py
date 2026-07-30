"""Rebuild ../output/ibkr_results.html from the Flex pipeline data.

Reads  ../data/flex_returns.csv, ../data/benchmark_closes.csv,
       ../data/flex_statement.xml, ../output/ibkr_tear_sheet.png
Writes ../output/ibkr_results.html  (keeps the existing page's CSS)

The tear sheet PNG is embedded as page-sized slices: Chrome's print
fragmentation paints following content over a single multi-page <img>.
"""
import base64
import io
import json
import os
import re
import xml.etree.ElementTree as ET

import pandas as pd
import empyrical as ep
import pyfolio as pf
from PIL import Image

REPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPORT, 'data')
OUT = os.path.join(REPORT, 'output', 'ibkr_results.html')

# ---------------------------------------------------------------- data
f = pd.read_csv(os.path.join(DATA, 'flex_returns.csv'),
                index_col=0, parse_dates=True)
nav, flows, returns = f.nav, f.flow, f.daily_return

closes = pd.read_csv(os.path.join(DATA, 'benchmark_closes.csv'),
                     index_col=0, parse_dates=True)
bench = closes.pct_change().dropna()
common = returns.index.intersection(bench.index)
port_al, bench_al = returns.loc[common], bench.loc[common]

root = ET.parse(os.path.join(DATA, 'flex_statement.xml')).getroot()
stmt = next(root.iter('FlexStatement'))
account = stmt.get('accountId')
pos = list(stmt.iter('OpenPosition'))
n_pos = len(pos)
longv = sum(float(p.get('positionValue') or 0) for p in pos
            if float(p.get('position') or 0) > 0)
shortv = sum(float(p.get('positionValue') or 0) for p in pos
             if float(p.get('position') or 0) < 0)
gross = longv - shortv
n_trades = len(list(stmt.iter('Trade')))

end_nav, start_nav = nav.iloc[-1], nav.iloc[0]
dep_in = flows[flows > 0].sum()
dep_out = flows[flows < 0].sum()
net_flow = flows.sum()
pnl = end_nav - start_nav - net_flow

cum = (1 + returns).cumprod()
twr = cum.iloc[-1] - 1
dd_now = cum.iloc[-1] / cum.max() - 1
stats = pf.timeseries.perf_stats(returns)

ab = {}
for sym in bench_al.columns:
    alpha, beta = ep.alpha_beta_aligned(port_al, bench_al[sym])
    ab[sym] = (float((1 + bench_al[sym]).prod() - 1), beta, alpha)
port_al_cum = float((1 + port_al).prod() - 1)

monthly_p = (1 + returns).resample('ME').prod() - 1
monthly_b = (1 + bench).resample('ME').prod() - 1
monthly_f = flows.resample('ME').sum()

# Tear sheet, sliced into page-sized pieces for clean PDF pagination.
ts = Image.open(os.path.join(REPORT, 'output', 'ibkr_tear_sheet.png'))
W, H = ts.size
SLICE = 1100
ts_imgs = []
n_slices = (H + SLICE - 1) // SLICE
for k, top in enumerate(range(0, H, SLICE)):
    part = ts.crop((0, top, W, min(top + SLICE, H)))
    buf = io.BytesIO()
    part.save(buf, format='PNG')
    ts_imgs.append(
        '<img alt="pyfolio tear sheet, part {} of {}" '
        'src="data:image/png;base64,{}">'.format(
            k + 1, n_slices, base64.b64encode(buf.getvalue()).decode()))

# ------------------------------------------------------------ helpers
def usd(v, dec=0):
    return '${:,.{}f}'.format(v, dec)

def pct(v, dec=2, sign=False):
    s = '+' if (sign and v > 0) else ''
    return s + '{:.{}f}%'.format(v * 100, dec)

def path(xs, ys):
    pts = ['{},{}'.format(round(x, 1), round(y, 1)) for x, y in zip(xs, ys)]
    return 'M' + ' L'.join(pts)

def month_ticks(index, x_of):
    ticks, seen = [], set()
    for i, d in enumerate(index):
        key = (d.year, d.month)
        if key not in seen and d.month % 2 == 0:  # every other month
            seen.add(key)
            ticks.append((x_of(i), d.strftime('%b %y').replace(' 20', ' ')))
        seen.add(key)
    return ticks

# ---------------------------------------------------------- NAV chart
X0, X1, Y0, Y1 = 64, 740, 26, 240  # plot box
n = len(nav)
xs = [X0 + i * (X1 - X0) / (n - 1) for i in range(n)]
NAV_MAX = 130000
y_of = lambda v: Y1 - v / NAV_MAX * (Y1 - Y0)
nav_path = path(xs, [y_of(v) for v in nav])

nav_grid, nav_ticklab = [], []
for t in range(0, NAV_MAX + 1, 25000):
    y = round(y_of(t), 1)
    nav_grid.append('<line class="gridline" x1="64" y1="{y}" x2="740" y2="{y}"></line>'.format(y=y))
    nav_ticklab.append('<text class="tick" x="56" y="{}" text-anchor="end">${}k</text>'
                       .format(y + 3, t // 1000))

flow_dots = []
for i, (d, fl) in enumerate(zip(nav.index, flows)):
    if fl != 0:
        flow_dots.append('<circle class="flowdot" cx="{}" cy="{}" r="3.5"></circle>'
                         .format(round(xs[i], 1), round(y_of(nav.iloc[i]), 1)))

nav_xticks = ['<text class="tick" x="{}" y="262" text-anchor="middle">{}</text>'
              .format(round(x, 1), lab)
              for x, lab in month_ticks(nav.index,
                                        lambda i: xs[i])]

nav_days = [[d.strftime('%Y-%m-%d'), round(v, 0), round(fl, 0), round(r * 100, 2)]
            for d, v, fl, r in zip(nav.index, nav, flows, returns)]

# ---------------------------------------------------- benchmark chart
BX1 = 700  # leave room for end labels
bcum = ((1 + bench_al).cumprod() - 1) * 100
pcum = ((1 + port_al).cumprod() - 1) * 100
m = len(pcum)
bxs = [X0 + i * (BX1 - X0) / (m - 1) for i in range(m)]

lo = min(pcum.min(), bcum.min().min())
hi = max(pcum.max(), bcum.max().max())
B_LO, B_HI = 50 * (int(lo // 50)), 50 * (int(hi // 50) + 1)
by_of = lambda v: Y1 - (v - B_LO) / (B_HI - B_LO) * (Y1 - Y0)

bench_grid = []
for t in range(B_LO, B_HI + 1, 50):
    y = round(by_of(t), 1)
    cls = 'zeroline' if t == 0 else 'gridline'
    bench_grid.append('<line class="{c}" x1="64" y1="{y}" x2="700" y2="{y}"></line>'.format(c=cls, y=y))
    bench_grid.append('<text class="tick" x="56" y="{}" text-anchor="end">{}{}%</text>'
                      .format(y + 3, '+' if t > 0 else ('−' if t < 0 else ''), abs(t)))

series = [('port', 'You', pcum), ('spy', 'SPY', bcum.SPY),
          ('qqq', 'QQQ', bcum.QQQ), ('smh', 'SMH', bcum.SMH)]
bench_paths = ['<path class="benchline bench-{k}" d="{d}"></path>'
               .format(k=k, d=path(bxs, [by_of(v) for v in s]))
               for k, _, s in series]

# end dots + collision-resolved end labels
ends = sorted(((by_of(s.iloc[-1]), k, lab, s.iloc[-1]) for k, lab, s in series))
placed = []
for y, k, lab, v in ends:
    ly = y if not placed else max(y, placed[-1] + 15)
    placed.append(ly)
bench_ends, bench_tags = [], []
for (y, k, lab, v), ly in zip(ends, placed):
    bench_ends.append('<circle class="enddot-{}" cx="700" cy="{}" r="3.5"></circle>'
                      .format(k, round(y, 1)))
    bench_tags.append('<text class="endtag" x="708" y="{}">{} {}</text>'
                      .format(round(ly + 4, 1), lab, pct(v / 100, 1, sign=True)))

bench_xticks = ['<text class="tick" x="{}" y="262" text-anchor="middle">{}</text>'
                .format(round(x, 1), lab)
                for x, lab in month_ticks(pcum.index, lambda i: bxs[i])]

bench_days = [[d.strftime('%Y-%m-%d'), round(pcum.iloc[i], 1),
               round(bcum.SPY.iloc[i], 1), round(bcum.QQQ.iloc[i], 1),
               round(bcum.SMH.iloc[i], 1)]
              for i, d in enumerate(pcum.index)]

# ----------------------------------------------------- tables & stats
NAMES = {'SPY': 'SPY · S&amp;P 500', 'QQQ': 'QQQ · Nasdaq-100',
         'SMH': 'SMH · Semiconductors'}
ab_rows = '\n'.join(
    '          <tr><td>{}</td><td>{}</td><td>{:.2f}</td><td>{}</td></tr>'
    .format(NAMES[s], pct(cumr, 1, sign=True), beta, pct(alpha, 1, sign=True))
    for s, (cumr, beta, alpha) in ab.items())

month_rows = []
for d, r in monthly_p.items():
    flow_m = monthly_f.get(d, 0.0)
    cells = ['<td>{}</td>'.format(d.strftime('%b %Y'))]
    cells.append('<td class="dep">{}</td>'.format(
        ('+' if flow_m > 0 else '−') + usd(abs(flow_m))) if flow_m
        else '<td>—</td>')
    cells.append('<td><b>{}</b></td>'.format(pct(r, 1, sign=True)))
    for s in ['SPY', 'QQQ', 'SMH']:
        v = monthly_b[s].get(d)
        cells.append('<td>{}</td>'.format(pct(v, 1, sign=True)
                                          if v is not None and v == v else '—'))
    month_rows.append('          <tr>' + ''.join(cells) + '</tr>')
month_rows = '\n'.join(month_rows)

S = stats
stats_html = '''
      <dl>
        <div class="row"><dt>Annual return</dt><dd class="mono">{ar}</dd></div>
        <div class="row"><dt>Cumulative return</dt><dd class="mono">{cr}</dd></div>
        <div class="row"><dt>Annual volatility</dt><dd class="mono">{av}</dd></div>
        <div class="row"><dt>Max drawdown</dt><dd class="mono">{dd}</dd></div>
        <div class="row"><dt>Daily value at risk</dt><dd class="mono">{var}</dd></div>
        <div class="row"><dt>Beta (vs SPY)</dt><dd class="mono">{be:.2f}</dd></div>
      </dl>
      <dl>
        <div class="row"><dt>Sharpe ratio</dt><dd class="mono">{sh:.2f}</dd></div>
        <div class="row"><dt>Sortino ratio</dt><dd class="mono">{so:.2f}</dd></div>
        <div class="row"><dt>Calmar ratio</dt><dd class="mono">{ca:.2f}</dd></div>
        <div class="row"><dt>Omega ratio</dt><dd class="mono">{om:.2f}</dd></div>
        <div class="row"><dt>Skew / kurtosis / tail ratio</dt><dd class="mono">{sk:.2f} / {ku:.2f} / {ta:.2f}</dd></div>
        <div class="row"><dt>Alpha (annualized, vs SPY)</dt><dd class="mono">{al}</dd></div>
      </dl>'''.format(
    ar=pct(S['Annual return'], 1, sign=True), cr=pct(S['Cumulative returns'], 1, sign=True),
    av=pct(S['Annual volatility'], 1), dd=pct(S['Max drawdown'], 1),
    var=pct(S['Daily value at risk'], 1), sh=S['Sharpe ratio'],
    so=S['Sortino ratio'], ca=S['Calmar ratio'], om=S['Omega ratio'],
    sk=S['Skew'], ku=S['Kurtosis'], ta=S['Tail ratio'],
    be=ab['SPY'][1], al=pct(ab['SPY'][2], 1, sign=True))

# -------------------------------------------------------------- html
old = open(OUT).read()
css = old[old.index('<style>'):old.index('</style>') + len('</style>')]
# Sliced tear sheet images must butt together and never fragment.
css = css.replace(
    'details img { max-width: 100%; border-radius: 4px; background: #fff; }',
    'details img { display: block; max-width: 100%; background: #fff; }')
css = css.replace('.card, .fact, details { break-inside: avoid; }',
                  '.card, .fact { break-inside: avoid; }')
css = css.replace('details img { break-inside: auto; }',
                  'details img { break-inside: avoid; }')

html = '''<title>IBKR Account · pyfolio Results</title>
''' + css + '''

<main>
  <header>
    <p class="eyebrow">Interactive Brokers · Flex Web Service · @@ACCT@@ · Base currency USD</p>
    <h1>Account performance — full-year Flex statement</h1>
    <p class="subtitle">Daily NAV, cash flows and trades from the official IBKR Activity Flex
    statement, fetched July 30, 2026. Statement period: July 30, 2025 &rarr; July 29, 2026.
    Returns are time-weighted: every deposit and withdrawal is stripped out before compounding.</p>
  </header>

  <div class="facts">
    <div class="fact"><div class="k">Net liquidation</div><div class="v mono">@@NETLIQ@@</div></div>
    <div class="fact"><div class="k">Gross positions</div><div class="v mono">@@GROSS@@</div></div>
    <div class="fact"><div class="k">Open positions</div><div class="v mono">@@NPOS@@</div></div>
    <div class="fact"><div class="k">Trades (12 mo)</div><div class="v mono">@@NTRADES@@</div></div>
    <div class="fact"><div class="k">Net deposits</div><div class="v mono">@@NETDEP@@</div></div>
  </div>

  <section class="card">
    <h2>Time-weighted return, July 2025 &rarr; July 2026</h2>
    <p class="note">Flow-adjusted daily returns: <i>r = (NAV − flow − NAV<sub>prev</sub>) / NAV<sub>prev</sub></i>,
    compounded across @@NDAYS@@ trading days. Deposits (@@DEPIN@@ in, @@DEPOUT@@ out) do not
    count as performance.</p>
    <div class="verdict">
      <span class="num mono">@@TWR@@</span>
      <span class="meta">In dollars the year nets to <b>@@PNL@@</b> of trading P&amp;L on
      @@NETDEP@@ of net contributions &mdash; the strong early run compounded on a small base,
      and the account is currently <b>@@DDNOW@@</b> below its late-June peak.</span>
    </div>
  </section>

  <section class="card">
    <h2>Net asset value and cash flows</h2>
    <p class="note">NAV in base currency; orange dots mark the @@NFLOWS@@ external cash flows.
    NAV peaked at @@NAVPEAK@@ on June 2, 2026.</p>
    <div class="chart-wrap" id="chartwrap">
      <svg viewBox="0 0 800 276" width="100%" role="img"
           aria-label="Line chart of account NAV from July 2025 to July 2026, rising from about $4,000 to a peak of $127,000 in early June 2026, then falling to about $70,000">
        @@NAVGRID@@
        @@NAVTICKS@@
        <path class="navline" d="@@NAVPATH@@"></path>
        @@FLOWDOTS@@
        @@NAVXTICKS@@
        <rect id="navhit" class="hit" x="64" y="20" width="676" height="226"></rect>
      </svg>
      <div id="tip" class="mono"></div>
    </div>
  </section>

  <section class="card">
    <h2>Benchmark comparison — SPY, QQQ, SMH</h2>
    <p class="note">Cumulative return from the July 31, 2025 close, IBKR daily closes through
    July 29, 2026 (price-only: benchmark dividends are not reinvested, which flatters the
    portfolio by roughly 1% against SPY).</p>
    <div class="legend">
      <span class="chip"><span class="sw" style="background:var(--series-nav)"></span>Portfolio</span>
      <span class="chip"><span class="sw" style="background:var(--series-flow)"></span>SPY · S&amp;P 500</span>
      <span class="chip"><span class="sw" style="background:var(--series-3)"></span>QQQ · Nasdaq-100</span>
      <span class="chip"><span class="sw" style="background:var(--series-4)"></span>SMH · Semiconductors</span>
    </div>
    <div class="chart-wrap" id="benchwrap">
      <svg viewBox="0 0 800 276" width="100%" role="img"
           aria-label="Line chart comparing cumulative returns July 2025 to July 2026: portfolio up 39.5% with a peak near 175%, SMH up 74.6%, QQQ up 17.1%, SPY up 15.4%">
        @@BENCHGRID@@
        @@BENCHPATHS@@
        @@BENCHENDS@@
        @@BENCHTAGS@@
        @@BENCHXTICKS@@
        <rect id="benchhit" class="hit" x="64" y="20" width="636" height="226"></rect>
      </svg>
      <div id="benchtip" class="mono"></div>
    </div>

    <p class="note" style="margin-top:18px">Beta is the regression slope of daily portfolio
    returns on each benchmark; alpha is the annualized excess after removing
    <i>beta &times; benchmark</i>. A beta of @@BETASPY@@ on SPY with only 1.61 on SMH says the
    account behaves like leveraged semiconductor exposure &mdash; consistent with @@GROSS@@ of
    positions on @@NETLIQ@@ of equity (@@LEV@@&times; gross leverage).</p>
    <div style="overflow-x:auto">
      <table class="mono">
        <thead>
          <tr><th>Benchmark</th><th>Period return</th><th>Beta</th><th>Alpha (annualized)</th></tr>
        </thead>
        <tbody>
@@ABROWS@@
          <tr><td><b>Portfolio</b></td><td><b>@@PORTAL@@</b></td><td>—</td><td>—</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="card">
    <h2>Monthly returns</h2>
    <p class="note">Portfolio months are flow-adjusted; July 2025 covers only the last three
    sessions of the month. Benchmark columns start August 2025.</p>
    <div style="overflow-x:auto">
      <table class="mono">
        <thead>
          <tr><th>Month</th><th>Net flow</th><th>Portfolio</th><th>SPY</th><th>QQQ</th><th>SMH</th></tr>
        </thead>
        <tbody>
@@MONTHROWS@@
        </tbody>
      </table>
    </div>
  </section>

  <section class="card">
    <h2>pyfolio performance statistics</h2>
    <p class="note">Computed by <code>pyfolio.timeseries.perf_stats</code> on the full
    @@NDAYS@@-day series; alpha and beta are regressed against SPY on the @@NALIGN@@
    aligned trading days. The 79% annual volatility and −49.5% max drawdown are the cost
    of the leverage that produced the headline return.</p>
    <div class="stats">@@STATS@@
    </div>
  </section>

  <details>
    <summary>Full pyfolio tear sheet</summary>
    <div class="inner">
      <p class="note">Generated by <code>create_returns_tear_sheet</code> from the flow-adjusted
      Flex return series, with SPY as the benchmark (adds the alpha/beta rows and the
      rolling-beta panel).</p>
      @@TSIMGS@@
    </div>
  </details>

  <footer>
    Method: daily NAV from the Flex statement&rsquo;s <code>EquitySummaryInBase</code> section;
    external flows from <code>CashTransactions</code> (Deposits/Withdrawals). Daily return
    <code>(NAV − flow − NAV<sub>prev</sub>) / NAV<sub>prev</sub></code> gives a true
    time-weighted series. Benchmarks: IBKR daily closes (SPY, QQQ, SMH primary US listings),
    price-only; alpha/beta via <code>empyrical.alpha_beta_aligned</code> on @@NALIGN@@ aligned
    trading days. Analysis run with pyfolio-2026 (commit 667960c) on Python 3.12 / pandas 2.3.
  </footer>
</main>

<script>
  (function () {
    var days = @@NAVDAYS@@;
    var svg = document.getElementById('navhit');
    var tip = document.getElementById('tip');
    var wrap = document.getElementById('chartwrap');
    svg.addEventListener('mousemove', function (e) {
      var b = svg.getBoundingClientRect();
      var i = Math.round((e.clientX - b.left) / b.width * (days.length - 1));
      i = Math.max(0, Math.min(days.length - 1, i));
      var d = days[i];
      tip.style.display = 'block';
      tip.textContent = d[0] + ' · NAV $' + d[1].toLocaleString() +
        (d[2] ? ' · flow ' + (d[2] > 0 ? '+$' : '−$') + Math.abs(d[2]).toLocaleString() : '') +
        ' · ' + (d[3] > 0 ? '+' : '') + d[3].toFixed(2) + '%';
      var w = wrap.getBoundingClientRect();
      tip.style.left = Math.min(e.clientX - w.left + 14, w.width - tip.offsetWidth - 4) + 'px';
      tip.style.top = (e.clientY - w.top - 34) + 'px';
    });
    svg.addEventListener('mouseleave', function () { tip.style.display = 'none'; });
  })();

  (function () {
    var days = @@BENCHDAYS@@;
    var svg = document.getElementById('benchhit');
    var tip = document.getElementById('benchtip');
    var wrap = document.getElementById('benchwrap');
    function fmt(v) { return (v > 0 ? '+' : '') + v.toFixed(1) + '%'; }
    svg.addEventListener('mousemove', function (e) {
      var b = svg.getBoundingClientRect();
      var i = Math.round((e.clientX - b.left) / b.width * (days.length - 1));
      i = Math.max(0, Math.min(days.length - 1, i));
      var d = days[i];
      tip.style.display = 'block';
      tip.textContent = d[0] + ' · You ' + fmt(d[1]) + ' · SPY ' + fmt(d[2]) +
        ' · QQQ ' + fmt(d[3]) + ' · SMH ' + fmt(d[4]);
      var w = wrap.getBoundingClientRect();
      tip.style.left = Math.min(e.clientX - w.left + 14, w.width - tip.offsetWidth - 4) + 'px';
      tip.style.top = (e.clientY - w.top - 34) + 'px';
    });
    svg.addEventListener('mouseleave', function () { tip.style.display = 'none'; });
  })();

  window.addEventListener('beforeprint', function () {
    document.querySelectorAll('details').forEach(function (d) {
      d.dataset.wasOpen = d.open ? '1' : '';
      d.open = true;
    });
  });
  window.addEventListener('afterprint', function () {
    document.querySelectorAll('details').forEach(function (d) {
      d.open = d.dataset.wasOpen === '1';
    });
  });
</script>
'''

subs = {
    '@@ACCT@@': account,
    '@@NETLIQ@@': usd(end_nav),
    '@@GROSS@@': usd(gross),
    '@@NPOS@@': str(n_pos),
    '@@NTRADES@@': '{:,}'.format(n_trades),
    '@@NETDEP@@': '+' + usd(net_flow),
    '@@NDAYS@@': str(len(returns)),
    '@@DEPIN@@': usd(dep_in),
    '@@DEPOUT@@': usd(-dep_out),
    '@@TWR@@': pct(twr, 2, sign=True),
    '@@PNL@@': ('+' if pnl > 0 else '−') + usd(abs(pnl)),
    '@@DDNOW@@': pct(dd_now, 1),
    '@@NFLOWS@@': str(int((flows != 0).sum())),
    '@@NAVPEAK@@': usd(nav.max()),
    '@@NAVGRID@@': '\n        '.join(nav_grid),
    '@@NAVTICKS@@': '\n        '.join(nav_ticklab),
    '@@NAVPATH@@': nav_path,
    '@@FLOWDOTS@@': '\n        '.join(flow_dots),
    '@@NAVXTICKS@@': '\n        '.join(nav_xticks),
    '@@BENCHGRID@@': '\n        '.join(bench_grid),
    '@@BENCHPATHS@@': '\n        '.join(bench_paths),
    '@@BENCHENDS@@': '\n        '.join(bench_ends),
    '@@BENCHTAGS@@': '\n        '.join(bench_tags),
    '@@BENCHXTICKS@@': '\n        '.join(bench_xticks),
    '@@BETASPY@@': '{:.2f}'.format(ab['SPY'][1]),
    '@@LEV@@': '{:.1f}'.format(gross / end_nav),
    '@@ABROWS@@': ab_rows,
    '@@PORTAL@@': pct(port_al_cum, 1, sign=True),
    '@@MONTHROWS@@': month_rows,
    '@@STATS@@': stats_html,
    '@@TSIMGS@@': '\n      '.join(ts_imgs),
    '@@NALIGN@@': str(len(common)),
    '@@NAVDAYS@@': json.dumps(nav_days),
    '@@BENCHDAYS@@': json.dumps(bench_days),
}
for k, v in subs.items():
    html = html.replace(k, v)

leftover = re.findall(r'@@[A-Z0-9]+@@', html)
assert not leftover, leftover

open(OUT, 'w').write(html)
print('wrote', OUT, len(html), 'bytes')
