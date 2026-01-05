"""
Data Layer - SQLite-based storage for tasks and study plans
"""

import sqlite3
import threading
from typing import List, Dict, Any, Optional
from pathlib import Path

# Use relative paths from the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "db"
DB_FILE = DB_DIR / "studyplan.db"
# Track initialization for thread-safe setup
_db_initialized = False
_init_lock = threading.Lock()

# Column headers for consistent responses
TASK_HEADERS = ["task_name", "scale_difficulty", "priority", "createdAt", "timedue"]
SCORE_HEADERS = ["task_name", "score", "calculated_at"]


def initialize_db():
    """Initialize SQLite database and tables if they don't exist."""
    global _db_initialized
    with _init_lock:
        if _db_initialized and DB_FILE.exists():
            return

        DB_DIR.mkdir(exist_ok=True)
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_name TEXT PRIMARY KEY,
                    scale_difficulty TEXT,
                    priority TEXT,
                    createdAt TEXT,
                    timedue TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT,
                    score REAL,
                    calculated_at TEXT,
                    FOREIGN KEY (task_name) REFERENCES tasks(task_name)
                )
                """
            )
        _db_initialized = True


def _get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row factory configured."""
    if not _db_initialized or not DB_FILE.exists():
        initialize_db()
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _isoformat(value: Any) -> Optional[str]:
    """Convert datetime-like objects to ISO strings."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (AttributeError, TypeError, ValueError):
            return str(value)
    return str(value)


def _normalize_value(value: Any) -> Any:
    """Extract value from enum-like objects."""
    return getattr(value, "value", value)


def process_task(data: dict) -> dict:
    """
    Add a new task to the database.
    
    Args:
        data: Dictionary containing task information
        
    Returns:
        Status dictionary
    """
    try:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tasks (task_name, scale_difficulty, priority, createdAt, timedue)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    data.get("task_name"),
                    str(_normalize_value(data.get("scale_difficulty"))),
                    str(_normalize_value(data.get("priority"))),
                    _isoformat(data.get("createdAt")),
                    _isoformat(data.get("timedue")),
                ),
            )
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Task already exists"}

    return {"status": "saved", "task_name": data.get("task_name")}


def read_tasks() -> List[Dict[str, Any]]:
    """
    Read all tasks from the database.
    
    Returns:
        List of task dictionaries
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT task_name, scale_difficulty, priority, createdAt, timedue FROM tasks"
        )
        rows = cursor.fetchall()
    return [dict(row) for row in rows]


def update_task_status(task_name: str, new_status: str) -> dict:
    """
    Update the status of a specific task.
    
    Args:
        task_name: Name of the task to update
        new_status: New priority status (Pending, Ongoing, Completed)
        
    Returns:
        Status dictionary
    """
    normalized_status = str(_normalize_value(new_status))
    with _get_connection() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET priority = ? WHERE task_name = ?",
            (normalized_status, task_name),
        )
        if cursor.rowcount == 0:
            return {"status": "error", "message": "Task not found"}
    return {"status": "updated", "task_name": task_name, "new_status": normalized_status}


def delete_task(task_name: str) -> dict:
    """
    Delete a task from the database.
    
    Args:
        task_name: Name of the task to delete
        
    Returns:
        Status dictionary
    """
    with _get_connection() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE task_name = ?", (task_name,))
        if cursor.rowcount == 0:
            return {"status": "error", "message": "Task not found"}
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
    from datetime import datetime, timezone
    if calculated_at is None:
        calculated_at = datetime.now(timezone.utc).isoformat()

    try:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scores (task_name, score, calculated_at)
                VALUES (?, ?, ?)
                """,
                (task_name, score, calculated_at),
            )
    except sqlite3.IntegrityError:
        return {
            "status": "error",
            "message": "Cannot store score due to a database constraint violation (likely a missing task)",
        }

    return {"status": "score saved", "task_name": task_name, "score": score}


def get_tasks_by_status(status: str) -> List[Dict[str, Any]]:
    """
    Get all tasks with a specific status.
    
    Args:
        status: Priority status to filter by
        
    Returns:
        List of matching tasks
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT task_name, scale_difficulty, priority, createdAt, timedue
            FROM tasks
            WHERE priority = ?
            """,
            (status,),
        )
        rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_overdue_tasks() -> List[Dict[str, Any]]:
    """
    Get all tasks that are past their due date.
    
    Returns:
        List of overdue tasks
    """
    from datetime import datetime, timezone

    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT task_name, scale_difficulty, priority, createdAt, timedue
            FROM tasks
            WHERE timedue IS NOT NULL
              AND priority != ?
            """,
            ("Completed",),
        )
        tasks = [dict(row) for row in cursor.fetchall()]

    now = datetime.now(timezone.utc)
    overdue = []

    for task in tasks:
        try:
            due_date = datetime.fromisoformat(str(task["timedue"]).replace("Z", "+00:00"))
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            if due_date < now:
                overdue.append(task)
        except (ValueError, AttributeError, TypeError):
            continue

    return overdue
