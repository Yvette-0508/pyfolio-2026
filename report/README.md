# Account reports

Performance analysis of a live IBKR account, built on this repo's pyfolio.

**Everything in here except this README and `scripts/` is gitignored** —
`data/` and `output/` hold personal financial data and must never be
committed to this public repo.

## Layout

```
report/
├── data/      account return series pulled from IBKR (gitignored)
│   ├── ibkr_returns.csv    date, cumulative TWR, NAV
│   └── ibkr_accurate.csv   full-precision return cross-check
├── output/    generated reports (gitignored)
│   ├── ibkr_results.html   the report page (published as a Claude artifact)
│   ├── ibkr_report_*.pdf   PDF exports
│   └── ibkr_tear_sheet.png pyfolio tear sheet
└── scripts/   analysis scripts (committed)
    ├── ibkr_accurate.py    returns two ways: IBKR TWR vs NAV-with-flows
    ├── ibkr_tear_sheet.py  pyfolio returns tear sheet -> PNG
    ├── ibkr_alpha_beta.py  alpha/beta split vs SPY, QQQ, SMH
    ├── flex_fetch.py       download a Flex statement from IBKR
    ├── flex_to_pyfolio.py  Flex XML -> returns/transactions CSVs
    └── render_pdf.sh       HTML report -> PDF via headless Chrome
```

## Flex Web Service setup (one time)

1. In IBKR Client Portal: **Performance & Reports → Flex Queries** →
   create an **Activity Flex Query** for the account. Include at least
   *Net Asset Value (NAV) in Base*, *Cash Transactions*, *Trades*, and
   *Open Positions*; date period "Last 365 Calendar Days".
2. **Reports → Settings → Flex Web Service** → enable, generate a token.
3. Save both in `data/flex_credentials` (gitignored):

   ```
   TOKEN=<flex web service token>
   QUERY_ID=<activity query id>
   ```

Then `python flex_fetch.py && python flex_to_pyfolio.py` produces
`data/flex_returns.csv` (true TWR daily returns, flow-adjusted) and
`data/flex_transactions.csv` ready for pyfolio.

## Refreshing

The IBKR data comes through the Claude IBKR connector (Portfolio Analyst
performance, positions, trades, benchmark price history) — ask Claude to
refresh `data/ibkr_returns.csv` and the benchmark closes, then:

```sh
cd report/scripts
PYTHONPATH=../.. python ibkr_accurate.py     # verify returns
PYTHONPATH=../.. python ibkr_tear_sheet.py   # regenerate tear sheet
PYTHONPATH=../.. python ibkr_alpha_beta.py   # benchmark split
./render_pdf.sh                              # export PDF
```

The published report lives at the Claude artifact URL from the session;
republishing the edited `output/ibkr_results.html` keeps the same link.
