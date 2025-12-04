import os
from pathlib import Path
import requests
import svgwrite
from datetime import datetime, timedelta

TOKEN = os.environ.get("GITLAB_TOKEN")

if not TOKEN:
    token_file = Path(__file__).with_name(".gitlab_token")
    if token_file.exists():
        TOKEN = token_file.read_text().strip()

if not TOKEN:
    print("ERROR: GITLAB_TOKEN environment variable not found and .gitlab_token file is missing.")
    raise SystemExit(1)

USERNAME = "mtagci"
BASE = "https://gitlab.iski.istanbul/api/v4"
headers = {"PRIVATE-TOKEN": TOKEN}

resp = requests.get(f"{BASE}/users", params={"username": USERNAME}, headers=headers)
resp.raise_for_status()
user_id = resp.json()[0]["id"]

URL = f"{BASE}/users/{user_id}/events"

today = datetime.utcnow().date()
first_day = today - timedelta(days=365)

start = first_day - timedelta(days=first_day.weekday())
end = today
num_weeks = 53

activity: dict[str, int] = {}

page = 1
while True:
    r = requests.get(URL, params={"page": page, "per_page": 100}, headers=headers)
    r.raise_for_status()
    data = r.json()
    if not data:
        break

    for e in data:
        date = datetime.fromisoformat(e["created_at"].split("T")[0]).date()
        if start <= date <= end:
            key = date.isoformat()
            activity[key] = activity.get(key, 0) + 1

    page += 1

cell_size = 12
x_offset = 30
y_offset = 30
width = x_offset + num_weeks * cell_size + 40
height = y_offset + 7 * cell_size + 40

dwg = svgwrite.Drawing(
    "gitlab-heatmap.svg",
    size=(f"{width}px", f"{height}px"),
    profile="tiny",
)

dwg.add(dwg.rect(insert=(0, 0), size=(width, height), fill="none"))

def color_for(count: int) -> str:
    if count == 0:
        return "#111827"
    elif count == 1:
        return "#1d4ed8"
    elif count == 2:
        return "#2563eb"
    elif count == 3:
        return "#3b82f6"
    else:
        return "#60a5fa"

MONTH_TR = {
    1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis",
    5: "May", 6: "Haz", 7: "Tem", 8: "Ağu",
    9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara",
}

last_month = None
for i in range(num_weeks):
    column_date = start + timedelta(weeks=i)
    if column_date.month != last_month and column_date.day <= 7:
        month_text = MONTH_TR[column_date.month]
        dwg.add(
            dwg.text(
                month_text,
                insert=(x_offset + i * cell_size, y_offset - 8),
                font_size="10px",
                fill="#9ca3af",
            )
        )
        last_month = column_date.month

weekday_labels = {
    0: "Pzt",
    2: "Çrş",
    4: "Cum",
}

for day_index, label in weekday_labels.items():
    dwg.add(
        dwg.text(
            label,
            insert=(5, y_offset + day_index * cell_size + 9),
            font_size="9px",
            fill="#6b7280",
        )
    )

for i in range(num_weeks):
    for j in range(7):
        cell_date = start + timedelta(weeks=i, days=j)
        if cell_date > end:
            continue
        date_str = cell_date.isoformat()
        count = activity.get(date_str, 0)

        color = color_for(count)

        dwg.add(
            dwg.rect(
                insert=(x_offset + i * cell_size, y_offset + j * cell_size),
                size=(cell_size - 2, cell_size - 2),
                fill=color,
                rx=2,
                ry=2,
            )
        )

legend_x = x_offset
legend_y = y_offset + 7 * cell_size + 20

levels = [0, 1, 2, 3, 4]
dwg.add(
    dwg.text(
        "Daha az  ▸  Daha çok",
        insert=(legend_x, legend_y - 5),
        font_size="9px",
        fill="#6b7280",
    )
)

for idx, lvl in enumerate(levels):
    dwg.add(
        dwg.rect(
            insert=(legend_x + idx * (cell_size + 2), legend_y),
            size=(cell_size - 2, cell_size - 2),
            fill=color_for(lvl),
            rx=2,
            ry=2,
        )
    )

dwg.save()
print("Heatmap generated: gitlab-heatmap.svg")
