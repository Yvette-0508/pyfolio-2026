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
    └── render_pdf.sh       HTML report -> PDF via headless Chrome
```

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
