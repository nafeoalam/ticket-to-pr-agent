# Reference solution

A hand written version of the sample app with every eval ticket solved.

It exists for one reason: to prove the hidden tests are fair. `python -m evals.check_cases`
checks that each hidden test **fails** on the starting app and **passes** on this one.

The agent never sees this folder. It only ever gets a copy of `sample_app/`.
