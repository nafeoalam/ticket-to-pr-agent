# Add a "complete" action that records when a task was finished

- `POST /tasks/{id}/complete` marks the task as done and sets `completed_at` to the current UTC time
- Tasks show `completed_at` as `null` until they are completed
- Completing a task that is already done returns 200 and keeps the first `completed_at`
- A missing task gives a 404
