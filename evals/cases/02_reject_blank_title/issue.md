# Tasks can be saved with an empty title

We have tasks in the list with no title at all, and some that are only spaces.

- Creating a task with a title that is empty or only spaces should be rejected with a 422.
- The same goes for renaming a task with PATCH.
- Titles should be saved without spaces at the start or the end.
