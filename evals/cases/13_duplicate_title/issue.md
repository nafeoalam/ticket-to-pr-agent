# Stop duplicate open tasks

People keep adding the same task twice.

Creating a task whose title matches an open task should be rejected with a 409.
Upper and lower case should not matter when comparing. If the matching task is
already done, the new one is allowed.
