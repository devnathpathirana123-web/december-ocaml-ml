# December 2026 · OCaml and machine learning

Learn OCaml alongside applied machine learning. Use Python for the textbook labs and OCaml to implement the ideas yourself.

## Study plan

| Dates | OCaml | Machine learning | Project |
|---|---|---|---|
| Dec 1–7 | Cornell chapters 2–3: functions, recursion, lists, variants, pattern matching | ISLP chapters 2–3: features, baselines, linear regression and loss | Write a moving-average function and fit a simple regression |
| Dec 8–14 | Cornell chapter 4: higher-order functions and folds | ISLP chapters 4–5: classification and validation | Port the 200-day backtest to OCaml and check the trade timing |
| Dec 15–21 | Cornell chapters 5–6: modules and tests | ISLP chapters 6 and 8: regularization, trees, forests and boosting | Implement linear regression in OCaml and check against Python |
| Dec 22–31 | Real World OCaml: command-line parsing and error handling | ISLP chapter 12: PCA and clustering, then a neural-network introduction | Compare the boom/bust classifier with a baseline using walk-forward testing |

## Reading list

- [Cornell OCaml Programming](https://cs3110.github.io/textbook/cover.html)
- [Real World OCaml](https://dev.realworldocaml.org/)
- [An Introduction to Statistical Learning with Python](https://www.statlearning.com/)
- [Mathematics for Machine Learning](https://mml-book.github.io/)
- [Dive into Deep Learning](https://www.d2l.ai/)
- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)

After December, cover time-series forecasting and Monte Carlo risk, cointegration and pairs trading, deep learning, and ML engineering.

## Run the included moving-average backtest

From the directory containing the script, use Python 3.10 or newer. No packages are required.

```sh
python3 moving_average_backtest.py --cache sp500tr.json --end 2026-11-21 --cost-bps 5
```

The first run downloads S&P 500 total-return history from Yahoo Finance. Later runs can reuse the cache. The end date is exclusive. Open the generated `moving_average_backtest.html` in your browser to see growth of 100 and peak-to-trough drawdowns. Use `--help` for options.

The example acts on each signal at the following session's close. Cash earns 0%, and each switch costs 5 basis points. With the November 2026 data snapshot, the rule returned 8.66% annualized with a 24.30% worst drawdown. Buy and hold returned 11.08% annualized with a 55.25% worst drawdown.

The [S&P 500 regression model](https://github.com/devnathpathirana123-web/market-regression) is a separate project.
