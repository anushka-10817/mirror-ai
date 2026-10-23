from datetime import datetime, timedelta
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Demo storage: tasks stay available while the server is running.
tasks = []
next_task_id = 1

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MIRROR AI | Planning Partner</title>
<style>
:root { color-scheme: dark; --bg:#0b1020; --panel:#151b30; --border:#303653; --text:#f5f7ff; --muted:#b7c0da; --accent:#a99cff; --card:#202744; }
* { box-sizing:border-box; }
body { margin:0; padding:28px 16px 50px; font-family:Inter,Arial,sans-serif; background:radial-gradient(ellipse at top,#1a2040 0%,var(--bg) 55%); color:var(--text); }
main { max-width:1100px; margin:auto; }
header { color:var(--accent); font-weight:800; letter-spacing:4px; }
.hero,.panel,.stat { background:rgba(21,27,48,.94); border:1px solid var(--border); border-radius:18px; padding:22px; margin:18px 0; box-shadow:0 12px 35px #0002; }
h1 { font-size:clamp(32px,6vw,52px); margin:10px 0; line-height:1.05; }
h2 { margin-top:0; font-size:21px; }
p { color:var(--muted); line-height:1.55; }
.eyebrow { color:var(--accent); text-transform:uppercase; letter-spacing:2px; font-size:12px; font-weight:800; }
.stats { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:18px 0; }
.stat { margin:0; } .stat strong { font-size:30px; display:block; margin-top:8px; }
.workspace { display:grid; grid-template-columns:1fr 1fr; gap:18px; align-items:start; }
label { display:block; margin:14px 0 7px; color:#c4cbea; }
input,select { width:100%; padding:12px; border-radius:9px; border:1px solid #3a4364; background:#0b1020; color:white; }
button { background:var(--accent); color:#141329; border:0; padding:11px 15px; border-radius:9px; margin-top:12px; font-weight:800; cursor:pointer; }
button:hover { filter:brightness(1.08); } button.secondary { background:#303957; color:var(--text); }
.task,.insight,.bubble { background:var(--card); padding:13px; border-radius:10px; margin:10px 0; overflow-wrap:anywhere; }
.task small { display:block; color:#c4cbea; margin-top:7px; }
.task.done { opacity:.65; } .task.done strong { text-decoration:line-through; }
.insight { border-left:3px solid var(--accent); }
.chat-window { min-height:180px; max-height:320px; overflow-y:auto; padding:6px 0; }
.bubble { max-width:92%; white-space:pre-wrap; line-height:1.5; }
.bubble.user { margin-left:auto; background:#39315e; }
.bubble.assistant { border-left:3px solid var(--accent); }
.chat-form { display:flex; gap:8px; align-items:center; } .chat-form input { flex:1; min-width:0; } .chat-form button { margin-top:0; }
.examples { display:flex; flex-wrap:wrap; gap:7px; margin-top:12px; }
.examples button { margin:0; font-size:12px; padding:8px 10px; }
#message { min-height:20px; }
footer { text-align:center; font-size:12px; color:#8490b2; margin-top:24px; }
@media(max-width:700px) { .workspace,.stats { grid-template-columns:1fr; } .chat-form { align-items:stretch; flex-direction:column; } .chat-form button { width:100%; } }
</style>
</head>
<body>
<main>
<header>MIRROR AI</header>
<section class="hero">
<div class="eyebrow">Your conversational planning partner</div>
<h1>Think ahead.<br>Not just on time.</h1>
<p>Organise commitments, understand deadline pressure, and use natural-language commands to plan your next move.</p>
</section>
<section class="stats">
<div class="stat"><p>Total commitments</p><strong id="total">0</strong></div>
<div class="stat"><p>Upcoming</p><strong id="upcoming">0</strong></div>
<div class="stat"><p>High priority</p><strong id="high">0</strong></div>
</section>
<section class="workspace">
<div class="panel">
<h2>＋ Add a commitment</h2>
<form id="taskForm">
<label for="title">Task name</label><input id="title" placeholder="e.g. Submit Java project" required maxlength="120">
<label for="deadline">Deadline</label><input id="deadline" type="datetime-local" required>
<label for="priority">Priority</label><select id="priority"><option>High</option><option selected>Medium</option><option>Low</option></select>
<button type="submit">Add commitment →</button><p id="message" role="status"></p>
</form>
</div>
<div class="panel">
<h2>Your commitments</h2><div id="taskList">Loading commitments...</div>
</div>
</section>
<section class="panel">
<h2>✦ Talk to Mirror</h2>
<p>Type a request in everyday language. Try adding a task, checking what's due next, or completing a task.</p>
<div id="chatWindow" class="chat-window" aria-live="polite"><div class="bubble assistant">Hi! I'm your Mirror planning assistant. I can add tasks, list commitments, find your next deadline, show overdue or high-priority tasks, and mark tasks complete.</div></div>
<form id="chatForm" class="chat-form"><input id="chatInput" autocomplete="off" placeholder="e.g. Add Java revision tomorrow at 6 pm high priority" maxlength="300" required><button type="submit">Send ↗</button></form>
<div class="examples">
<button type="button" class="secondary" data-prompt="Add Java revision tomorrow at 6 pm high priority">Add a task</button>
<button type="button" class="secondary" data-prompt="What is my next deadline?">Next deadline</button>
<button type="button" class="secondary" data-prompt="Show my pending tasks">Pending tasks</button>
<button type="button" class="secondary" data-prompt="Show my high priority tasks">High priority</button>
</div>
</section>
<section class="panel"><h2>✦ Planning insights</h2><div id="insights"></div></section>
<footer>Mirror AI · Conversational productivity demo · Tasks are stored in memory while the app is running.</footer>
</main>
<script>
const form = document.getElementById('taskForm');
const message = document.getElementById('message');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatWindow = document.getElementById('chatWindow');
function safeElement(tag, text, className) { const el=document.createElement(tag); el.textContent=text; if(className) el.className=className; return el; }
function addBubble(text, who) { const b=safeElement('div',text,'bubble '+who); chatWindow.appendChild(b); chatWindow.scrollTop=chatWindow.scrollHeight; }
async function refresh() {
 const response=await fetch('/api/tasks'); const items=await response.json();
 document.getElementById('total').textContent=items.filter(t=>!t.completed).length;
 document.getElementById('upcoming').textContent=items.filter(t=>!t.completed && new Date(t.deadline)>=new Date()).length;
 document.getElementById('high').textContent=items.filter(t=>!t.completed && t.priority==='High').length;
 const list=document.getElementById('taskList'); list.replaceChildren();
 if(!items.length) list.appendChild(safeElement('p','No commitments yet. Add your first one.'));
 items.sort((a,b)=>new Date(a.deadline)-new Date(b.deadline));
 items.forEach(task=>{
  const card=safeElement('div','','task'+(task.completed?' done':''));
  card.appendChild(safeElement('strong',task.title));
  card.appendChild(safeElement('small',new Date(task.deadline).toLocaleString()+' · '+task.priority+' priority · '+(task.completed?'Completed':'Pending')));
  if(!task.completed){ const btn=safeElement('button','Mark complete','secondary'); btn.type='button'; btn.style.marginTop='10px'; btn.addEventListener('click',async()=>{ const r=await fetch('/api/tasks/'+task.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({completed:true})}); if(r.ok){ addBubble('Marked “'+task.title+'” complete. Nice work!','assistant'); await refresh(); }}); card.appendChild(btn); }
  list.appendChild(card);
 });
 const insights=document.getElementById('insights'); insights.replaceChildren(); const notes=[]; const now=new Date();
 const active=items.filter(t=>!t.completed);
 const soon=active.filter(t=>{const h=(new Date(t.deadline)-now)/3600000;return h>=0&&h<=48;});
 const overdue=active.filter(t=>new Date(t.deadline)<now);
 if(soon.length) notes.push(soon.length+' commitment(s) are due within the next 48 hours. Plan time for them now.');
 if(overdue.length) notes.push(overdue.length+' commitment(s) have passed their deadlines. Review your plan.');
 for(let i=0;i<active.length;i++) for(let j=i+1;j<active.length;j++) if(Math.abs(new Date(active[i].deadline)-new Date(active[j].deadline))<=24*3600000) notes.push('“'+active[i].title+'” and “'+active[j].title+'” are due within 24 hours of each other. Check your workload.');
 if(!notes.length) notes.push('No immediate deadline pressure detected from your pending tasks.');
 notes.forEach(n=>insights.appendChild(safeElement('div',n,'insight')));
}
form.addEventListener('submit',async e=>{e.preventDefault();message.textContent='';const r=await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:document.getElementById('title').value.trim(),deadline:document.getElementById('deadline').value,priority:document.getElementById('priority').value})});const data=await r.json();if(!r.ok){message.textContent=data.error||'Could not add commitment.';return;}form.reset();document.getElementById('priority').value='Medium';message.textContent='Commitment added!';await refresh();});
chatForm.addEventListener('submit',async e=>{e.preventDefault();const text=chatInput.value.trim();if(!text)return;addBubble(text,'user');chatInput.value='';const r=await fetch('/api/assistant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});const data=await r.json();addBubble(data.reply||'I could not process that request.','assistant');await refresh();});
document.querySelectorAll('[data-prompt]').forEach(b=>b.addEventListener('click',()=>{chatInput.value=b.dataset.prompt;chatInput.focus();}));
refresh().catch(()=>{document.getElementById('taskList').textContent='Could not load tasks. Please refresh the page.';});
</script>
</body>
</html>
"""


def parse_deadline(text):
    """Parse common demo-friendly natural-language deadlines."""
    now = datetime.now().replace(second=0, microsecond=0)
    lower = text.lower()
    time_match = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lower)
    hour, minute = 17, 0
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridiem = time_match.group(3)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        if hour > 23 or minute > 59:
            time_match = None
            hour, minute = 17, 0

    if "tomorrow" in lower:
        day = (now + timedelta(days=1)).date()
        return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute), r"\btomorrow\b(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?"
    if "today" in lower:
        day = now.date()
        due = datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)
        if due <= now and not time_match:
            due = now + timedelta(hours=2)
        return due, r"\btoday\b(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?"

    relative = re.search(r"\bin\s+(\d+)\s+(hours?|days?|weeks?)\b", lower)
    if relative:
        count = int(relative.group(1)); unit = relative.group(2)
        delta = timedelta(hours=count) if unit.startswith('hour') else timedelta(days=count * (7 if unit.startswith('week') else 1))
        return now + delta, relative.group(0)

    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})(?:\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?", lower)
    if iso:
        d = datetime.strptime(iso.group(1), "%Y-%m-%d").date()
        h, m = 17, 0
        if iso.group(2):
            h = int(iso.group(2)); m = int(iso.group(3) or 0); mer = iso.group(4)
            if mer == 'pm' and h != 12: h += 12
            if mer == 'am' and h == 12: h = 0
        return datetime.combine(d, datetime.min.time()).replace(hour=h, minute=m), iso.group(0)

    return now + timedelta(days=1, hours=0), None


def create_task(title, deadline, priority="Medium"):
    global next_task_id
    task = {"id": next_task_id, "title": title, "deadline": deadline.strftime("%Y-%m-%dT%H:%M"), "priority": priority, "completed": False}
    next_task_id += 1
    tasks.append(task)
    return task


def format_task(task):
    due = datetime.fromisoformat(task["deadline"]).strftime("%a, %b %d at %I:%M %p")
    status = "completed" if task.get("completed") else "pending"
    return f"• {task['title']} — {due}, {task['priority']} priority ({status})"


def assistant_reply(message):
    text = message.strip()
    lower = text.lower()
    active = [t for t in tasks if not t.get("completed")]

    # Match greetings as whole words so "high priority" is not mistaken for "hi".
    if re.fullmatch(r"(?:hello|hi|hey)[!. ]*", lower):
        return "Hi! I'm Mirror, your planning assistant. I can add tasks, list pending commitments, find your next deadline, show overdue or high-priority work, and mark tasks complete."

    # Handle task creation BEFORE priority/deadline queries. Otherwise a command like
    # "Add Java revision tomorrow at 6 pm high priority" is mistaken for a query.
    if re.search(r"\b(add|create|new task|remind me to)\b", lower):
        deadline, matched_date = parse_deadline(text)
        priority = "High" if re.search(r"\b(high|urgent)\s+priority\b|\bpriority\s+(high|urgent)\b", lower) else ("Low" if re.search(r"\blow\s+priority\b|\bpriority\s+low\b", lower) else "Medium")
        title = text
        title = re.sub(r"^\s*(please\s+)?(add|create|new task|remind me to)\s*", "", title, flags=re.I)
        if matched_date:
            title = re.sub(matched_date, "", title, flags=re.I)
        title = re.sub(r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", "", title, flags=re.I)
        title = re.sub(r"\b(?:with\s+)?(?:high|medium|low|urgent)\s+priority\b|\bpriority\s+(?:high|medium|low|urgent)\b", "", title, flags=re.I)
        title = re.sub(r"\b(?:for|by|with)\s*$", "", title, flags=re.I).strip(" .,:;-–")
        if title.lower().startswith("task "):
            title = title[5:].strip()
        if not title:
            return "What should I call the task? Try: ‘Add Java revision tomorrow at 6 pm high priority.’"
        task = create_task(title[:120], deadline, priority)
        default_note = " I used tomorrow at 5:00 PM because no date was specified." if not matched_date else ""
        return f'Added “{task["title"]}” for {deadline.strftime("%a, %b %d at %I:%M %p")} with {priority.lower()} priority.{default_note}'

    if any(p in lower for p in ["what's next", "what is next", "next deadline", "upcoming deadline", "due next"]):
        future = [t for t in active if datetime.fromisoformat(t["deadline"]) >= datetime.now()]
        if not future:
            return "You don't have any future deadlines in your pending tasks. Want to add a commitment?"
        task = min(future, key=lambda t: t["deadline"])
        return "Your next deadline is:\n" + format_task(task)

    if "overdue" in lower or "past deadline" in lower or "late task" in lower:
        overdue = [t for t in active if datetime.fromisoformat(t["deadline"]) < datetime.now()]
        return "Here are your overdue tasks:\n" + "\n".join(format_task(t) for t in overdue) if overdue else "Good news — you have no overdue pending tasks."

    if any(phrase in lower for phrase in ["high priority", "high-priority", "urgent tasks", "urgent work"]):
        high = [t for t in active if t["priority"] == "High"]
        return "Your high-priority pending tasks:\n" + "\n".join(format_task(t) for t in high) if high else "You have no high-priority pending tasks right now."

    if any(phrase in lower for phrase in ["show my tasks", "list my tasks", "pending tasks", "what tasks", "my commitments", "list tasks", "show tasks"]):
        return "Here are your pending commitments:\n" + "\n".join(format_task(t) for t in active) if active else "You have no pending commitments yet. Try: ‘Add Java revision tomorrow at 6 pm high priority.’"

    if any(word in lower for word in ["complete", "mark", "finish", "done"]):
        candidates = [t for t in active if t["title"].lower() in lower or any(part in lower for part in t["title"].lower().split() if len(part) > 3)]
        if candidates:
            task = candidates[0]
            task["completed"] = True
            return f'Marked “{task["title"]}” complete. Nice work!'
        return "I couldn't match that to a pending task. Include part of the task name, such as ‘mark Java revision complete’."

    return "I can help with tasks and deadlines. Try ‘Add Java revision tomorrow at 6 pm high priority’, ‘What is my next deadline?’, ‘Show my pending tasks’, or ‘Mark Java revision complete’."


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/api/tasks", methods=["GET", "POST"])
def manage_tasks():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        title = str(data.get("title", "")).strip()
        deadline_text = str(data.get("deadline", "")).strip()
        priority = data.get("priority", "Medium")
        if not title or not deadline_text:
            return jsonify({"error": "Task name and deadline are required."}), 400
        if priority not in ["High", "Medium", "Low"]:
            return jsonify({"error": "Invalid priority."}), 400
        try:
            deadline = datetime.fromisoformat(deadline_text)
        except ValueError:
            return jsonify({"error": "Please provide a valid deadline."}), 400
        return jsonify(create_task(title[:120], deadline, priority)), 201
    return jsonify(tasks)


@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def update_task(task_id):
    data = request.get_json(silent=True) or {}
    for task in tasks:
        if task["id"] == task_id:
            if "completed" in data:
                task["completed"] = bool(data["completed"])
            return jsonify(task)
    return jsonify({"error": "Task not found."}), 404


@app.route("/api/assistant", methods=["POST"])
def assistant():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Please enter a request."}), 400
    if len(message) > 300:
        return jsonify({"error": "Please keep your request under 300 characters."}), 400
    return jsonify({"reply": assistant_reply(message)})


if __name__ == "__main__":
    app.run(debug=True)
