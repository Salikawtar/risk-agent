"""
Step 7: evaluate.py
Compares the agent with the answer key (the risks we planted)
and with plain rules (the "baseline").

For each risk type it reports:
  precision = when the agent says "risk", how often is it right?
  recall    = of the real risks, how many did the agent find?
  false alarms = risks flagged on portfolios that do not have them
"""

import csv

import tools


def load_answer_key():
    with open("answer_key.csv", newline="") as f:
        return {r["portfolio_id"]: {k for k in tools.RISKS if r[k] == "1"} for r in csv.DictReader(f)}


def load_results(column):
    with open("results.csv", newline="", encoding="utf-8") as f:
        return {r["portfolio_id"]: set(filter(None, r[column].split(";"))) for r in csv.DictReader(f)}


def score(predicted, truth, label):
    print(f"\n{label}")
    print(f"{'risk':<14}{'found':>6}{'missed':>8}{'false alarms':>14}{'precision':>11}{'recall':>8}")
    total_fp = 0
    for risk in tools.RISKS:
        tp = sum(1 for p in predicted if risk in predicted[p] and risk in truth[p])
        fp = sum(1 for p in predicted if risk in predicted[p] and risk not in truth[p])
        fn = sum(1 for p in predicted if risk not in predicted[p] and risk in truth[p])
        total_fp += fp
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        print(f"{risk:<14}{tp:>6}{fn:>8}{fp:>14}{precision:>11.2f}{recall:>8.2f}")
    exact = sum(1 for p in predicted if predicted[p] == truth[p])
    print(f"Portfolios fully correct: {exact} of {len(predicted)}   Total false alarms: {total_fp}")


def main():
    tools.reload_data()
    truth = load_answer_key()
    agent_raw = load_results("agent_risks")
    agent_final = load_results("final_risks")
    tested = sorted(agent_final)
    truth = {p: truth[p] for p in tested}
    rules = {p: {r for r in tools.RISKS if tools.rule_breach(p, r)} for p in tested}

    score(agent_raw, truth, "AGENT, before the critic")
    score(agent_final, truth, "AGENT, after the critic")
    score(rules, truth, "RULES BASELINE")

    with open("results.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    steps = sum(int(r["steps_used"]) for r in rows) / len(rows)
    changed = sum(int(r["critic_changed"]) for r in rows)
    review = sum(int(r["needs_human_review"]) for r in rows)
    print(f"\nAverage steps per portfolio: {steps:.1f}")
    print(f"Critic changed the answer on {changed} portfolio(s)")
    print(f"Sent to human review: {review} of {len(rows)}")


if __name__ == "__main__":
    main()
