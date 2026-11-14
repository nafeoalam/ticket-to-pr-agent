# Sort the task list

- `GET /tasks?sort=title` sorts by title, ignoring upper and lower case
- `sort=created_at` is the default and keeps the order tasks were created in
- `order=desc` reverses the result. The default is `asc`
- An unknown `sort` or `order` value gives a 422
