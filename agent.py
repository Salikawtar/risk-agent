"""
Steps 4 and 5: agent.py
The agent investigates each portfolio in a loop:
  1. the model decides which tool to use next (or decides it is done)
  2. Python runs that tool and gives the numbers back
  3. repeat, up to MAX_STEPS
Then a second "critic" call tries to disprove the findings.
Every decision is written to audit_log.jsonl.

Output: results.csv (one row per portfolio) and audit_log.jsonl
"""

import csv
import json
import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from google import genai
from google.genai import types

import tools

# ---------- settings and guardrails ----------
RUN_LIMIT = None      # start with 5 portfolios to test cheaply; set to None for all 30
MAX_STEPS = 6      # the agent must finish within 6 steps
LOG_FILE = "audit_log.jsonl"

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.environ["AGENT_MODEL"]

P = tools.POLICY
INVESTIGATOR_PROMPT = f"""You are a careful portfolio risk investigator at a wealth management firm.
You investigate ONE client portfolio at a time and look for three risk types:
- concentration: a single stock is more than {P['max_single_stock_pct']}% of the portfolio
- liquidity: cash covers less than {P['min_cash_years']} year of the client's planned withdrawals
- drift: the equity share is more than {P['max_drift_points']} percentage points away from the client's target

You cannot see the data. You must use tools. Never calculate numbers yourself; use the numbers the tools return.
Tools (each one works on the current portfolio, you do not pass any input):
- list_holdings: everything the client owns, with each holding's share in %
- check_concentration: the largest single stock and its share in %
- check_liquidity: cash, yearly withdrawals and how many years the cash covers
- check_drift: target equity %, actual equity % and the gap in points

Reply with JSON only, in one of these two forms:
{{"thought": "one short sentence", "action": "<tool name>"}}
{{"thought": "one short sentence", "action": "finish", "risks": ["concentration", "liquidity", "drift"],
  "evidence": {{"<risk>": "the numbers from the tools that show it"}},
  "summary": "two plain sentences an advisor can read"}}
Report a risk only if a tool result shows the limit is broken. Use an empty list if there is no risk.
Do not call the same tool twice."""

CRITIC_PROMPT = f"""You are a risk reviewer. Your job is to try to disprove an investigator's findings.
Policy limits: single stock above {P['max_single_stock_pct']}% = concentration;
cash below {P['min_cash_years']} year of withdrawals = liquidity;
equity more than {P['max_drift_points']} points from target = drift.
You receive the tool results and the risks the investigator reported.
For each reported risk, compare the numbers with the limit. Confirm it only if the numbers clearly break the limit.
Also list any risk the tool results clearly show but the investigator missed.
Reply with JSON only:
{{"confirmed": ["<risk>"], "rejected": [{{"risk": "<risk>", "reason": "..."}}], "missed": [{{"risk": "<risk>", "reason": "..."}}]}}"""


# ---------- helpers ----------

def log(event):
    """Audit trail: one line of JSON per event, with a timestamp."""
    event["time"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    return json.loads(text[: text.rfind("}") + 1])


def ask_llm(system_prompt, user_prompt):
    """One call to the model. Temperature 0 = as consistent as possible. Retries once."""
    for attempt in range(2):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            return parse_json(resp.text)
        except Exception as err:
            if attempt == 1:
                return {"action": "error", "thought": f"model call failed: {err}"}
            time.sleep(3)


def clean_risks(items):
    """Keep only valid risk names, written the same way."""
    names = [(i.get("risk") if isinstance(i, dict) else i) for i in (items or [])]
    return sorted({str(n).strip().lower() for n in names if str(n).strip().lower() in tools.RISKS})


# ---------- the agent loop ----------

def investigate(pid):
    history = []
    for step in range(1, MAX_STEPS + 1):
        user_prompt = (f"Portfolio: {pid}\nSteps so far:\n{json.dumps(history, indent=1)}\n"
                       "What is your next action? Reply with JSON only.")
        decision = ask_llm(INVESTIGATOR_PROMPT, user_prompt)
        action = decision.get("action")
        log({"portfolio": pid, "step": step, "type": "decision", "content": decision})

        if action == "finish":
            return decision, history, step, True
        if action == "error":
            return {"risks": [], "summary": decision["thought"]}, history, step, False

        # Guardrails: only known tools, no repeats
        if action not in tools.TOOLS:
            observation = {"error": f"'{action}' is not an allowed tool"}
        elif any(h["action"] == action for h in history):
            observation = {"error": f"{action} was already called; use the earlier result"}
        else:
            observation = tools.TOOLS[action](pid)

        history.append({"step": step, "action": action, "result": observation})
        log({"portfolio": pid, "step": step, "type": "tool", "tool": action, "content": observation})

    # Step limit reached: stop and send to a person
    return {"risks": [], "summary": "Stopped at the step limit without a conclusion."}, history, MAX_STEPS, False


def critique(pid, finding, history):
    user_prompt = (f"Portfolio: {pid}\nTool results:\n{json.dumps(history, indent=1)}\n"
                   f"Investigator's reported risks: {json.dumps(finding.get('risks', []))}\n"
                   f"Investigator's evidence: {json.dumps(finding.get('evidence', {}))}")
    review = ask_llm(CRITIC_PROMPT, user_prompt)
    log({"portfolio": pid, "type": "critic", "content": review})
    return review


def main():
    tools.reload_data()
    portfolios = tools.list_portfolios()[:RUN_LIMIT]
    rows = []
    for pid in portfolios:
        finding, history, steps, finished = investigate(pid)
        reported = clean_risks(finding.get("risks"))
        review = critique(pid, finding, history)
        final = sorted(set(clean_risks(review.get("confirmed"))) | set(clean_risks(review.get("missed"))))
        changed = final != reported
        rows.append({
            "portfolio_id": pid,
            "agent_risks": ";".join(reported),
            "final_risks": ";".join(final),
            "critic_changed": int(changed),
            "steps_used": steps,
            "needs_human_review": int(bool(final) or changed or not finished),
            "summary": finding.get("summary", ""),
        })
        print(f"{pid}: agent={reported or '-'}  after critic={final or '-'}  steps={steps}")

    with open("results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"\nDone. {len(rows)} portfolios -> results.csv, every step -> {LOG_FILE}")


if __name__ == "__main__":
    main()
