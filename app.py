from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

tasks = []

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MIRROR AI</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0; padding: 30px 18px;
    font-family: Arial, sans-serif;
    background: #0b1020; color: #f5f7ff;
}
main { max-width: 1000px; margin: auto; }
header { color: #a99cff; font-weight: bold; letter-spacing: 3px; }
.hero, .panel, .stat {
    background: #151b30; border: 1px solid #303653;
    border-radius: 16px; padding: 24px; margin: 20px 0;
}
h1 { font-size: clamp(32px, 6vw, 52px); margin-bottom: 10px; }
p { color: #b7c0da; line-height: 1.6; }
.stats { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; }
.stat { margin: 0; }
.stat strong { font-size: 28px; }
.workspace { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
label { display: block; margin: 14px 0 7px; color: #c4cbea; }
input, select {
    width: 100%; padding: 12px; border-radius: 8px;
    border: 1px solid #3a4364; background: #0b1020; color: white;
}
button {
    background: #a99cff; color: #141329; border: 0;
    padding: 12px 16px; border-radius: 8px;
    margin-top: 16px; font-weight: bold; cursor: pointer;
}
.task, .insight {
    background: #202744; padding: 14px;
    border-radius: 9px; margin: 10px 0; overflow-wrap: anywhere;
}
.task small { display: block; color: #c4cbea; margin-top: 8px; }
.insight { border-left: 3px solid #a99cff; }
@media(max-width:650px) {
    .workspace, .stats { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<main>
<header>MIRROR AI</header>
<section class="hero">
<p>YOUR PROACTIVE PLANNING PARTNER</p>
<h1>Think ahead.<br>Not just on time.</h1>
<p>Spot deadline pressure, organise your commitments, and decide what needs attention next.</p>
</section>

<section class="stats">
<div class="stat"><p>Commitments</p><strong id="total">0</strong></div>
<div class="stat"><p>Upcoming</p><strong id="upcoming">0</strong></div>
<div class="stat"><p>High priority</p><strong id="high">0</strong></div>
</section>

<section class="workspace">
<div class="panel">
<h2>＋ Add a commitment</h2>
<form id="taskForm">
<label for="title">Task name</label>
<input id="title" placeholder="e.g. Submit Java project" required maxlength="120">
<label for="deadline">Deadline</label>
<input id="deadline" type="datetime-local" required>
<label for="priority">Priority</label>
<select id="priority">
<option>High</option><option selected>Medium</option><option>Low</option>
</select>
<button type="submit">Add commitment →</button>
<p id="message" role="status"></p>
</form>
</div>
<div class="panel">
<h2>Your commitments</h2>
<div id="taskList">Loading commitments...</div>
</div>
</section>

<section class="panel">
<h2>✦ MIRROR insights</h2>
<div id="insights"></div>
</section>
</main>

<script>
const form = document.getElementById("taskForm");
const message = document.getElementById("message");

function safeElement(tag, text, className) {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    return el;
}

async function refresh() {
    const response = await fetch("/api/tasks");
    const tasks = await response.json();
    document.getElementById("total").textContent = tasks.length;
    document.getElementById("upcoming").textContent =
        tasks.filter(t => new Date(t.deadline) >= new Date()).length;
    document.getElementById("high").textContent =
        tasks.filter(t => t.priority === "High").length;

    const list = document.getElementById("taskList");
    list.replaceChildren();

    if (!tasks.length) {
        list.appendChild(safeElement("p", "No commitments yet. Add your first one."));
    }

    tasks.sort((a,b) => new Date(a.deadline)-new Date(b.deadline));

    tasks.forEach(task => {
        const card = safeElement("div", "", "task");
        card.appendChild(safeElement("strong", task.title));
        card.appendChild(safeElement("small",
            new Date(task.deadline).toLocaleString() + " · " + task.priority + " priority"));
        list.appendChild(card);
    });

    const insights = document.getElementById("insights");
    insights.replaceChildren();
    const notes = [];
    const now = new Date();

    const soon = tasks.filter(t => {
        const hours = (new Date(t.deadline) - now) / 3600000;
        return hours >= 0 && hours <= 48;
    });
    if (soon.length) notes.push(soon.length +
        " commitment(s) are due within the next 48 hours. Plan time for them now.");

    const overdue = tasks.filter(t => new Date(t.deadline) < now);
    if (overdue.length) notes.push(overdue.length +
        " commitment(s) have passed their deadlines. Review your plan.");

    for (let i=0; i<tasks.length; i++) {
        for (let j=i+1; j<tasks.length; j++) {
            if (Math.abs(new Date(tasks[i].deadline)-new Date(tasks[j].deadline))
                <= 24*3600000) {
                notes.push('"' + tasks[i].title + '" and "' + tasks[j].title +
                    '" are due within 24 hours of each other. Check your workload.');
            }
        }
    }

    if (!notes.length) notes.push(
        "No immediate deadline pressure detected from the tasks you've added.");
    notes.forEach(note => insights.appendChild(safeElement("div", note, "insight")));
}

form.addEventListener("submit", async event => {
    event.preventDefault();
    message.textContent = "";
    const response = await fetch("/api/tasks", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            title: document.getElementById("title").value.trim(),
            deadline: document.getElementById("deadline").value,
            priority: document.getElementById("priority").value
        })
    });
    const result = await response.json();
    if (!response.ok) {
        message.textContent = result.error || "Couldn't add commitment.";
        return;
    }
    form.reset();
    document.getElementById("priority").value = "Medium";
    message.textContent = "Commitment added!";
    await refresh();
});

refresh().catch(() => {
    document.getElementById("taskList").textContent =
        "Could not load tasks. Please refresh the page.";
});
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/api/tasks", methods=["GET", "POST"])
def manage_tasks():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        title = data.get("title", "").strip()
        deadline = data.get("deadline", "")
        priority = data.get("priority", "Medium")

        if not title or not deadline:
            return jsonify({"error": "Task name and deadline are required."}), 400

        if priority not in ["High", "Medium", "Low"]:
            return jsonify({"error": "Invalid priority."}), 400

        task = {
            "id": len(tasks) + 1,
            "title": title,
            "deadline": deadline,
            "priority": priority
        }
        tasks.append(task)
        return jsonify(task), 201

    return jsonify(tasks)

if __name__ == "__main__":
    app.run(debug=True)