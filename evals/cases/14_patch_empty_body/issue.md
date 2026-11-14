# PATCH with nothing to change should be an error

`PATCH /tasks/{id}` with an empty JSON object returns 200 today, which hides bugs
in the front end. It should return a 400 with the detail `No fields to update`.

A missing task should still be a 404.
