# TAO Working Method Rule

All agents in this repository must follow TAO (Thought, Action, Observation) when working on non-trivial tasks.

## Method

- `Thought`: Before each action, state in one sentence what you are about to do and why.
- `Action`: Take exactly one focused action such as reading a file, writing code, or running a command.
- `Observation`: After the action, state what you learned or what changed. If the result is unexpected, adjust the plan before the next step.

Repeat until the task is complete.

## Rules

- Do not batch multiple actions without an observation in between when the outcome of one affects the next.
- Do not skip the Thought step to save tokens; it prevents reasoning errors.
- If an action fails, the Observation must include the root cause, not just the error message.
- When a task is done, state the final observation clearly so the user can verify the outcome without re-reading code.

## Example

```text
Thought: I need to read freqtrade_executor.py before modifying it to avoid overwriting existing logic.
Action: [Read lib/strategy/execution/freqtrade_executor.py]
Observation: The file uses REPO_ROOT correctly but STRATEGY_PATH is hardcoded. I will fix line 24.

Thought: I will replace the hardcoded STRATEGY_PATH with a repo-relative path.
Action: [Edit lib/strategy/execution/freqtrade_executor.py line 24]
Observation: Edit applied. STRATEGY_PATH now resolves from REPO_ROOT dynamically.
```
