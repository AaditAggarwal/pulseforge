# FAILURE_MODES

Every failure that was reproduced, understood, and fixed. A failure does not get an entry until it has
a regression test. The point of this file is that the same class of bug cannot happen twice silently.

## Status

No failures recorded yet. No code exists.

## Entry template

```
## FM-001: <short name>
Phase:        NN
Discovered:   YYYY-MM-DD, how
Reproduce:    exact steps and commands
Observed:     what actually happened, including exact error text
Expected:     what should have happened
Root cause:   the real one, not the symptom
Mitigation:   what was changed, with file and line
Regression:   the test that now fails if this returns
```
