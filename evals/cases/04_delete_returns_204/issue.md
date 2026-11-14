# DELETE should return 204

Our API guide says a successful delete returns `204 No Content` with an empty body.
Right now `DELETE /tasks/{id}` returns 200 with `{"ok": true}`.

Deleting a task that does not exist should still be a 404.
