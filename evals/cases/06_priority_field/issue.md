# Add a priority to tasks

Users want to mark what matters most.

- A task has a `priority` that is one of `low`, `medium` or `high`
- It can be set when the task is created. If it is left out, it is `medium`
- Any other value is rejected with a 422
- Every response that returns a task includes the priority
