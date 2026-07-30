"""Convert a fetched Flex statement into pyfolio-ready CSVs.

Reads  ../data/flex_statement.xml   (from flex_fetch.py)
Writes ../data/flex_returns.csv     daily NAV, external flows, returns
       ../data/flex_transactions.csv one row per trade (if the query
                                     includes the Trades section)

Returns use the flow-adjusted formula
    r_t = (NAV_t - flow_t - NAV_{t-1}) / NAV_{t-1}
with flows taken from Deposits/Withdrawals cash transactions, so the
result is a true time-weighted daily return series.
"""
import os
import sys
import xml.etree.ElementTree as ET

import pandas as pd

REPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XML_PATH = os.path.join(REPORT, 'data', 'flex_statement.xml')

if not os.path.exists(XML_PATH):
    sys.exit('No statement found; run flex_fetch.py first.')

root = ET.fromstring(open(XML_PATH).read())

for stmt in root.iter('FlexStatement'):
    account = stmt.get('accountId')
    print('processing account', account)

    # NAV series: EquitySummaryInBase section
    nav_rows = [(e.get('reportDate'), float(e.get('total')))
                for e in stmt.iter('EquitySummaryByReportDateInBase')
                if e.get('total')]
    if not nav_rows:
        print('  no EquitySummaryInBase section in the query; add '
              '"Net Asset Value (NAV) in Base" and re-fetch')
        continue
    nav = (pd.DataFrame(nav_rows, columns=['date', 'nav'])
           .assign(date=lambda d: pd.to_datetime(d.date))
           .set_index('date').nav.sort_index())

    # External flows: Deposits/Withdrawals cash transactions
    flow_rows = [(t.get('dateTime', '')[:8], float(t.get('amount')))
                 for t in stmt.iter('CashTransaction')
                 if t.get('type') == 'Deposits/Withdrawals']
    flows = pd.Series(0.0, index=nav.index)
    for date_str, amount in flow_rows:
        date = pd.to_datetime(date_str)
        if date in flows.index:
            flows[date] += amount

    prev = nav.shift(1)
    returns = ((nav - flows - prev) / prev).fillna(0.0)

    out = pd.DataFrame({'nav': nav, 'flow': flows, 'daily_return': returns})
    returns_path = os.path.join(REPORT, 'data', 'flex_returns.csv')
    out.to_csv(returns_path)
    print('  wrote', returns_path, f'({len(out)} days)')

    # Trades -> pyfolio transactions frame (amount, price, symbol)
    trade_rows = [(t.get('dateTime'), float(t.get('quantity')),
                   float(t.get('tradePrice')), t.get('symbol'))
                  for t in stmt.iter('Trade')]
    if trade_rows:
        txns = pd.DataFrame(trade_rows,
                            columns=['dt', 'amount', 'price', 'symbol'])
        txns['dt'] = pd.to_datetime(txns.dt.str.replace(';', ' '))
        txns = txns.set_index('dt').sort_index()
        txn_path = os.path.join(REPORT, 'data', 'flex_transactions.csv')
        txns.to_csv(txn_path)
        print('  wrote', txn_path, f'({len(txns)} trades)')
    else:
        print('  no trades in statement')

    print('  usage: returns = pd.read_csv(..., index_col=0, parse_dates=True)'
          '.daily_return.tz_localize("UTC")\n'
          '         pf.create_returns_tear_sheet(returns)')
