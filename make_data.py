"""
Step 2: make_data.py
Creates 30 made-up client portfolios. Some have risks planted on purpose,
so we know the right answer before the agent starts (the "answer key").

Run it once. It writes three files:
  portfolios.csv  - one row per client (target equity share, yearly withdrawals)
  holdings.csv    - what each client owns (stocks, bond fund, cash)
  answer_key.csv  - which risks we planted in each portfolio
"""

import csv
import math
import random

import tools  # we reuse the same policy limits and calculations

random.seed(42)  # same "random" data every time you run it

TICKERS = ["ALDR", "BRVO", "CEDR", "DLTA", "ELMX", "FJRD", "GRNT", "HRBR",
           "IRON", "JUNO", "KELP", "LYNX", "MAPL", "NRTH", "OTTR", "PINE",
           "QUIL", "RDGE", "SPRC", "TUND"]

# What we plant in each portfolio.
# c = concentration, l = liquidity, d = drift, b = borderline (close to a limit but safe)
PLAN = (
    ["c"] * 6 +          # P01-P06: one stock is too big
    ["l"] * 6 +          # P07-P12: not enough cash for withdrawals
    ["d"] * 6 +          # P13-P18: equity share far from target
    ["cl", "ld", "cd"] + # P19-P21: two risks at once
    ["b"] * 3 +          # P22-P24: close to the limits, but no risk
    [""] * 6             # P25-P30: clean
)


def build_portfolio(pid, plan):
    total = random.randint(200, 2000) * 1000          # portfolio value in dollars
    target = random.choice([40, 50, 60])              # target equity share (%)
    border = plan == "b"

    # 1. Equity share (drift risk = far from target)
    if "d" in plan:
        drift = random.uniform(15, 25)
        equity_pct = target + drift if target <= 50 else target - drift
    elif border:
        equity_pct = target + random.choice([-1, 1]) * random.uniform(7, 9)
    else:
        equity_pct = target + random.uniform(-5, 5)
    e = equity_pct / 100

    # 2. Cash versus planned withdrawals (liquidity risk = less than 1 year covered)
    withdrawals = total * random.uniform(0.02, 0.04)
    if "l" in plan:
        cash = withdrawals * random.uniform(0.3, 0.8)
    elif border:
        cash = withdrawals * random.uniform(1.1, 1.3)
    else:
        cash = withdrawals * random.uniform(1.5, 3.0)
    c = cash / total

    # 3. Largest single stock (concentration risk = more than 25%)
    if "c" in plan:
        top = random.uniform(0.32, min(0.48, e - 0.05))
    elif border:
        top = random.uniform(0.21, 0.24)
    else:
        top = random.uniform(0.06, 0.14)

    # Split the rest of the equity into smaller stocks, each smaller than the top one
    rest = e - top
    piece_max = min(top * 0.9, 0.15)
    n_rest = max(1, math.ceil(rest / piece_max))
    pieces = [rest / n_rest] * n_rest

    names = random.sample(TICKERS, n_rest + 1)
    holdings = [(pid, names[0], "stock", round(top * total, 2))]
    holdings += [(pid, names[i + 1], "stock", round(p * total, 2)) for i, p in enumerate(pieces)]
    bonds = total - sum(h[3] for h in holdings) - cash
    holdings.append((pid, "BOND_FUND", "bond", round(bonds, 2)))
    holdings.append((pid, "CASH", "cash", round(cash, 2)))

    client = (pid, target, round(withdrawals, 2))
    return client, holdings


def main():
    clients, all_holdings = [], []
    for i, plan in enumerate(PLAN, start=1):
        pid = f"P{i:02d}"
        client, holdings = build_portfolio(pid, plan)
        clients.append(client)
        all_holdings += holdings

    with open("portfolios.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["portfolio_id", "target_equity_pct", "annual_withdrawals"])
        w.writerows(clients)

    with open("holdings.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["portfolio_id", "ticker", "asset_type", "value"])
        w.writerows(all_holdings)

    # The answer key is calculated with the same rules the policy uses,
    # so it is the "truth" we test the agent against.
    tools.reload_data()
    with open("answer_key.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["portfolio_id", "concentration", "liquidity", "drift"])
        for (pid, _, _) in clients:
            w.writerow([pid] + [int(tools.rule_breach(pid, r)) for r in tools.RISKS])

    print(f"Created {len(clients)} portfolios and {len(all_holdings)} holdings.")
    print("Files written: portfolios.csv, holdings.csv, answer_key.csv")


if __name__ == "__main__":
    main()
