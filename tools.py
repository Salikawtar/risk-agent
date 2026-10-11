"""
Step 3: tools.py
The agent's "calculators". The language model never does math itself:
it asks for a tool, and the tool returns exact numbers from the data.

Each tool takes only a portfolio id. That is a guardrail:
the agent cannot pass other inputs or touch other data.
"""

import csv
from collections import defaultdict

# The firm's risk policy. One place, easy to change.
POLICY = {
    "max_single_stock_pct": 25.0,   # concentration: one stock above 25% of the portfolio
    "min_cash_years": 1.0,          # liquidity: cash must cover at least 1 year of withdrawals
    "max_drift_points": 10.0,       # drift: equity share within 10 points of the target
}
RISKS = ["concentration", "liquidity", "drift"]

_clients = {}
_holdings = defaultdict(list)


def reload_data():
    """Read the CSV files made by make_data.py."""
    _clients.clear()
    _holdings.clear()
    with open("portfolios.csv", newline="") as f:
        for row in csv.DictReader(f):
            _clients[row["portfolio_id"]] = {
                "target_equity_pct": float(row["target_equity_pct"]),
                "annual_withdrawals": float(row["annual_withdrawals"]),
            }
    with open("holdings.csv", newline="") as f:
        for row in csv.DictReader(f):
            _holdings[row["portfolio_id"]].append(
                {"ticker": row["ticker"], "asset_type": row["asset_type"], "value": float(row["value"])}
            )


def _total(pid):
    return sum(h["value"] for h in _holdings[pid])


def list_portfolios():
    if not _clients:
        reload_data()
    return sorted(_clients)


# ---------- the four tools the agent can call ----------

def list_holdings(pid):
    """Everything the client owns, with each holding's share of the portfolio."""
    total = _total(pid)
    return {
        "portfolio_value": round(total, 2),
        "holdings": [
            {"ticker": h["ticker"], "type": h["asset_type"], "pct": round(100 * h["value"] / total, 1)}
            for h in sorted(_holdings[pid], key=lambda h: -h["value"])
        ],
    }


def check_concentration(pid):
    """The largest single stock and its share of the portfolio."""
    total = _total(pid)
    stocks = [h for h in _holdings[pid] if h["asset_type"] == "stock"]
    top = max(stocks, key=lambda h: h["value"])
    return {
        "largest_stock": top["ticker"],
        "largest_stock_pct": round(100 * top["value"] / total, 1),
        "policy_limit_pct": POLICY["max_single_stock_pct"],
    }


def check_liquidity(pid):
    """How many years of planned withdrawals the cash can cover."""
    cash = sum(h["value"] for h in _holdings[pid] if h["asset_type"] == "cash")
    withdrawals = _clients[pid]["annual_withdrawals"]
    return {
        "cash": round(cash, 2),
        "annual_withdrawals": round(withdrawals, 2),
        "years_covered": round(cash / withdrawals, 2),
        "policy_minimum_years": POLICY["min_cash_years"],
    }


def check_drift(pid):
    """How far the equity share is from the client's target."""
    total = _total(pid)
    equity = sum(h["value"] for h in _holdings[pid] if h["asset_type"] == "stock")
    actual = 100 * equity / total
    target = _clients[pid]["target_equity_pct"]
    return {
        "target_equity_pct": target,
        "actual_equity_pct": round(actual, 1),
        "drift_points": round(abs(actual - target), 1),
        "policy_limit_points": POLICY["max_drift_points"],
    }


TOOLS = {
    "list_holdings": list_holdings,
    "check_concentration": check_concentration,
    "check_liquidity": check_liquidity,
    "check_drift": check_drift,
}


# ---------- plain rules, used for the answer key and the baseline ----------

def rule_breach(pid, risk):
    if risk == "concentration":
        r = check_concentration(pid)
        return r["largest_stock_pct"] > r["policy_limit_pct"]
    if risk == "liquidity":
        r = check_liquidity(pid)
        return r["years_covered"] < r["policy_minimum_years"]
    if risk == "drift":
        r = check_drift(pid)
        return r["drift_points"] > r["policy_limit_points"]
    raise ValueError(risk)


if __name__ == "__main__":
    # Quick check: run this file to see the tools on one portfolio
    reload_data()
    for name, fn in TOOLS.items():
        print(name, "->", fn("P01"))
