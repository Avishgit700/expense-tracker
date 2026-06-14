# Expense Tracker — Python Learning Project

A desktop Expense Tracker built while learning Python fundamentals.
Grew from a CLI script into a full GUI desktop app with AI features.

---

## What this project covers

| Topic | Where it shows up in this project |
|---|---|
| Variables & data types | `DB_FILE`, colours, fonts, amount parsing |
| Loops & functions | `db_fetch_all()`, `refresh_table()`, `for row in rows` |
| OOP (classes) | `ExpenseApp(tk.Tk)` — the whole GUI is one class |
| Git branches & PRs | This repo history |
| Linux CLI | Used to run Python & pip commands in terminal |
| File permissions | `.gitignore` keeps secrets out of the repo |
| SQL SELECT / JOIN | All four `db_*` functions use raw SQL |
| SQLite (local DB) | `expenses.db` — built-in Python database |

---

## Project evolution

### Phase 1 — CLI version (`tracker.py`)
A terminal menu app. No GUI, just `input()` and `print()`.

```
1. Add income
2. Add expense
3. View all transactions
4. Summary (balance)
5. Delete a transaction
6. Export to CSV
0. Quit
```

### Phase 2 — Desktop GUI version (`app.py`)
Rebuilt the same app using **Tkinter** — Python's built-in GUI library.
Same SQLite database, same logic, but with a dark purple UI you can click around in.

### Phase 3 — AI Edition (current)
Added three AI features powered by the **Anthropic Python SDK** (Claude Opus 4.8).

---

## Tech stack

| Tool | Purpose | How we got it |
|---|---|---|
| Python 3.14 | Language | Already installed (`py --version`) |
| `sqlite3` | Local database | Built into Python — no install needed |
| `tkinter` | GUI framework | Built into Python — no install needed |
| `csv` | Export to spreadsheet | Built into Python |
| `threading` | Non-blocking AI calls | Built into Python |
| `anthropic` | Claude AI SDK | `py -m pip install anthropic` |
| PyInstaller | Package into .exe | `py -m pip install pyinstaller` |

---

## Database — SQLite

### What is SQLite?

SQLite is a **file-based** database. The entire database lives in one file (`expenses.db`).
No server to start, no password to set — it just works.

Compare to PostgreSQL:
- SQLite = file on your computer, perfect for local apps
- PostgreSQL = full server, perfect for web apps with many users

### Schema (the table we created)

```sql
CREATE TABLE IF NOT EXISTS transactions (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    type     TEXT    NOT NULL,
    category TEXT    NOT NULL,
    amount   REAL    NOT NULL,
    note     TEXT,
    date     TEXT    NOT NULL
);
```

**What each column means:**

| Column | Type | Constraint | Meaning |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique row number, auto-increments |
| `type` | TEXT | NOT NULL | "income" or "expense" |
| `category` | TEXT | NOT NULL | e.g. "Food", "Rent" |
| `amount` | REAL | NOT NULL | Dollar value, e.g. 12.50 |
| `note` | TEXT | (optional) | Free text, e.g. "McDonald's" |
| `date` | TEXT | NOT NULL | Stored as "YYYY-MM-DD HH:MM" |

### SQL queries used in this app

**Insert a transaction:**
```sql
INSERT INTO transactions (type, category, amount, note, date)
VALUES (?, ?, ?, ?, ?);
```

**Read all transactions (newest first):**
```sql
SELECT id, type, category, amount, note, date
FROM transactions
ORDER BY id DESC;
```

**Sum income:**
```sql
SELECT COALESCE(SUM(amount), 0)
FROM transactions
WHERE type = 'income';
```
`COALESCE` returns 0 instead of NULL when there are no rows.

**Delete a transaction:**
```sql
DELETE FROM transactions WHERE id = ?;
```

### Steps we followed to set up the database

1. Imported `sqlite3` (no install needed — it ships with Python)
2. Wrote `init_db()` — called once when the app starts
3. Used `conn = sqlite3.connect("expenses.db")` — creates the file if it does not exist
4. Ran `CREATE TABLE IF NOT EXISTS` — safe to call every startup, only creates once
5. Used `?` placeholders in all queries — **never** string-format SQL (prevents SQL injection)
6. Always called `conn.commit()` after INSERT/DELETE, then `conn.close()`

---

## How the GUI works (Tkinter)

