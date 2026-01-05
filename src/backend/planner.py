"""
Study Plan Generator - Core Planning Logic
Implements dynamic scheduling based on difficulty, priority, time, and exam proximity
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

# Difficulty weight mapping (1-5 scale)
difficulty_weight = {
    1: 1.0,   # Very Easy
    2: 1.5,   # Easy
    3: 2.0,   # Medium
    4: 2.5,   # Hard
    5: 3.0    # Very Hard
}

# Priority weight mapping
priority_weight = {
    "Pending": 1.0,
    "Ongoing": 2.0,
    "Completed": 0.0  # Completed tasks don't need scheduling
}


def time_weight(due_date: Optional[datetime]) -> float:
    """
    Calculate time-based urgency weight.
    Returns higher weight for tasks that are due sooner.
    
    Args:
        due_date: Optional datetime when task is due
        
    Returns:
        float: Weight multiplier based on urgency (1.0 to 5.0)
    """
    if due_date is None:
        return 1.0  # Default weight for tasks without due date
    
    now = datetime.now(timezone.utc)
    
    # If due_date is naive (no timezone), make it timezone-aware
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    
    time_remaining = due_date - now
    days_remaining = time_remaining.total_seconds() / (24 * 3600)
    
    # Urgency increases as deadline approaches
    if days_remaining <= 0:
        return 5.0  # Overdue - maximum urgency
    elif days_remaining <= 1:
        return 4.5  # Due within 24 hours
    elif days_remaining <= 3:
        return 3.5  # Due within 3 days
    elif days_remaining <= 7:
        return 2.5  # Due within a week
    elif days_remaining <= 14:
        return 1.5  # Due within 2 weeks
    else:
        return 1.0  # Due later


def calculate_task_score(task: Dict[str, Any]) -> float:
    """
    Calculate priority score for a task based on difficulty, priority, and time.
    
    Args:
        task: Dictionary containing task information
        
    Returns:
        float: Priority score for the task
    """
    difficulty = int(task.get("scale_difficulty", 1))
    priority = task.get("priority", "Pending")
    
    # Parse due date
    due_date = None
    if task.get("timedue"):
        try:
            due_date = datetime.fromisoformat(str(task["timedue"]).replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            due_date = None
    
    # Calculate weights
    diff_weight = difficulty_weight.get(difficulty, 1.0)
    pri_weight = priority_weight.get(priority, 1.0)
    time_w = time_weight(due_date)
    
    # Combined score
    score = diff_weight * pri_weight * time_w
    
    return score


def generate_study_plan(
    tasks: List[Dict[str, Any]], 
    available_hours_per_day: float = 4.0,
    study_session_duration: float = 1.0
) -> Dict[str, Any]:
    """
    Generate a personalized study plan based on task priorities and available time.
    
    Args:
        tasks: List of task dictionaries
        available_hours_per_day: Hours available for study per day
        study_session_duration: Length of each study session in hours
        
    Returns:
        Dictionary containing the generated study plan
    """
    # Filter out completed tasks
    active_tasks = [
        task for task in tasks 
        if task.get("priority") != "Completed"
    ]
    
    # Calculate scores for all active tasks
    scored_tasks = []
    for task in active_tasks:
        score = calculate_task_score(task)
        task_with_score = task.copy()
        task_with_score["priority_score"] = score
        scored_tasks.append(task_with_score)
    
    # Sort tasks by priority score (highest first)
    scored_tasks.sort(key=lambda x: x["priority_score"], reverse=True)
    
    # Generate schedule
    schedule = []
    current_date = datetime.now(timezone.utc)
    sessions_per_day = int(available_hours_per_day / study_session_duration)
    
    for task in scored_tasks:
        # Calculate estimated sessions needed based on difficulty
        difficulty = int(task.get("scale_difficulty", 1))
        estimated_sessions = difficulty  # Higher difficulty = more sessions needed
        
        # Allocate sessions
        task_sessions = []
        for session_num in range(estimated_sessions):
            session_date = current_date + timedelta(
                days=(len(schedule) + session_num) // sessions_per_day
            )
            session_time_slot = (len(schedule) + session_num) % sessions_per_day
            
            task_sessions.append({
                "session_number": session_num + 1,
                "date": session_date.isoformat(),
                "time_slot": session_time_slot + 1,
                "duration_hours": study_session_duration
            })
        
        schedule.append({
            "task_name": task.get("task_name"),
            "priority_score": task["priority_score"],
            "difficulty": task.get("scale_difficulty"),
            "priority_status": task.get("priority"),
            "due_date": task.get("timedue"),
            "sessions": task_sessions
        })
    
    # Calculate plan statistics
    total_sessions = sum(len(item["sessions"]) for item in schedule)
    total_study_hours = total_sessions * study_session_duration
    estimated_completion_days = (total_sessions / sessions_per_day) if sessions_per_day > 0 else 0
    
    return {
        "plan_generated_at": datetime.now(timezone.utc).isoformat(),
        "available_hours_per_day": available_hours_per_day,
        "session_duration": study_session_duration,
        "total_active_tasks": len(scored_tasks),
        "total_study_hours": total_study_hours,
        "estimated_completion_days": int(estimated_completion_days) + 1,
        "schedule": schedule
    }


def adjust_plan_for_missed_task(
    current_plan: Dict[str, Any],
    missed_task_name: str
) -> Dict[str, Any]:
    """
    Adjust the study plan when a task is missed.
    Increases priority and reschedules.
    
    Args:
        current_plan: Current study plan
        missed_task_name: Name of the missed task
        
    Returns:
        Updated study plan
    """
    # Find the missed task in the schedule
    for task in current_plan.get("schedule", []):
        if task["task_name"] == missed_task_name:
            # Increase priority score for missed task
            task["priority_score"] = task["priority_score"] * 1.5
            task["priority_status"] = "Ongoing"  # Mark as ongoing to give it attention
    
    # Re-sort schedule by priority score
    current_plan["schedule"].sort(key=lambda x: x["priority_score"], reverse=True)
    
    # Regenerate session timings
    sessions_per_day = int(
        current_plan.get("available_hours_per_day", 4) / 
        current_plan.get("session_duration", 1)
    )
    current_date = datetime.now(timezone.utc)
    session_counter = 0
    
    for task in current_plan["schedule"]:
        for session in task["sessions"]:
            session_date = current_date + timedelta(days=session_counter // sessions_per_day)
            session["date"] = session_date.isoformat()
            session["time_slot"] = (session_counter % sessions_per_day) + 1
            session_counter += 1
    
    current_plan["plan_generated_at"] = datetime.now(timezone.utc).isoformat()
    current_plan["adjustment_reason"] = f"Adjusted for missed task: {missed_task_name}"
    
    return current_plan


def get_upcoming_tasks(tasks: List[Dict[str, Any]], days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Get tasks that are due within the specified number of days.
    
    Args:
        tasks: List of all tasks
        days_ahead: Number of days to look ahead
        
    Returns:
        List of upcoming tasks
    """
    now = datetime.now(timezone.utc)
    cutoff_date = now + timedelta(days=days_ahead)
    
    upcoming = []
    for task in tasks:
        if task.get("timedue"):
            try:
                due_date = datetime.fromisoformat(str(task["timedue"]).replace('Z', '+00:00'))
                if due_date.tzinfo is None:
                    due_date = due_date.replace(tzinfo=timezone.utc)
                
                if now <= due_date <= cutoff_date:
                    upcoming.append(task)
            except (ValueError, AttributeError):
                continue
    
    return sorted(upcoming, key=lambda x: x.get("timedue", ""))
