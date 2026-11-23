"""Backtest a 200-session S&P 500 total-return moving average."""
import argparse
import json
from collections import deque
from datetime import date, datetime, timezone
from math import isfinite, log
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ESP500TR"
START = 567993600
WINDOW = 200


def load_prices(cache, end):
    if cache and cache.exists():
        raw = cache.read_bytes()
    else:
        stop = int(datetime.combine(end, datetime.min.time(), timezone.utc).timestamp())
        request = Request(f"{URL}?period1={START}&period2={stop}&interval=1d",
                          headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=30) as response:
            raw = response.read()
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(raw)
    result = json.loads(raw)["chart"]["result"][0]
    if result["meta"]["symbol"] != "^SP500TR":
        raise ValueError("Expected the S&P 500 Total Return Index.")
    closes = result["indicators"]["quote"][0]["close"]
    prices = {}
    for stamp, close in zip(result["timestamp"], closes, strict=True):
        day = datetime.fromtimestamp(stamp, timezone.utc).date()
        if day < end and close is not None and isfinite(close) and close > 0:
            prices[day] = close
    return sorted(prices.items())


def backtest(prices, cost):
    if len(prices) < WINDOW + 2:
        raise ValueError("Need at least 202 market closes.")
    window = deque((close for _, close in prices[:WINDOW]), maxlen=WINDOW)
    first_day, first_close = prices[WINDOW - 1]
    previous_close = first_close
    signal = first_close > sum(window) / WINDOW
    invested = False
    strategy = 100.0
    strategy_peak = benchmark_peak = 100.0
    rows = [(first_day, 100.0, 100.0, 0.0, 0.0)]
    trades = exposed = 0

    for day, close in prices[WINDOW:]:
        # Earn today's close-to-close move only if already in at yesterday's close.
        if invested:
            strategy *= close / previous_close
            exposed += 1

        # At today's close, execute the signal computed at yesterday's close.
        if invested != signal:
            strategy *= 1 - cost
            trades += 1
        invested = signal
        window.append(close)
        signal = close > sum(window) / WINDOW

        benchmark = 100 * close / first_close
        strategy_peak = max(strategy_peak, strategy)
        benchmark_peak = max(benchmark_peak, benchmark)
        rows.append((day, strategy, benchmark,
                     100 * (strategy / strategy_peak - 1),
                     100 * (benchmark / benchmark_peak - 1)))
        previous_close = close
    return rows, trades, exposed


def chart(rows, title, columns, ticks, transform, suffix):
    width, height = 900, 300
    left, right, top, bottom = 65, 875, 16, 269
    first, last = rows[0][0], rows[-1][0]
    low, high = transform(ticks[0]), transform(ticks[-1])

    def x(day):
        return left + (right - left) * (day - first).days / (last - first).days

    def y(value):
        return bottom - (bottom - top) * (transform(value) - low) / (high - low)

    parts = [f'<svg role="img" aria-label="{title}" viewBox="0 0 {width} {height}">']
    for tick in ticks:
        point = y(tick)
        parts.append(f'<path class="grid" d="M{left} {point:.1f}H{right}"/>'
                     f'<text x="{left - 8}" y="{point + 4:.1f}" text-anchor="end">{tick:,}{suffix}</text>')
    for year in range(1990, last.year + 1, 5):
        day = date(year, 1, 1)
        if first < day < last:
            point = x(day)
            parts.append(f'<path class="grid" d="M{point:.1f} {top}V{bottom}"/>'
                         f'<text x="{point:.1f}" y="{bottom + 21}" text-anchor="middle">{year}</text>')
    for column, color in zip(columns, ("#106a65", "#5144a2")):
        points = " ".join(f"{x(row[0]):.1f},{y(row[column]):.1f}" for row in rows)
        parts.append(f'<polyline points="{points}" stroke="{color}" fill="none" stroke-width="1.7"/>')
    parts.append("</svg>")
    return "".join(parts)


