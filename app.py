import html as _html
import json
import math
from pathlib import Path

import pandas as pd
import streamlit as st

# ---- Edit these ------------------------------------------------------------
PRODUCT_NAME = "XYZ"   # <-- nijer indicator-er nam din
BUY_URL = "https://your-buy-link"
CTA_TITLE = "Get the indicator"
CTA_TEXT = "Automated setups and pending orders on TradingView."
CTA_BUTTON = "Get access"
LOW_SAMPLE_TRADES = 10  # pairs with fewer trades get a "Low sample" tag
# ----------------------------------------------------------------------------

st.set_page_config(page_title=f"{PRODUCT_NAME}: Backtest Summary", page_icon="📈", layout="wide")
S = json.loads((Path(__file__).parent / "public_snapshot.json").read_text(encoding="utf-8"))
m, k = S["meta"], S["kpi"]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp{background:#0E1116}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],footer,#MainMenu{display:none!important}
.block-container{max-width:1180px!important;padding:32px 24px 48px!important}
.pd{font-family:Inter,system-ui,sans-serif;color:#E6EDF3;display:flex;flex-direction:column;gap:20px}
.pd .card{background:#161B22;border:1px solid #232B36;border-radius:14px;padding:20px}
.pd .lbl{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#9AA4B2;margin:0 0 8px}
.pd .big{font-size:28px;font-weight:700;margin:0;color:#E6EDF3}
.pd .note{font-size:12px;color:#9AA4B2;margin:6px 0 0}
.pd .h2{font-size:18px;font-weight:600;margin:0 0 4px;color:#E6EDF3}
.pd .sub{font-size:13px;color:#9AA4B2;margin:0 0 16px}
.pd .title{font-size:34px;font-weight:700;letter-spacing:-.02em;margin:0;line-height:1.2}
.pd .grid{display:grid;gap:16px}
.pd .hm{display:grid;grid-template-columns:56px repeat(12,1fr) 64px;gap:6px;min-width:760px;font-size:12px;color:#9AA4B2;align-items:center;text-align:center}
.pd .hm div.v{border-radius:6px;padding:10px 0;color:#E6EDF3;font-weight:500}
.pd .hm div.t{font-weight:600;color:#E6EDF3}
.pd table.tbl{width:100%;border-collapse:collapse;font-size:14px;color:#E6EDF3;margin:0}
.pd table.tbl th{text-align:left;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#9AA4B2;font-weight:500;padding:8px 10px;border:0;border-bottom:1px solid #232B36;background:transparent}
.pd table.tbl td{padding:12px 10px;border:0;border-bottom:1px solid #1C232D;background:transparent;color:#E6EDF3}
.pd .pos{color:#2DD4BF!important}
.pd .neg{color:#F97316!important}
.pd .pill{display:inline-block;font-size:12px;padding:3px 10px;border-radius:999px;border:1px solid #2DD4BF;color:#2DD4BF}
.pd .warn{display:inline-block;font-size:12px;padding:3px 10px;border-radius:999px;border:1px solid #F97316;color:#F97316}
.pd .bar{height:8px;border-radius:99px;background:#232B36;overflow:hidden;margin-bottom:16px}
.pd .bar span{display:block;height:100%;background:#2DD4BF}
.pd .step{font-size:15px;line-height:1.6;color:#C9D1DB;margin-top:12px}
.pd .step b{color:#E6EDF3}
.pd .about{font-size:15px;line-height:1.6;color:#C9D1DB;margin:8px 0 0}
.pd a.btn{display:inline-block;background:#2DD4BF;color:#0E1116!important;font-weight:600;text-decoration:none!important;padding:14px 22px;border-radius:10px;min-height:20px}
.pd a.btn:hover{background:#5EEAD4}
.pd .chips{display:flex;flex-wrap:wrap;gap:10px}
.pd .chip{display:inline-flex;align-items:baseline;gap:8px;background:#161B22;border:1px solid #232B36;border-radius:999px;padding:8px 16px;font-size:13px;color:#9AA4B2}
.pd .chip b{font-size:16px;color:#E6EDF3;font-weight:700}
.pd .chip b.pos{color:#2DD4BF}
.pd .hero{font-size:16px;line-height:1.6;color:#C9D1DB;margin:10px 0 0;max-width:760px}
.pd ul.pts{margin:12px 0 0;padding-left:20px;color:#C9D1DB;font-size:15px;line-height:1.65}
.pd ul.pts li{margin-bottom:8px}
.pd ul.pts b{color:#E6EDF3}
.pd .foot{font-size:12px;line-height:1.6;color:#9AA4B2;margin:0}
@media (max-width:640px){.pd .title{font-size:26px}.pd .big{font-size:24px}}
"""


# ---------- helpers ---------------------------------------------------------
def esc(x):
    return _html.escape(str(x))


def num(v, spec, suffix="", dash="-"):
    return dash if v is None else f"{v:{spec}}{suffix}"


def dd(v):
    return "-" if v is None else (f"-{abs(v):.1f}R" if v else "0R")


def sign_cls(v):
    return "pos" if v is not None and v >= 0 else "neg"


def kpi_card(label, value, cls="", note=""):
    n = f"<div class='note'>{esc(note)}</div>" if note else ""
    return f"<div class='card'><div class='lbl'>{esc(label)}</div><div class='big {cls}'>{esc(value)}</div>{n}</div>"


def nice_step(span, n=4):
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    for f in (1, 2, 2.5, 5, 10):
        if raw <= f * mag:
            return f * mag
    return 10 * mag


# ---------- equity curve (inline SVG) --------------------------------------
def equity_svg(xs, ys, oos_start=None):
    if len(ys) < 2:
        return ""
    ts = [pd.Timestamp(x).timestamp() for x in xs]
    t0, t1 = ts[0], ts[-1]
    lo, hi = min(0, min(ys)), max(ys)
    step = nice_step(max(hi - lo, 1e-9))
    tmin, tmax = math.floor(lo / step) * step, math.ceil(hi / step) * step
    top, bot, left, right = 40, 220, 60, 780

    def X(t):
        return left + (t - t0) / ((t1 - t0) or 1) * (right - left)

    def Y(v):
        return bot - (v - tmin) / ((tmax - tmin) or 1) * (bot - top)

    ticks, t = [], tmin
    while t <= tmax + 1e-9:
        ticks.append(t)
        t += step
    grid = "".join(f"<line x1='50' y1='{Y(v):.1f}' x2='790' y2='{Y(v):.1f}'></line>" for v in ticks)
    ylab = "".join(f"<text x='42' y='{Y(v) + 4:.1f}'>{v:g}R</text>" for v in ticks)
    pts = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in zip(ts, ys))
    base = Y(0)
    area = f"M{pts.replace(' ', ' L')} L{X(t1):.1f},{base:.1f} L{X(t0):.1f},{base:.1f} Z"
    xlab = ""
    for i in range(5):
        tt = t0 + (t1 - t0) * i / 4
        xlab += f"<text x='{X(tt):.1f}' y='252'>{pd.Timestamp(tt, unit='s').strftime('%b %y')}</text>"
    oos = ""
    if oos_start:
        xo = X(pd.Timestamp(oos_start).timestamp())
        if left < xo < right:
            oos = (f"<line x1='{xo:.1f}' y1='{top - 10}' x2='{xo:.1f}' y2='{bot}' stroke='#9AA4B2' "
                   f"stroke-dasharray='4 4' stroke-width='1'></line>"
                   f"<text x='{xo + 6:.1f}' y='{top - 2}' fill='#9AA4B2' font-size='11' "
                   f"font-family='Inter,sans-serif'>Out-of-sample</text>")
    return (f"<svg viewBox='0 0 800 270' role='img' aria-label='Weekly equity curve from {ys[0]:g}R to {ys[-1]:g}R' "
            f"style='width:100%;height:auto;display:block'>"
            f"<g stroke='#232B36' stroke-width='1'>{grid}</g>"
            f"<g fill='#9AA4B2' font-size='11' font-family='Inter,sans-serif' text-anchor='end'>{ylab}</g>"
            f"<path d='{area}' fill='#2DD4BF' fill-opacity='0.12'></path>"
            f"<polyline points='{pts}' fill='none' stroke='#2DD4BF' stroke-width='2.5' stroke-linejoin='round'></polyline>"
            f"{oos}"
            f"<g fill='#9AA4B2' font-size='11' font-family='Inter,sans-serif' text-anchor='middle'>{xlab}</g>"
            f"</svg>")


# ---------- monthly heatmap -------------------------------------------------
def heatmap(monthly, yearly):
    mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    vals = [abs(v) for row in monthly.values() for v in row if v is not None]
    mx = max(vals) if vals else 1
    h = "<div class='hm'><div></div>" + "".join(f"<div>{x}</div>" for x in mon) + "<div>Year</div>"
    for y in sorted(monthly):
        h += f"<div class='t'>{esc(y)}</div>"
        for v in monthly[y]:
            if v is None:
                h += "<div style='color:#5B6675'>-</div>"
                continue
            a = 0.14 + 0.50 * min(abs(v) / mx, 1)
            col = "45,212,191" if v >= 0 else "249,115,22"
            h += f"<div class='v' style='background:rgba({col},{a:.2f})'>{v:+.1f}</div>"
        yv = yearly.get(y)
        h += f"<div class='t {sign_cls(yv)}'>{num(yv, '+.1f')}</div>"
    return h + "</div>"


# ---------- tables ----------------------------------------------------------
def cell(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:g}"
    return esc(v)


def table_rows(rows):
    """Generic table from a list of dicts (used for the FTMO table)."""
    if not rows:
        return ""
    keys = list(rows[0].keys())
    head = "".join(f"<th>{esc(str(c).replace('_', ' ')[:1].upper() + str(c).replace('_', ' ')[1:])}</th>" for c in keys)
    body = "".join("<tr>" + "".join(f"<td>{cell(r.get(c))}</td>" for c in keys) + "</tr>" for r in rows)
    return f"<table class='tbl'><tr>{head}</tr>{body}</table>"


def ftmo_table(rows):
    """Risk / trade | Attempts | Passed | Violated | Success | Avg days to pass"""
    body = ""
    for r in rows:
        passed = r.get("Challenges passed") or 0
        viol = (r.get("Violated (max loss)") or 0) + (r.get("Violated (daily loss)") or 0)
        rate = r.get("Success rate")
        days = r.get("Avg total days to full pass")
        body += (f"<tr><td><b>{esc(r.get('Risk per trade'))}</b></td><td>{passed + viol}</td><td>{passed}</td>"
                 f"<td>{viol}</td><td class='pos'><b>{num(rate, 'g', '%')}</b></td>"
                 f"<td>{num(days, '.0f', ' d')}</td></tr>")
    return ("<table class='tbl'><tr><th>Risk / trade</th><th>Attempts</th><th>Passed</th><th>Violated</th>"
            f"<th>Success</th><th>Avg days</th></tr>{body}</table>")


def is_oos_table():
    d = S["is_oos"]
    cols = []
    for key in d:
        low = str(key).lower()
        if "out" in low or "oos" in low:
            cols.append((key, "Out-of-sample", m.get("oos_window", "")))
        else:
            cols.append((key, "In-sample", m.get("is_window", "")))
    spec = [
        ("Trades", "trades", lambda v: num(v, ",.0f"), False),
        ("Net R", "net_r", lambda v: num(v, "+,.1f", "R"), True),
        ("Profit factor", "profit_factor", lambda v: num(v, ".2f"), False),
        ("Win rate", "win_rate", lambda v: num(v, ".0f", "%"), False),
        ("Expectancy", "expectancy_r", lambda v: num(v, ".2f", "R"), False),
        ("Max drawdown", "max_dd_r", dd, False),
        ("Longest losing run", "max_consec_loss", lambda v: num(v, ".0f"), False),
    ]
    head = "<th></th>" + "".join(f"<th>{n}<br>{esc(w)}</th>" for _, n, w in cols)
    body = ""
    for label, key, f, colored in spec:
        body += f"<tr><td>{label}</td>"
        for ck, _, _ in cols:
            v = d[ck].get(key)
            cls = f" class='{sign_cls(v)}'" if colored else ""
            body += f"<td{cls}>{f(v)}</td>"
        body += "</tr>"
    return f"<table class='tbl'><tr>{head}</tr>{body}</table>"


def pairs_table():
    rows = sorted(S["pairs"], key=lambda r: r.get("net_r") or 0, reverse=True)
    body = ""
    for r in rows:
        low = "<span class='warn'>Low sample</span>" if (r.get("trades") or 0) < LOW_SAMPLE_TRADES else ""
        body += (f"<tr><td>{esc(r['pair'])}</td><td>{num(r.get('trades'), ',.0f')}</td>"
                 f"<td>{num(r.get('win_rate'), '.0f', '%')}</td>"
                 f"<td class='{sign_cls(r.get('net_r'))}'>{num(r.get('net_r'), '+,.1f', 'R')}</td><td>{low}</td></tr>")
    return ("<table class='tbl'><tr><th>Pair</th><th>Trades</th><th>Win rate</th><th>Net R</th><th></th></tr>"
            f"{body}</table>")


def ftmo_bars(c):
    """Optional progress bars. Expects S['ftmo_check'] = {passed, daily_loss:[used,limit], total_loss:[used,limit], profit_target:[got,target]}"""
    def bar(label, pct):
        return f"<div class='lbl' style='margin-bottom:6px'>{label}</div><div class='bar'><span style='width:{max(0, min(pct, 100)):.0f}%'></span></div>"

    out = ""
    if "passed" in c:
        out += f"<p style='margin:0 0 16px'><span class='{'pill' if c['passed'] else 'warn'}'>{'Passed' if c['passed'] else 'Failed'}</span></p>"
    if c.get("daily_loss"):
        u, lim = c["daily_loss"]
        out += bar(f"Max daily loss: {u:g}% of {lim:g}% limit", u / lim * 100)
    if c.get("total_loss"):
        u, lim = c["total_loss"]
        out += bar(f"Max total loss: {u:g}% of {lim:g}% limit", u / lim * 100)
    if c.get("profit_target"):
        g, tgt = c["profit_target"]
        out += bar(f"Profit target {tgt:g}%: {'reached' if g >= tgt else f'{g:g}% so far'}", g / tgt * 100)
    return out


# ---------- page ------------------------------------------------------------
sample_pill = "<span class='warn'>Sample numbers only</span>" if m.get("sample") else ""
period = f"Test period: {esc(m['period_from'])} to {esc(m['period_to'])} · Updated: {esc(m['generated'])}"

p = ["<div class='pd'>"]

# FTMO row for 0.5% risk (headline) and helper
def ftmo_row(label):
    for r in S.get("ftmo") or []:
        if str(r.get("Risk per trade")).strip() == label:
            return r
    return None


f05 = ftmo_row("0.5%")
f05_rate = f05.get("Success rate") if f05 else None
med = k.get("median_hold_days")
p90 = k.get("p90_hold_days")
fdd = k.get("max_float_dd_r", k.get("max_dd_r"))
fdd_note = "worst floating drawdown" if "max_float_dd_r" in k else "closed trades"

# header
p.append("<div style='display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:flex-end'><div>"
         "<div class='lbl' style='margin:0 0 6px'>Public backtest summary</div>"
         f"<div class='title'>{esc(PRODUCT_NAME)}</div>"
         "<div class='h2' style='margin:10px 0 0;font-size:22px'>See exactly how it behaves before you risk a dollar.</div>"
         "<div class='hero'>Every trade, every drawdown and every FTMO challenge attempt, replayed from real Pine logs, "
         "with floating risk included. No cherry-picking.</div>"
         f"<div class='sub' style='margin:10px 0 0'>{period}</div></div>{sample_pill}</div>")

# KPI cards
cards = (kpi_card("Trades", f"{k['trades']:,}", note=f"{k['pairs']} pairs" if k.get("pairs") else "")
         + kpi_card("Net R", num(k["net_r"], "+,.1f"), sign_cls(k["net_r"]), "closed trades")
         + kpi_card("Profit factor", num(k["profit_factor"], ".2f"), note="gross win / gross loss")
         + kpi_card("Win rate", num(k["win_rate"], ".1f", "%"), note="TP vs SL")
         + kpi_card("Expectancy", num(k["expectancy_r"], "+.3f", " R"), sign_cls(k["expectancy_r"]), "per trade")
         + kpi_card("Avg holding time", num(k["avg_hold_days"], ".1f", " d"), note=f"median {med:.1f} d" if med is not None else "")
         + kpi_card("Max floating DD", dd(fdd).replace("R", " R"), "neg", fdd_note))
if f05_rate is not None:
    cards += kpi_card("FTMO success rate", f"{f05_rate:g}%", "pos", "FTMO @ 0.5% risk / trade")
p.append("<div class='grid' style='grid-template-columns:repeat(auto-fit,minmax(170px,1fr))'>" + cards + "</div>")

# equity curve
svg = equity_svg(S["equity"]["x"], S["equity"]["y"], m.get("oos_start"))
p.append("<div class='card'><div class='h2'>Equity curve</div>"
         "<div class='sub'>Weekly points, in R. Individual trades are not shown.</div>" + svg + "</div>")

# monthly heatmap
p.append("<div class='card'><div class='h2'>Monthly returns</div>"
         "<div class='sub'>Net R per month. Teal is positive, orange is negative.</div>"
         "<div style='overflow-x:auto'>" + heatmap(S["monthly"], S["yearly"]) + "</div></div>")

# IS/OOS + prop-firm check
ftmo_html = ""
if S.get("ftmo") or S.get("ftmo_check"):
    rules = esc(m.get("ftmo_rules", "Standard challenge rules"))
    ftmo_html = ("<div class='card'><div class='h2'>FTMO challenge simulator</div>"
                 f"<div class='sub'>Every possible start date, replayed through your real rules. {rules}. Floating equity counted.</div>"
                 + (ftmo_bars(S["ftmo_check"]) if S.get("ftmo_check") else "")
                 + (f"<div style='overflow-x:auto'>{ftmo_table(S['ftmo'])}</div>" if S.get("ftmo") else "")
                 + "</div>")
p.append("<div class='grid' style='grid-template-columns:repeat(auto-fit,minmax(320px,1fr))'>"
         "<div class='card'><div class='h2'>In-sample vs out-of-sample</div>"
         "<div class='sub'>Shows whether the results hold on data not used to build the model.</div>"
         f"<div style='overflow-x:auto'>{is_oos_table()}</div></div>" + ftmo_html + "</div>")

# by pair
p.append("<div class='card'><div class='h2'>Results by pair</div>"
         "<div class='sub'>Totals only. Pairs with few trades are marked as low sample.</div>"
         f"<div style='overflow-x:auto'>{pairs_table()}</div></div>")

# how it works
hold_line = (f"Trades are held for days (average {k['avg_hold_days']:.1f}"
             + (f", median {med:.1f}" if med is not None else "")
             + (f"; 9 in 10 trades close within {p90:.1f} days" if p90 is not None else "")
             + "), so a few minutes of your day is enough.")
p.append(f"<div class='card'><div class='h2'>How {esc(PRODUCT_NAME)} works</div>"
         "<div class='about'>A liquidity-sweep + break-of-structure model that enters with a pending limit order.</div>"
         "<div class='step'><b>1. Liquidity sweep</b> - price takes out a swing high (for sells) or a swing low (for buys): "
         "the stops resting beyond it are cleared.</div>"
         "<div class='step'><b>2. Break of structure (BOS)</b> - within a limited number of candles price closes back beyond "
         "the last opposite swing, confirming the sweep was rejected.</div>"
         "<div class='step'><b>3. Fibonacci limit order</b> - a fib is drawn from the sweep extreme to the BOS point and a "
         "limit order is placed between 0.70 and 0.85.</div>"
         "<div class='step'><b>4. Fixed risk and reward from the first second</b> - stop-loss at fib 1 (the sweep extreme), "
         "take-profit at fib 0. Every trade's risk (1R) and target are known before the order is even filled.</div></div>")

p.append("<div class='card'><div class='h2'>Built for people with a job, and for any time zone</div><ul class='pts'>"
         "<li><b>Place it once, then walk away.</b> Entry, stop and target are fixed limit orders: no chart watching, "
         "no manual entries, no reacting to news spikes.</li>"
         f"<li><b>Swing trades, not scalps.</b> {esc(hold_line)}</li>"
         "<li><b>Not tied to a trading session.</b> Orders fill whenever price reaches the level, day or night, so the "
         "9-to-5 trader and the trader in another time zone get the same trades.</li>"
         "<li><b>Alerts included.</b> The indicator sends alerts for a new setup, a fill, take-profit and stop-loss.</li>"
         "</ul></div>")

# CTA
p.append("<div class='card' style='display:flex;flex-wrap:wrap;gap:16px;justify-content:space-between;align-items:center'>"
         f"<div><div class='h2'>{esc(CTA_TITLE)}</div><div class='sub' style='margin:0'>{esc(CTA_TEXT)}</div></div>"
         f"<a class='btn' href='{esc(BUY_URL)}' target='_blank' rel='noopener'>{esc(CTA_BUTTON)}</a></div>")

# disclaimer
p.append("<div class='foot'>Educational purpose only, not financial advice. Hypothetical backtest results; past results "
         "do not guarantee future results. Spread, commission and slippage may differ in live trading. Losses happen and "
         "trading carries risk. This page shows summary statistics only; individual trades and exact indicator settings are "
         "not published. Not affiliated with FTMO or any other prop firm.</div>")
p.append("</div>")

# One single-line HTML string so Streamlit's markdown parser keeps it as a raw HTML block.
st.markdown(f"<style>{' '.join(CSS.split())}</style>" + "".join(p), unsafe_allow_html=True)
