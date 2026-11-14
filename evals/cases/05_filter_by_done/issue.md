# Filter the task list by status

The list page needs to show open and finished tasks in separate tabs.

- `GET /tasks?done=true` returns only finished tasks
- `GET /tasks?done=false` returns only open tasks
- Without the parameter, all tasks come back like today
- A value that is not a boolean, such as `done=maybe`, gives a 422