def write_report(rows, trades, exposed, cost, output, input_start):
    first, last = rows[0][0], rows[-1][0]
    years = (last - first).days / 365.2425
    records = []
    for name, value, drawdown in (("200-day rule", 1, 3), ("Buy and hold", 2, 4)):
        end = rows[-1][value]
        annualized = 100 * ((end / 100) ** (1 / years) - 1)
        worst = min(row[drawdown] for row in rows)
        records.append((name, end, annualized, worst))

    table = "".join(f"<tr><th scope='row'>{name}</th><td>{end:,.2f}</td>"
                    f"<td>{annual:.2f}%</td><td>{worst:.2f}%</td></tr>"
                    for name, end, annual, worst in records)
    value_ticks = [100, 250, 500, 1000, 2500, 5000]
    minimum = min(min(row[1:3]) for row in rows)
    while value_ticks[0] > minimum:
        value_ticks.insert(0, value_ticks[0] // 2)
    while value_ticks[-1] < max(max(row[1:3]) for row in rows):
        value_ticks.append(value_ticks[-1] * 2)
    drawdown_ticks = list(range(-10 * int((-min(record[3] for record in records)) // 10 + 1), 1, 10))
    equity = chart(rows, "Portfolio value on a logarithmic scale", (1, 2), value_ticks, log, "")
    drawdown = chart(rows, "Percentage decline from each portfolio's own peak", (3, 4),
                     drawdown_ticks, float, "%")

    output.write_text(f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>S&amp;P 500 moving-average backtest</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f1f5f6;color:#13252a;font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1050px;margin:auto;padding:clamp(12px,4vw,44px)}}h1{{font-size:clamp(28px,5vw,46px);line-height:1.1;margin:0}}
section{{background:#fff;border:1px solid #d7e2e4;border-radius:14px;margin:20px 0;padding:clamp(11px,2vw,24px)}}
h2{{margin:0;font-size:21px}}p{{margin:8px 0 12px}}svg{{display:block;width:100%;height:auto}}svg text{{font-size:13px;fill:#41565b}}
.grid{{stroke:#d8e2e4;fill:none}}.rule{{color:#106a65}}.hold{{color:#5144a2}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:clamp(12px,2vw,16px)}}
td,th{{text-align:right;border-bottom:1px solid #d8e2e4;padding:9px 4px}}th:first-child{{text-align:left}}
</style><main>
<h1>Does a 200-day rule reduce drawdowns?</h1>
<p>S&amp;P 500 Total Return · {first} to {last} · Dividends reinvested</p>
<section><h2>Backtest results</h2>
<table><thead><tr><th scope="col">Strategy</th><th scope="col">Ending value</th>
<th scope="col">Annualized return</th><th scope="col">Worst drawdown</th></tr></thead>
<tbody>{table}</tbody></table>
<p>The rule switched positions {trades} times and held the index for {exposed / (len(rows)-1):.1%} of the measured sessions.</p>
</section>
<section><h2>Growth of 100</h2><p><b class="rule">━ 200-day rule</b> &nbsp; <b class="hold">━ Buy and hold</b> · Logarithmic scale</p>{equity}</section>
<section><h2>Drawdown from each portfolio's peak</h2><p><b class="rule">━ 200-day rule</b> &nbsp; <b class="hold">━ Buy and hold</b></p>{drawdown}</section>
<section><h2>How the rule works</h2>
<p>At each close, compare the total-return index with its average over the latest 200 sessions. If the index is above the average, hold it from the following close onward. Otherwise, switch to cash at that close.</p>
<p>Cash earns 0%. Each switch costs {cost*10000:g} basis points. Taxes and tracking differences are excluded. Both portfolios start at the end of the 200-session warm-up. Input history starts on {input_start}.</p>
<p>Source: <a href="https://finance.yahoo.com/quote/%5ESP500TR/history/">Yahoo Finance S&amp;P 500 Total Return history</a>.</p>
</section></main></html>""", encoding="utf-8")
    for name, end, annual, worst in records:
        print(f"{name:14} Ending value {end:,.2f} | Annualized {annual:.2f}% | Drawdown {worst:.2f}%")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, help="Read or save Yahoo's chart response")
    parser.add_argument("--end", type=date.fromisoformat, default=date.today(),
                        help="Exclusive end date (YYYY-MM-DD)")
    parser.add_argument("--cost-bps", type=float, default=5)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("moving_average_backtest.html"))
    args = parser.parse_args()
    if not 0 <= args.cost_bps < 10000:
        parser.error("--cost-bps must be in [0, 10000)")
    prices = load_prices(args.cache, args.end)
    cost = args.cost_bps / 10000
    rows, trades, exposed = backtest(prices, cost)
    write_report(rows, trades, exposed, cost, args.output, prices[0][0])
    print(f"{len(prices):,} input closes, {prices[0][0]} to {prices[-1][0]}")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
