# Mini Portfolio Risk Investigator

A small AI agent that investigates made-up client portfolios for three risks
(one stock too large, not enough cash for withdrawals, equity far from target).

## How it works
1. `make_data.py` creates 30 synthetic portfolios with risks planted on purpose, plus an answer key.
2. `tools.py` holds the calculators. The model never does math; it asks for a tool.
3. `agent.py` runs the loop: the model picks a tool, Python runs it, the model sees the numbers, and so on until it finishes. A second "critic" call tries to disprove the findings.
4. `evaluate.py` scores the agent against the answer key and against plain rules.

## Controls built in
- Only four allowed tools, each limited to the current portfolio
- A step limit (6) so the agent cannot loop forever
- Temperature 0 for consistent answers
- A critic that challenges every finding
- Every decision and tool result logged with a timestamp (`audit_log.jsonl`)
- Any flagged portfolio, critic change or unfinished case goes to human review

## Run
1. Copy `.env.example` to `.env` and add your Gemini key and model name.
2. Install the packages and run the four scripts in order:
```
pip install -r requirements.txt
python make_data.py
python agent.py
python evaluate.py
```
`agent.py` runs all 30 portfolios. Set `RUN_LIMIT = 5` in `agent.py` for a cheap test first.

## Result
On 30 synthetic portfolios the agent found every planted risk with no false alarms,
the same as a plain rules baseline. On simple threshold checks, rules are just as accurate
and cheaper; the point of the project is the agent loop, its controls and how to measure it.

All data is synthetic. No real clients or companies.

See `CONTROLS.md` for the controls, my results, and what a real institution would still need.
