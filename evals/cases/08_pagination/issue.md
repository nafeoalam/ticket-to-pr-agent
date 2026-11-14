# Add paging to the task list

One customer has thousands of tasks and the list call is getting slow.

`GET /tasks` should take two new query parameters:

- `limit`: how many tasks to return. Default 50, lowest 1, highest 100
- `offset`: how many tasks to skip. Default 0, cannot be negative

Values outside those ranges give a 422.
