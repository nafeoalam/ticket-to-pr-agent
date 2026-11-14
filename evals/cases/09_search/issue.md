# Search tasks by text

`GET /tasks?q=report` should return the tasks whose title or description contains
that text. Upper and lower case should not matter. Without `q`, all tasks come back.
