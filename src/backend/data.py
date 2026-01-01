import csv

file_path = "C:/Sannman/BACKEND/hackthonapp/backend/db/db.csv"

import csv

file_path = "C:/Sannman/BACKEND/hackthonapp/backend/db/db.csv"

def process_task(data: dict):
    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            data.get("task_name"),
            data.get("scale_difficulty"),
            data.get("priority"),
            data.get("createdAt"),
            data.get("timedue")
        ])

    return {"status": "saved"}

def read_tasks() -> list[dict]:
    tasks = []
    with open(file_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            tasks.append(row)
    return tasks


def store_score(task_name: str, score: float):
    with open("C:/Sannman/BACKEND/hackthonapp/backend/db/scores.csv", mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([task_name, score])
    return {"status": "score saved"}