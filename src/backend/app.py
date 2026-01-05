"""
Flask API for EduTech Personalized Study Plan Generator
Provides endpoints for task management and study plan generation
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from pydantic import BaseModel, Field, ValidationError
from typing import Optional
from datetime import datetime, timezone
from enum import Enum

from .data import (
    process_task as pt,
    read_tasks as rt,
    update_task_status,
    delete_task,
    store_score as st,
    get_tasks_by_status,
    get_overdue_tasks
)
from .planner import (
    DIFFICULTY_WEIGHT,
    PRIORITY_WEIGHT,
    time_weight,
    calculate_task_score,
    generate_study_plan,
    adjust_plan_for_missed_task,
    get_upcoming_tasks
)


class Priority(str, Enum):
    ONGOING = "Ongoing"
    COMPLETED = "Completed"
    PENDING = "Pending"


class TaskRequest(BaseModel):
    task_name: str
    scale_difficulty: int = Field(..., ge=1, le=5)  # Scale from 1 to 5
    priority: Priority
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timedue: Optional[datetime] = Field(default=None)


class TaskStatusUpdate(BaseModel):
    task_name: str
    new_status: Priority


class StudyPlanRequest(BaseModel):
    available_hours_per_day: float = Field(default=4.0, ge=0.5, le=24.0)
    study_session_duration: float = Field(default=1.0, ge=0.25, le=8.0)


app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "EduTech Study Planner API"}


@app.route("/post_task", methods=["POST"])
def post_task() -> dict:
    """
    Create a new task.
    
    Expected JSON body:
    {
        "task_name": "Study Calculus",
        "scale_difficulty": 4,
        "priority": "Pending",
        "timedue": "2026-01-15T10:00:00Z"
    }
    """
    try:
        data = request.get_json()
        task = TaskRequest(**data)
        result = pt(task.model_dump())
        return jsonify(result), 201
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/get_tasks", methods=["GET"])
def get_tasks() -> list:
    """Get all tasks."""
    try:
        tasks = rt()
        return jsonify(tasks), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/update_task_status", methods=["PUT"])
def update_task() -> dict:
    """
    Update the status of a task.
    
    Expected JSON body:
    {
        "task_name": "Study Calculus",
        "new_status": "Completed"
    }
    """
    try:
        data = request.get_json()
        update_req = TaskStatusUpdate(**data)
        result = update_task_status(update_req.task_name, update_req.new_status)
        
        if result.get("status") == "error":
            return jsonify(result), 404
        
        return jsonify(result), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/delete_task/<task_name>", methods=["DELETE"])
def delete_task_endpoint(task_name: str) -> dict:
    """Delete a task by name."""
    try:
        result = delete_task(task_name)
        
        if result.get("status") == "error":
            return jsonify(result), 404
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/score_tasks", methods=["GET"])
def score_tasks() -> dict:
    """
    Calculate priority scores for all tasks.
    Returns tasks sorted by priority score.
    """
    try:
        tasks = rt()
        scores = []
        
        for task in tasks:
            task_name = task.get("task_name")
            score = calculate_task_score(task)
            scores.append({
                "task_name": task_name,
                "score": round(score, 2),
                "difficulty": task.get("scale_difficulty"),
                "priority": task.get("priority"),
                "timedue": task.get("timedue")
            })
            
            # Store the score
            st(task_name, score)
        
        # Sort by score descending
        scores.sort(key=lambda x: x["score"], reverse=True)
        
        return jsonify({"scores": scores}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/generate_plan", methods=["POST"])
def generate_plan() -> dict:
    """
    Generate a personalized study plan based on all active tasks.
    
    Optional JSON body:
    {
        "available_hours_per_day": 4.0,
        "study_session_duration": 1.0
    }
    """
    try:
        data = request.get_json() or {}
        plan_request = StudyPlanRequest(**data)
        
        tasks = rt()
        plan = generate_study_plan(
            tasks,
            available_hours_per_day=plan_request.available_hours_per_day,
            study_session_duration=plan_request.study_session_duration
        )
        
        return jsonify(plan), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/mark_missed/<task_name>", methods=["POST"])
def mark_missed(task_name: str) -> dict:
    """
    Mark a task as missed and regenerate the study plan with adjusted priorities.
    """
    try:
        # Update task status to Ongoing (needs attention)
        update_result = update_task_status(task_name, "Ongoing")
        
        if update_result.get("status") == "error":
            return jsonify(update_result), 404
        
        # Generate new plan with adjusted priorities
        tasks = rt()
        plan = generate_study_plan(tasks)
        
        # Find and boost the missed task in the plan
        for scheduled_task in plan.get("schedule", []):
            if scheduled_task["task_name"] == task_name:
                scheduled_task["priority_score"] *= 1.5
                scheduled_task["note"] = "Priority increased due to missed session"
        
        # Re-sort by priority
        plan["schedule"].sort(key=lambda x: x["priority_score"], reverse=True)
        plan["adjustment_reason"] = f"Plan adjusted for missed task: {task_name}"
        
        return jsonify({
            "status": "adjusted",
            "missed_task": task_name,
            "updated_plan": plan
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/upcoming_tasks", methods=["GET"])
def upcoming_tasks() -> dict:
    """
    Get tasks that are due soon (within next 7 days by default).
    
    Query parameters:
    - days_ahead: Number of days to look ahead (default: 7)
    """
    try:
        days_ahead = request.args.get("days_ahead", default=7, type=int)
        tasks = rt()
        upcoming = get_upcoming_tasks(tasks, days_ahead)
        
        return jsonify({
            "days_ahead": days_ahead,
            "count": len(upcoming),
            "tasks": upcoming
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/overdue_tasks", methods=["GET"])
def overdue_tasks() -> dict:
    """Get all tasks that are past their due date."""
    try:
        overdue = get_overdue_tasks()
        return jsonify({
            "count": len(overdue),
            "tasks": overdue
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/tasks_by_status/<status>", methods=["GET"])
def tasks_by_status(status: str) -> dict:
    """Get all tasks with a specific status (Pending, Ongoing, Completed)."""
    try:
        if status not in ["Pending", "Ongoing", "Completed"]:
            return jsonify({
                "status": "error",
                "message": "Invalid status. Must be one of: Pending, Ongoing, Completed"
            }), 400
        
        tasks = get_tasks_by_status(status)
        return jsonify({
            "status": status,
            "count": len(tasks),
            "tasks": tasks
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/stats", methods=["GET"])
def stats() -> dict:
    """Get overall statistics about tasks and study progress."""
    try:
        tasks = rt()
        
        total_tasks = len(tasks)
        pending_tasks = len([t for t in tasks if t.get("priority") == "Pending"])
        ongoing_tasks = len([t for t in tasks if t.get("priority") == "Ongoing"])
        completed_tasks = len([t for t in tasks if t.get("priority") == "Completed"])
        overdue = get_overdue_tasks()
        
        # Calculate average difficulty
        difficulties = [int(t.get("scale_difficulty", 1)) for t in tasks]
        avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else 0
        
        return jsonify({
            "total_tasks": total_tasks,
            "pending": pending_tasks,
            "ongoing": ongoing_tasks,
            "completed": completed_tasks,
            "overdue": len(overdue),
            "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0,
            "average_difficulty": round(avg_difficulty, 1)
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
