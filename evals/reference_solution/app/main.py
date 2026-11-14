from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Response

from . import __version__, store
from .models import Task, TaskCreate, TaskUpdate

app = FastAPI(title="Task Tracker")

NOT_FOUND = "Task not found"


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/stats")
def stats():
    tasks = store.list_all()
    done = sum(1 for task in tasks if task.done)
    return {"total": len(tasks), "done": done, "open": len(tasks) - done}


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(body: TaskCreate):
    wanted = body.title.lower()
    if any(not t.done and t.title.lower() == wanted for t in store.list_all()):
        raise HTTPException(status_code=409, detail="An open task with this title already exists")
    return store.create(body)


@app.get("/tasks", response_model=List[Task])
def list_tasks(
    done: Optional[bool] = None,
    q: Optional[str] = None,
    tag: Optional[str] = None,
    sort: Literal["created_at", "title"] = "created_at",
    order: Literal["asc", "desc"] = "asc",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    tasks = store.list_all()
    if done is not None:
        tasks = [t for t in tasks if t.done == done]
    if q:
        needle = q.lower()
        tasks = [t for t in tasks if needle in t.title.lower() or needle in t.description.lower()]
    if tag:
        tasks = [t for t in tasks if tag.strip().lower() in t.tags]
    if sort == "title":
        tasks = sorted(tasks, key=lambda t: t.title.lower())
    if order == "desc":
        tasks = list(reversed(tasks))
    return tasks[offset : offset + limit]


@app.delete("/tasks")
def delete_done_tasks(done: Optional[bool] = None):
    if done is not True:
        raise HTTPException(status_code=400, detail="Only done=true is supported")
    return {"deleted": store.delete_done()}


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return task


@app.patch("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, body: TaskUpdate):
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.done is not None:
        task.done = body.done
        if not body.done:
            task.completed_at = None
    return store.save(task)


@app.post("/tasks/{task_id}/complete", response_model=Task)
def complete_task(task_id: int):
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if not task.done:
        task.done = True
        task.completed_at = datetime.now(timezone.utc)
    return store.save(task)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    if not store.delete(task_id):
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return Response(status_code=204)
