import os
import requests
import svgwrite
from datetime import datetime, timedelta

TOKEN = os.environ.get("GITLAB_TOKEN")
if not TOKEN:
    print("ERROR: GITLAB_TOKEN environment variable not found.")
    exit(1)

USERNAME = "mtagci"
BASE = "https://gitlab.iski.istanbul/api/v4"

headers = {"PRIVATE-TOKEN": TOKEN}

# username'den user_id bul
resp = requests.get(f"{BASE}/users", params={"username": USERNAME}, headers=headers)
resp.raise_for_status()
user_id = resp.json()[0]["id"]

URL = f"{BASE}/users/{user_id}/events"

# 365 günlük aktiviteleri çek
end = datetime.utcnow()
start = end - timedelta(days=365)

activity = {}

page = 1
while True:
    r = requests.get(URL, params={"page": page, "per_page": 100}, headers=headers)
    if r.status_code != 200:
        print("GitLab API error:", r.text)
        break
    data = r.json()
    if not data:
        break

    for e in data:
        date = e["created_at"].split("T")[0]
        if start.date() <= datetime.fromisoformat(date).date() <= end.date():
            activity[date] = activity.get(date, 0) + 1

    page += 1

# SVG üret
dwg = svgwrite.Drawing("gitlab-heatmap.svg", size=("900px", "140px"))

cell_size = 12
x_offset = 20
y_offset = 20

for i in range(53):
    for j in range(7):
        date = start + timedelta(weeks=i, days=j)
        date_str = date.strftime("%Y-%m-%d")
        count = activity.get(date_str, 0)

        if count == 0:
            color = "#1e1e1e"
        elif count == 1:
            color = "#3b82f6"
        elif count == 2:
            color = "#2563eb"
        else:
            color = "#1d4ed8"

        dwg.add(dwg.rect(
            insert=(x_offset + i * cell_size, y_offset + j * cell_size),
            size=(cell_size - 2, cell_size - 2),
            fill=color,
            rx=2, ry=2
        ))

dwg.save()
print("Heatmap generated: gitlab-heatmap.svg")
