# Controls and limits

This file explains how the agent is kept under control, what each control protects against,
and what a real financial institution would still need before using something like it.

## Controls built into this prototype

| Control | Where in the code | What it protects against |
|---|---|---|
| Only 4 allowed tools, each limited to the current portfolio | `tools.py` (`TOOLS`), `agent.py` (`investigate`) | The agent doing things it should not, or reaching other data |
| The model never calculates; tools return exact numbers | `tools.py` | Invented or wrong numbers |
| Step limit of 6 | `agent.py` (`MAX_STEPS`) | Loops, runaway cost, no conclusion |
| Temperature 0 and a fixed JSON reply format | `agent.py` (`ask_llm`, prompts) | Inconsistent or unreadable answers |
| Critic step that tries to disprove each finding | `agent.py` (`critique`) | Confident but wrong findings |
| Audit log of every decision and tool result, with a timestamp | `agent.py` (`log`), `audit_log.jsonl` | Decisions nobody can explain afterwards |
| Human review rule: any risk, any critic change, or any unfinished case goes to a person | `agent.py` (`main`) | The agent closing cases on its own |
| Answer key and rules baseline | `make_data.py`, `evaluate.py` | Trusting the agent without evidence |

## Results from my run

Results from `python evaluate.py` on the full run:

- Portfolios tested: 30
- Portfolios fully correct: 30 of 30 (agent and rules baseline)
- False alarms before the critic: 0
- False alarms after the critic: 0
- Portfolios the critic changed: 0
- Average steps per portfolio: 4.0
- Sent to human review: 21 of 30 (every portfolio with a planted risk)

What I learned: on this simple data, plain rules are as accurate as the agent, because the risks
are defined by the same rules. An agent is only worth its cost where cases are messy, need an
explanation, or combine several factors. Measuring against rules is how you find out.

## What a real institution would still need

- Access controls and protection of real client data (this prototype uses synthetic data only)
- Independent model validation before use. In Canada, OSFI Guideline E-23 on model risk,
  which covers AI models, takes effect in May 2027.
- Monitoring over time, to catch the model behaving differently after an update
- A record of who reviewed and approved each flagged case
- Clear accountability: a named owner for the agent and for each policy limit

## Known limits of this prototype

- 30 synthetic portfolios with simple thresholds, not real or messy data
- Only three risk types, each defined by one rule
- One model, tested once; results may change with another model or another run
- The critic never had an error to catch, so its value is not shown by this run
