# EduTech - Personalized Study Plan Generator Backend

A dynamic study plan system that adjusts based on difficulty, available time, upcoming exams, and missed or completed tasks.

## Features

- **Task Management**: Create, update, and track study tasks with difficulty levels and deadlines
- **Dynamic Scheduling**: Automatically generates personalized study plans based on:
  - Task difficulty (1-5 scale)
  - Priority status (Pending, Ongoing, Completed)
  - Time urgency (proximity to due date)
  - Available study hours per day
- **Adaptive Planning**: Adjusts study plans when tasks are missed or completed
- **Progress Tracking**: Monitor completion rates, overdue tasks, and study statistics
- **Smart Prioritization**: Calculates priority scores combining difficulty, status, and urgency

## Installation

1. Clone the repository:
```bash
git clone https://github.com/sannman/studyplan-backend.git
cd studyplan-backend
```

2. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies:
```bash
uv sync
```

## Running the Application

Start the Flask development server:
```bash
uv run python -m src.backend.app
```

The server will start on `http://localhost:5000`

**For development with debug mode enabled:**
```bash
FLASK_DEBUG=true uv run python -m src.backend.app
```

**For production:** Use a production WSGI server like gunicorn or waitress:
```bash
uv add gunicorn
uv run gunicorn -w 4 -b 0.0.0.0:5000 src.backend.app:app
```

## API Endpoints

### Health Check
```
GET /health
```
Returns server status.

### Task Management

#### Create Task
```
POST /post_task
Content-Type: application/json

{
  "task_name": "Study Calculus Chapter 1",
  "scale_difficulty": 4,
  "priority": "Pending",
  "timedue": "2026-01-15T10:00:00Z"
}
```

#### Get All Tasks
```
GET /get_tasks
```

#### Update Task Status
```
PUT /update_task_status
Content-Type: application/json

{
  "task_name": "Study Calculus Chapter 1",
  "new_status": "Completed"
}
```

#### Delete Task
```
DELETE /delete_task/<task_name>
```

#### Get Tasks by Status
```
GET /tasks_by_status/<status>
```
Status can be: `Pending`, `Ongoing`, or `Completed`

### Study Planning

#### Calculate Task Scores
```
GET /score_tasks
```
Returns priority scores for all tasks based on difficulty, priority, and time urgency.

#### Generate Study Plan
```
POST /generate_plan
Content-Type: application/json

{
  "available_hours_per_day": 4.0,
  "study_session_duration": 1.0
}
```
Generates a complete study schedule with session timings.

#### Mark Task as Missed
```
POST /mark_missed/<task_name>
```
Increases priority and regenerates the study plan.

### Task Queries

#### Get Upcoming Tasks
```
GET /upcoming_tasks?days_ahead=7
```

#### Get Overdue Tasks
```
GET /overdue_tasks
```

#### Get Statistics
```
GET /stats
```
Returns overall statistics including completion rate, average difficulty, and task counts.

## Priority Scoring Algorithm

The system calculates priority scores using:

**Score = Difficulty Weight × Priority Weight × Time Weight**

- **Difficulty Weight**: 1.0 (easy) to 3.0 (very hard)
- **Priority Weight**: 
  - Pending: 1.0
  - Ongoing: 2.0
  - Completed: 0.0
- **Time Weight**: Increases as deadline approaches
  - Overdue: 5.0
  - Due within 24 hours: 4.5
  - Due within 3 days: 3.5
  - Due within 7 days: 2.5
  - Due within 14 days: 1.5
  - Due later: 1.0

## Example Usage

### Creating Tasks and Generating a Study Plan

```bash
# Create tasks
curl -X POST http://localhost:5000/post_task \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "Physics Exam Prep",
    "scale_difficulty": 5,
    "priority": "Ongoing",
    "timedue": "2026-01-08T14:00:00Z"
  }'

# Generate study plan
curl -X POST http://localhost:5000/generate_plan \
  -H "Content-Type: application/json" \
  -d '{"available_hours_per_day": 5.0, "study_session_duration": 1.5}'

# Check statistics
curl http://localhost:5000/stats

# Mark task as completed
curl -X PUT http://localhost:5000/update_task_status \
  -H "Content-Type: application/json" \
  -d '{"task_name": "Physics Exam Prep", "new_status": "Completed"}'
```

## Data Storage

The application now uses a lightweight local SQLite database for persistence:
- `db/studyplan.db`: Stores task records and calculated priority scores

## Architecture

- **app.py**: Flask REST API endpoints
- **planner.py**: Core scheduling and prioritization algorithms
- **data.py**: SQLite-based data persistence layer

## Technologies

- Python 3.13+
- Flask 3.1.2
- Flask-CORS 6.0.2
- Pydantic 2.12.5
- Python-dotenv 1.2.1
