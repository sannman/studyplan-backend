from flask import Flask , jsonify , request
from flask_cors import CORS
from pydantic import BaseModel , Field
from typing import Optional
from datetime import datetime , timezone
from enum import Enum
from .data import process_task as pt
from .data import read_tasks as rt
from .data import store_score as st
from .planner import difficulty_weight , priority_weight , time_weight

class Priority(str , Enum):
    ONGOING = "Ongoing"
    COMPLETED = "Completed"
    PENDING = "Pending"

class TaskRequest(BaseModel):
    task_name: str
    scale_difficulty: int = Field(...,ge=1,le=5) # Scale from 1 to 5
    priority: Priority
    createdAt : datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timedue: Optional[datetime] = None , Field(default_factory=lambda: datetime.now(timezone.utc))

app = Flask(__name__)
CORS(app)


@app.route("/post_task", methods = ["POST"])
def post_task() -> dict:

    data = request.get_json()
    task = TaskRequest(**data)
    result = pt(task.model_dump())
    return result


@app.route("/get_tasks", methods=["GET"])
def get_tasks() -> list[dict]:
    tasks = rt()
    return tasks

@app.route("/score_task")
def score_task() -> dict:
    task = rt()
    scores = []
    for t in task:
        task_name = t.get("task_name")
        difweight = difficulty_weight.get(int(t.get("difficulty" , 1)), 1)
        priweight = priority_weight.get(t.get("priority"), 1)
        timew = time_weight(datetime.fromisoformat(t["timedue"]) if t.get("timedue") else None)
        score = difweight * priweight * timew
        print(score)
        scores.append({"task_name": t.get("task_name"), "score": score})
        return {"scores": scores}
    






if __name__ == "__main__":
    app.run(debug = True)