```
ExpenseApp (inherits from tk.Tk — the main window)
├── header  (Frame)  — title bar
└── body    (Frame)  — split into two columns
    ├── sidebar (column 0)
    │   ├── Summary labels (income / expense / balance)
    │   ├── Add Transaction form (Category, Amount, Note, Type, Add button)
    │   ├── Export CSV button
    │   └── AI Insights button
    └── main (column 1)
        ├── Transactions table (ttk.Treeview)
        ├── AI Finance Assistant header
        ├── Chat text area (scrollable)
        └── Chat input + Send button
```

Key Tkinter concepts used:
- `tk.Frame` — invisible container for grouping widgets
- `tk.Label` — displays text
- `tk.Entry` — single-line text input
- `tk.Button` — clickable button
- `tk.Radiobutton` — select one option from a group
- `ttk.Treeview` — the table of transactions
- `.pack()` and `.grid()` — layout managers
- `.config()` — change a widget's properties at runtime
- `.bind("<Event>", handler)` — react to keyboard/mouse events

---

## AI features (Anthropic SDK)

All three features use `client.messages.create()` from the `anthropic` Python package.
Calls run in a **background thread** so the UI never freezes while waiting for a response.

### 1. Smart Category Suggestion

Triggered when the user types a note and clicks away from the field.

```python
resp = ai_client.messages.create(
    model="claude-opus-4-8",
    max_tokens=40,
    messages=[{
        "role": "user",
        "content": 'A financial transaction has this note: "mcdonalds"\n'
                   'Reply with ONLY a short category name.'
    }]
)
category = resp.content[0].text.strip()
# → "Food"
```

### 2. Monthly Spending Insights

Sends the full transaction table as text and asks Claude to analyse it.

```python
resp = ai_client.messages.create(
    model="claude-opus-4-8",
    max_tokens=600,
    messages=[{"role": "user", "content": "Analyse my spending...\n" + data}]
)
```

### 3. AI Chat Assistant

Multi-turn conversation. Each message is added to `_chat_history` (a list of dicts).
The system prompt contains the live transaction data so Claude always knows your finances.

```python
resp = ai_client.messages.create(
    model="claude-opus-4-8",
    max_tokens=500,
    system="You are a finance assistant. Here is the user's data:\n" + data,
    messages=self._chat_history   # full conversation history
)
```

---

## How to run

```bash
# 1. Set your API key (required for AI features)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# 2. Go to the project folder
cd C:\Projects\expense-tracker

# 3. Install the AI library (first time only)
py -m pip install anthropic

# 4. Run the app
py app.py
```

Without the API key, the app still works — only the AI features will show an error message.

---

## How to build the .exe (optional)

```bash
py -m pip install pyinstaller
py -m PyInstaller --onefile --windowed --name "ExpenseTracker" app.py
# Output: dist/ExpenseTracker.exe
```

The `.exe` runs on any Windows PC without Python installed.

---

## File structure

```
expense-tracker/
├── app.py          ← Main GUI app (AI Edition)
├── tracker.py      ← Original CLI version
├── .gitignore      ← Keeps secrets + build files out of git
└── README.md       ← This file
```

`expenses.db` and `dist/` are excluded from git via `.gitignore`.
The database contains personal financial data — never commit it.

---

## Git workflow used

```bash
git init
git add app.py tracker.py .gitignore README.md
git commit -m "Add expense tracker: CLI + GUI + AI features"
git push
```

**Why we only add specific files:**
Running `git add .` would accidentally include `expenses.db` (your personal data),
`dist/ExpenseTracker.exe` (12 MB binary), and build cache files.
Always add files by name or use `.gitignore` carefully.

---

## Key Python concepts used — quick reference

### Variables & data types
```python
DB_FILE = "expenses.db"          # str
amount  = 12.50                  # float
income  = 0                      # int
rows    = []                     # list
widths  = {"ID": 40, "Type": 70} # dict
```

### Functions
```python
def db_add(type_, category, amount, note):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO ...", (type_, category, amount, note, ...))
    conn.commit()
    conn.close()
```

### Loops
```python
for row in db_fetch_all():
    self.tree.insert("", "end", values=(row[0], row[1], ...))
```

### OOP — class with inheritance
```python
class ExpenseApp(tk.Tk):          # inherits from tk.Tk
    def __init__(self):
        super().__init__()        # call parent constructor
        self._chat_history = []   # instance variable
        self._build_ui()          # call own method

    def add_transaction(self):    # instance method
        ...
```

### Threading (non-blocking AI calls)
```python
threading.Thread(
    target=self._run_chat,
    args=(data,),
    daemon=True          # thread dies when app closes
).start()

# After thread finishes, schedule UI update on main thread:
self.after(0, self._finish_chat, answer)
```