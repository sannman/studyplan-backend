from flask import Flask , jsonify , request
from flask_cors import CORS
from pydantic import BaseModel , Field
from typing import Optional
from datetime import datetime , timezone
from enum import Enum

class Priority(str , Enum):
    ONGOING = "Ongoing"
    COMPLETED = "Completed"
    PENDING = "Pending"

class TaskRequest(BaseModel):
    task_name: str
    scale_difficulty: int = Field(...,ge=1,le=5) # Scale from 1 to 5
    priority: Priority
    createdAt : datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timedue: Optional[datetime] = None

app = Flask(__name__)
CORS(app)


@app.route("/post_task", methods = ["POST"])
def post_task() -> dict:

    data = request.get_json()
    

    task = TaskRequest(**data)

    return task.model_dump()    



if __name__ == "__main__":
    app.run(debug = True)