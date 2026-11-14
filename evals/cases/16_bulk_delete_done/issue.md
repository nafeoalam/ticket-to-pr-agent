# Clear finished tasks in one call

- `DELETE /tasks?done=true` deletes every finished task and returns 200 with `{"deleted": 2}`, using the real count
- `DELETE /tasks` without `done=true` returns a 400 and deletes nothing
- Deleting one task by id keeps working as before
