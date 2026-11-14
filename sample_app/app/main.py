from typing import List

from fastapi import FastAPI, HTTPException

from . import store
from .models import Task, TaskCreate, TaskUpdate

app = FastAPI(title="Task Tracker")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(body: TaskCreate):
    return store.create(body)


@app.get("/tasks", response_model=List[Task])
def list_tasks():
    return store.list_all()


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not fonud")
    return task


@app.patch("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, body: TaskUpdate):
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not fonud")
    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.done:
        task.done = body.done
    return store.save(task)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    if not store.delete(task_id):
        raise HTTPException(status_code=404, detail="Task not fonud")
    return {"ok": True}
