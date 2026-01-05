"""
Data Layer - CSV-based storage for tasks and study plans
"""

import csv
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# Use relative paths from the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "db"
TASKS_FILE = DB_DIR / "tasks.csv"
SCORES_FILE = DB_DIR / "scores.csv"

# Ensure database directory exists
DB_DIR.mkdir(exist_ok=True)

# CSV headers
TASK_HEADERS = ["task_name", "scale_difficulty", "priority", "createdAt", "timedue"]
SCORE_HEADERS = ["task_name", "score", "calculated_at"]


def initialize_csv_files():
    """Initialize CSV files with headers if they don't exist."""
    if not TASKS_FILE.exists():
        with open(TASKS_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(TASK_HEADERS)
    
    if not SCORES_FILE.exists():
        with open(SCORES_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(SCORE_HEADERS)


def process_task(data: dict) -> dict:
    """
    Add a new task to the database.
    
    Args:
        data: Dictionary containing task information
        
    Returns:
        Status dictionary
    """
    initialize_csv_files()
    
    with open(TASKS_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            data.get("task_name"),
            data.get("scale_difficulty"),
            data.get("priority"),
            data.get("createdAt"),
            data.get("timedue")
        ])

    return {"status": "saved", "task_name": data.get("task_name")}


def read_tasks() -> List[Dict[str, Any]]:
    """
    Read all tasks from the database.
    
    Returns:
        List of task dictionaries
    """
    initialize_csv_files()
    
    tasks = []
    try:
        with open(TASKS_FILE, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                tasks.append(row)
    except FileNotFoundError:
        return []
    
    return tasks


def update_task_status(task_name: str, new_status: str) -> dict:
    """
    Update the status of a specific task.
    
    Args:
        task_name: Name of the task to update
        new_status: New priority status (Pending, Ongoing, Completed)
        
    Returns:
        Status dictionary
    """
    initialize_csv_files()
    
    tasks = read_tasks()
    updated = False
    
    for task in tasks:
        if task.get("task_name") == task_name:
            task["priority"] = new_status
            updated = True
            break
    
    if not updated:
        return {"status": "error", "message": "Task not found"}
    
    # Rewrite the entire file
    with open(TASKS_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=TASK_HEADERS)
        writer.writeheader()
        writer.writerows(tasks)
    
    return {"status": "updated", "task_name": task_name, "new_status": new_status}


def delete_task(task_name: str) -> dict:
    """
    Delete a task from the database.
    
    Args:
        task_name: Name of the task to delete
        
    Returns:
        Status dictionary
    """
    initialize_csv_files()
    
    tasks = read_tasks()
    original_count = len(tasks)
    tasks = [t for t in tasks if t.get("task_name") != task_name]
    
    if len(tasks) == original_count:
        return {"status": "error", "message": "Task not found"}
    
    # Rewrite the file
    with open(TASKS_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=TASK_HEADERS)
        writer.writeheader()
        writer.writerows(tasks)
    
    return {"status": "deleted", "task_name": task_name}


def store_score(task_name: str, score: float, calculated_at: Optional[str] = None) -> dict:
    """
    Store a calculated priority score for a task.
    
    Args:
        task_name: Name of the task
        score: Calculated priority score
        calculated_at: Timestamp of calculation
        
    Returns:
        Status dictionary
    """
    initialize_csv_files()
    
    from datetime import datetime, timezone
    if calculated_at is None:
        calculated_at = datetime.now(timezone.utc).isoformat()
    
    with open(SCORES_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([task_name, score, calculated_at])
    
    return {"status": "score saved", "task_name": task_name, "score": score}


def get_tasks_by_status(status: str) -> List[Dict[str, Any]]:
    """
    Get all tasks with a specific status.
    
    Args:
        status: Priority status to filter by
        
    Returns:
        List of matching tasks
    """
    tasks = read_tasks()
    return [t for t in tasks if t.get("priority") == status]


def get_overdue_tasks() -> List[Dict[str, Any]]:
    """
    Get all tasks that are past their due date.
    
    Returns:
        List of overdue tasks
    """
    from datetime import datetime, timezone
    
    tasks = read_tasks()
    now = datetime.now(timezone.utc)
    overdue = []
    
    for task in tasks:
        if task.get("timedue") and task.get("priority") != "Completed":
            try:
                due_date = datetime.fromisoformat(str(task["timedue"]).replace('Z', '+00:00'))
                if due_date.tzinfo is None:
                    due_date = due_date.replace(tzinfo=timezone.utc)
                
                if due_date < now:
                    overdue.append(task)
            except (ValueError, AttributeError):
                continue
    
    return overdue