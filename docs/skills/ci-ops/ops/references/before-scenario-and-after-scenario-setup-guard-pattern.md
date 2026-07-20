---
name: before-scenario-and-after-scenario-setup-guard-pattern
description: "Deep dive: before_scenario and after_scenario setup guard pattern"
metadata:
  type: reference
  audience: agents
  maturity: stable
---
# Before Scenario And After Scenario Setup Guard Pattern

## before_scenario and after_scenario setup guard pattern

```python
def before_scenario(context, scenario) -> None:
    from tests.shared.quarantine import skip_quarantine
    if skip_quarantine(scenario):
        return
    if getattr(context, 'failed_setup', None):    # GUARD
        try:
            scenario.skip(reason=context.failed_setup)
        except TypeError:
            scenario.skip()
        return
    ...

def after_scenario(context, scenario) -> None:
    if getattr(context, 'failed_setup', None):    # GUARD
        return
    ...
    if hasattr(context, 'sandbox'):               # GUARD: sandbox may not exist
        context.sandbox.after_scenario(context, scenario)
```

**CRITICAL:** Use `getattr(context, 'failed_setup', None)` (truthiness check), NOT `hasattr()`. `TestSandbox.__init__` sets `context.failed_setup = None` on every run (even success), so `hasattr()` is always `True` and causes every scenario to skip.

Also use `scenario.skip()`, NOT `context.scenario.skip()` — `context.scenario` is not set yet at the guard point.

---
