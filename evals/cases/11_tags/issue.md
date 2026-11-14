# Tags for tasks

- A task can be created with an optional `tags` list of strings. The default is an empty list
- Tags are saved in lower case, with spaces around them removed
- Empty tags and repeated tags are dropped. The order of first appearance is kept
- `GET /tasks?tag=work` returns only the tasks that have that tag. Case does not matter in the query
