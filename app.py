import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
import os
import threading
from datetime import datetime

import anthropic

DB_FILE = "expenses.db"

BG       = "#1e1e2e"
PANEL    = "#2a2a3e"
ACCENT   = "#7c3aed"
ACCENT2  = "#a855f7"
GREEN    = "#22c55e"
RED      = "#ef4444"
TEXT     = "#f1f5f9"
SUBTEXT  = "#94a3b8"
BORDER   = "#3f3f5a"
CHAT_BG  = "#12121e"

FONT        = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_TITLE  = ("Segoe UI", 18, "bold")
FONT_LABEL  = ("Segoe UI", 9)
FONT_SMALL  = ("Segoe UI", 9)

ai_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


# database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            type     TEXT    NOT NULL,
            category TEXT    NOT NULL,
            amount   REAL    NOT NULL,
            note     TEXT,
            date     TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def db_add(type_, category, amount, note):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO transactions (type,category,amount,note,date) VALUES (?,?,?,?,?)",
        (type_, category, round(amount, 2), note, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()


def db_delete(id_):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM transactions WHERE id=?", (id_,))
    conn.commit()
    conn.close()


def db_fetch_all():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute(
        "SELECT id,type,category,amount,note,date FROM transactions ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def db_summary():
    conn = sqlite3.connect(DB_FILE)
    income   = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income'").fetchone()[0]
    expenses = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense'").fetchone()[0]
    conn.close()
    return income, expenses


def db_transactions_text():
    rows = db_fetch_all()
    if not rows:
        return "No transactions recorded yet."
    lines = ["ID | Type    | Category       | Amount  | Note                | Date"]
    lines.append("-" * 75)
    for r in rows:
        lines.append(f"{r[0]:<4} | {r[1]:<7} | {r[2]:<14} | ${r[3]:>7.2f} | {str(r[4]):<20} | {r[5]}")
    income, expenses = db_summary()
    lines.append("")
    lines.append(f"Total income: ${income:.2f}  |  Total expenses: ${expenses:.2f}  |  Balance: ${income-expenses:.2f}")
    return "\n".join(lines)


# helper widgets
def styled_btn(parent, text, command, color=ACCENT, width=14):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=color, fg=TEXT, font=FONT_BOLD,
        relief="flat", bd=0, padx=10, pady=6,
        cursor="hand2", width=width,
        activebackground=ACCENT2, activeforeground=TEXT
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=ACCENT2))
    btn.bind("<Leave>", lambda e: btn.config(bg=color))
    return btn


def labeled_entry(parent, label, row, secret=False):
    tk.Label(parent, text=label, bg=PANEL, fg=SUBTEXT, font=FONT_LABEL).grid(
        row=row, column=0, sticky="w", pady=(6, 0))
    var = tk.StringVar()
    e = tk.Entry(parent, textvariable=var, bg=BORDER, fg=TEXT, font=FONT,
                 relief="flat", bd=6, insertbackground=TEXT,
                 show="*" if secret else "")
    e.grid(row=row+1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    return var, e


# main app
class ExpenseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        init_db()
        self.title("Expense Tracker  - AI Edition")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._chat_history = []
        self._ai_busy = False

        self._build_ui()
        self.refresh_table()
        self.refresh_summary()

    def _build_ui(self):
        header = tk.Frame(self, bg=PANEL, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="   Expense Tracker", bg=PANEL, fg=TEXT,
                 font=FONT_TITLE).pack(side="left", padx=20)
        tk.Label(header, text="AI Edition", bg=PANEL, fg=ACCENT2,
                 font=("Segoe UI", 11, "italic")).pack(side="left")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        self._build_sidebar(body)
        self._build_main(body)

    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=PANEL, bd=0, padx=16, pady=16)
        side.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        side.columnconfigure(0, weight=1)

        tk.Label(side, text="Summary", bg=PANEL, fg=TEXT, font=FONT_BOLD).grid(
            row=0, column=0, columnspan=2, sticky="w")
        tk.Frame(side, bg=BORDER, height=1).grid(row=1, column=0, columnspan=2, sticky="ew", pady=6)

        self.lbl_income   = tk.Label(side, text="Income:  $0.00", bg=PANEL, fg=GREEN, font=FONT)
        self.lbl_expense  = tk.Label(side, text="Expense: $0.00", bg=PANEL, fg=RED,   font=FONT)
        self.lbl_balance  = tk.Label(side, text="Balance: $0.00", bg=PANEL, fg=TEXT,  font=FONT_BOLD)
        self.lbl_income.grid( row=2, column=0, sticky="w", pady=2)
        self.lbl_expense.grid(row=3, column=0, sticky="w", pady=2)
        self.lbl_balance.grid(row=4, column=0, sticky="w", pady=(2,12))

        tk.Label(side, text="Add Transaction", bg=PANEL, fg=TEXT, font=FONT_BOLD).grid(
            row=5, column=0, columnspan=2, sticky="w")
        tk.Frame(side, bg=BORDER, height=1).grid(row=6, column=0, columnspan=2, sticky="ew", pady=6)

        self.v_category, self.e_category = labeled_entry(side, "Category", 7)
        self.v_amount, _                 = labeled_entry(side, "Amount ($)", 9)
        self.v_note, self.e_note         = labeled_entry(side, "Note (optional)", 11)

        self.e_note.bind("<FocusOut>", self._on_note_focusout)

        self.lbl_ai_suggest = tk.Label(side, text="", bg=PANEL, fg=ACCENT2,
                                        font=FONT_SMALL, wraplength=180, justify="left")
        self.lbl_ai_suggest.grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 4))

        tk.Label(side, text="Type", bg=PANEL, fg=SUBTEXT, font=FONT_LABEL).grid(
            row=13, column=0, sticky="w", pady=(6,0))
        self.v_type = tk.StringVar(value="expense")
        type_frame = tk.Frame(side, bg=PANEL)
        type_frame.grid(row=14, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(type_frame, text="Expense", variable=self.v_type, value="expense",
                       bg=PANEL, fg=RED,   selectcolor=PANEL, activebackground=PANEL,
                       font=FONT).pack(side="left")
        tk.Radiobutton(type_frame, text="Income",  variable=self.v_type, value="income",
                       bg=PANEL, fg=GREEN, selectcolor=PANEL, activebackground=PANEL,
                       font=FONT).pack(side="left", padx=8)

        styled_btn(side, "+ Add", self.add_transaction, color=ACCENT).grid(
            row=15, column=0, columnspan=2, sticky="ew", pady=(10,0))

        tk.Frame(side, bg=BORDER, height=1).grid(row=16, column=0, columnspan=2, sticky="ew", pady=10)
        styled_btn(side, "Export CSV", self.export_csv, color="#0f766e").grid(
            row=17, column=0, columnspan=2, sticky="ew")

        tk.Frame(side, bg=BORDER, height=1).grid(row=18, column=0, columnspan=2, sticky="ew", pady=10)
        self.btn_insights = styled_btn(side, "AI Insights", self.get_ai_insights, color="#6d28d9", width=16)
        self.btn_insights.grid(row=19, column=0, columnspan=2, sticky="ew")
        tk.Label(side, text="Monthly analysis of your spending", bg=PANEL, fg=SUBTEXT,
                 font=FONT_LABEL, wraplength=170).grid(row=20, column=0, columnspan=2, sticky="w", pady=(2,0))

    def _build_main(self, parent):
        main = tk.Frame(parent, bg=BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(1, weight=2)
        main.rowconfigure(3, weight=3)
        main.columnconfigure(0, weight=1)

        toolbar = tk.Frame(main, bg=BG, pady=4)
        toolbar.grid(row=0, column=0, sticky="ew")
        tk.Label(toolbar, text="Transactions", bg=BG, fg=TEXT, font=FONT_BOLD).pack(side="left")
        styled_btn(toolbar, "Delete selected", self.delete_selected, color=RED, width=16).pack(side="right")

        cols = ("ID", "Type", "Category", "Amount", "Note", "Date")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview",
            background=PANEL, foreground=TEXT, fieldbackground=PANEL,
            rowheight=28, font=FONT, borderwidth=0)
        style.configure("Custom.Treeview.Heading",
            background=BORDER, foreground=TEXT, font=FONT_BOLD, relief="flat")
        style.map("Custom.Treeview", background=[("selected", ACCENT)])

        tframe = tk.Frame(main, bg=BG)
        tframe.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        tframe.rowconfigure(0, weight=1)
        tframe.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tframe, columns=cols, show="headings",
                                  style="Custom.Treeview", selectmode="browse")
        widths = {"ID":40, "Type":70, "Category":120, "Amount":80, "Note":200, "Date":130}
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor="w")

        vsb = ttk.Scrollbar(tframe, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        tk.Frame(main, bg=BORDER, height=1).grid(row=2, column=0, sticky="ew", pady=(8,4))

        chat_header = tk.Frame(main, bg=BG)
        chat_header.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        tk.Label(chat_header, text="AI Finance Assistant", bg=BG, fg=ACCENT2, font=FONT_BOLD).pack(side="left")
        tk.Label(chat_header, text="  Ask anything about your spending", bg=BG, fg=SUBTEXT, font=FONT_SMALL).pack(side="left")

        chat_outer = tk.Frame(main, bg=CHAT_BG, bd=1, relief="flat")
        chat_outer.grid(row=3, column=0, sticky="nsew")
        chat_outer.rowconfigure(0, weight=1)
        chat_outer.columnconfigure(0, weight=1)

        self.chat_text = tk.Text(
            chat_outer, bg=CHAT_BG, fg=TEXT, font=FONT_SMALL,
            relief="flat", bd=8, wrap="word", state="disabled",
            insertbackground=TEXT, cursor="arrow"
        )
        chat_vsb = ttk.Scrollbar(chat_outer, orient="vertical", command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=chat_vsb.set)
        self.chat_text.grid(row=0, column=0, sticky="nsew")
        chat_vsb.grid(row=0, column=1, sticky="ns")

        self.chat_text.tag_configure("user_tag", foreground=ACCENT2, font=FONT_BOLD)
        self.chat_text.tag_configure("ai_tag",   foreground=GREEN,   font=FONT_BOLD)
        self.chat_text.tag_configure("msg_text", foreground=TEXT,    font=FONT_SMALL)
        self.chat_text.tag_configure("thinking", foreground=SUBTEXT, font=FONT_SMALL)

        input_row = tk.Frame(main, bg=BG, pady=6)
        input_row.grid(row=4, column=0, sticky="ew")
        input_row.columnconfigure(0, weight=1)

        self.chat_input = tk.Entry(
            input_row, bg=BORDER, fg=SUBTEXT, font=FONT,
            relief="flat", bd=8, insertbackground=TEXT
        )
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.chat_input.bind("<Return>", lambda e: self.send_chat())
        self.chat_input.insert(0, "Ask me about your finances...")
        self.chat_input.bind("<FocusIn>",  self._chat_placeholder_clear)
        self.chat_input.bind("<FocusOut>", self._chat_placeholder_restore)

        self.btn_send = styled_btn(input_row, "Send", self.send_chat, color=ACCENT, width=8)
        self.btn_send.grid(row=0, column=1)

        self._chat_append("ai", "Hi! I am your AI finance assistant. Ask me anything about your spending, or click [AI Insights] in the sidebar for a full monthly analysis.")

    def _chat_placeholder_clear(self, event=None):
        if self.chat_input.get() == "Ask me about your finances...":
            self.chat_input.delete(0, "end")
            self.chat_input.config(fg=TEXT)

    def _chat_placeholder_restore(self, event=None):
        if not self.chat_input.get().strip():
            self.chat_input.insert(0, "Ask me about your finances...")
            self.chat_input.config(fg=SUBTEXT)

    def _chat_append(self, role, text):
        self.chat_text.config(state="normal")
        if role == "user":
            self.chat_text.insert("end", "\nYou: ", "user_tag")
        else:
            self.chat_text.insert("end", "\nAI:  ", "ai_tag")
        self.chat_text.insert("end", text + "\n", "msg_text")
        self.chat_text.config(state="disabled")
        self.chat_text.see("end")

    def _chat_set_thinking(self, show):
        if show:
            self.chat_text.config(state="normal")
            self.chat_text.insert("end", "\nAI:  thinking...\n", "thinking")
            self.chat_text.config(state="disabled")
            self.chat_text.see("end")
            self._thinking_mark = self.chat_text.index("end-2l")
        else:
            try:
                self.chat_text.config(state="normal")
                self.chat_text.delete(self._thinking_mark, "end")
                self.chat_text.config(state="disabled")
            except Exception:
                pass

    # AI feature 1: smart category suggestion
    def _on_note_focusout(self, event=None):
        note = self.v_note.get().strip()
        if not note or len(note) < 3:
            return
        if self.v_category.get().strip():
            return
        self.lbl_ai_suggest.config(text="Suggesting category...")
        threading.Thread(target=self._suggest_category, args=(note,), daemon=True).start()

    def _suggest_category(self, note):
        try:
            resp = ai_client.messages.create(
                model="claude-opus-4-8",
                max_tokens=40,
                messages=[{
                    "role": "user",
                    "content": (
                        "A financial transaction has this note: \"" + note + "\"\n"
                        "Reply with ONLY a short category name (1-3 words, e.g. Food, Transport, Rent, "
                        "Entertainment, Health, Utilities, Shopping, Salary). No explanation."
                    )
                }]
            )
            category = resp.content[0].text.strip().strip('"').strip("'")
            self.after(0, self._apply_suggestion, category)
        except Exception as err:
            self.after(0, lambda: self.lbl_ai_suggest.config(text=f"AI error: {err}"))

    def _apply_suggestion(self, category):
        self.lbl_ai_suggest.config(text=f"Suggested: {category}  (click to apply)", cursor="hand2")
        self.lbl_ai_suggest.bind("<Button-1>", lambda e: self._accept_suggestion(category))

    def _accept_suggestion(self, category):
        self.v_category.set(category)
        self.lbl_ai_suggest.config(text=f"Applied: {category}", cursor="")
        self.lbl_ai_suggest.unbind("<Button-1>")

    # AI feature 2: monthly spending insights
    def get_ai_insights(self):
        if not db_fetch_all():
            messagebox.showinfo("No data", "Add some transactions first.")
            return
        if self._ai_busy:
            return
        self._ai_busy = True
        self.btn_insights.config(state="disabled", text="Analysing...")
        data = db_transactions_text()
        threading.Thread(target=self._run_insights, args=(data,), daemon=True).start()

    def _run_insights(self, data):
        try:
            resp = ai_client.messages.create(
                model="claude-opus-4-8",
                max_tokens=600,
                messages=[{
                    "role": "user",
                    "content": (
                        "You are a personal finance advisor. Analyse the following transaction history "
                        "and give concise, actionable insights. Highlight top spending categories, "
                        "any concerning patterns, and 2-3 specific tips to improve finances.\n\n"
                        + data
                    )
                }]
            )
            text_parts = [b.text for b in resp.content if b.type == "text"]
            answer = "\n".join(text_parts).strip()
            self.after(0, self._show_insights, answer)
        except Exception as err:
            self.after(0, self._show_insights, f"Error: {err}")

    def _show_insights(self, text):
        self._ai_busy = False
        self.btn_insights.config(state="normal", text="AI Insights")
        self._chat_append("ai", "Monthly Insights\n\n" + text)
        win = tk.Toplevel(self)
        win.title("AI Monthly Insights")
        win.geometry("640x500")
        win.configure(bg=BG)
        tk.Label(win, text="AI Monthly Insights", bg=BG, fg=ACCENT2, font=FONT_BOLD).pack(pady=(16, 4))
        txt = tk.Text(win, bg=PANEL, fg=TEXT, font=FONT_SMALL, relief="flat", bd=12,
                      wrap="word", padx=8, pady=8)
        txt.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        txt.insert("1.0", text)
        txt.config(state="disabled")

    # AI feature 3: chat assistant
    def send_chat(self):
        msg = self.chat_input.get().strip()
        if not msg or msg == "Ask me about your finances...":
            return
        if self._ai_busy:
            return
        self._ai_busy = True
        self.chat_input.delete(0, "end")
        self.btn_send.config(state="disabled")
        self._chat_append("user", msg)
        self._chat_set_thinking(True)
        self._chat_history.append({"role": "user", "content": msg})
        data = db_transactions_text()
        threading.Thread(target=self._run_chat, args=(data,), daemon=True).start()

    def _run_chat(self, data):
        system_prompt = (
            "You are a helpful personal finance assistant embedded in an Expense Tracker app. "
            "The user's full transaction history is provided below. Answer their questions concisely. "
            "If asked to add or delete transactions, remind them to use the form in the app.\n\n"
            "--- TRANSACTION HISTORY ---\n" + data + "\n--- END ---"
        )
        try:
            resp = ai_client.messages.create(
                model="claude-opus-4-8",
                max_tokens=500,
                system=system_prompt,
                messages=self._chat_history
            )
            text_parts = [b.text for b in resp.content if b.type == "text"]
            answer = "\n".join(text_parts).strip()
            self._chat_history.append({"role": "assistant", "content": answer})
            self.after(0, self._finish_chat, answer)
        except Exception as err:
            self.after(0, self._finish_chat, f"Error: {err}")

    def _finish_chat(self, answer):
        self._chat_set_thinking(False)
        self._chat_append("ai", answer)
        self._ai_busy = False
        self.btn_send.config(state="normal")

    # standard actions
    def add_transaction(self):
        category = self.v_category.get().strip()
        note     = self.v_note.get().strip()
        type_    = self.v_type.get()

        if not category:
            messagebox.showwarning("Missing", "Please enter a category.")
            return
        try:
            amount = float(self.v_amount.get().strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid", "Enter a valid positive amount.")
            return

        db_add(type_, category, amount, note)
        self.v_category.set("")
        self.v_amount.set("")
        self.v_note.set("")
        self.lbl_ai_suggest.config(text="")
        self.refresh_table()
        self.refresh_summary()

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Click a row to select it first.")
            return
        id_ = self.tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Delete", f"Delete transaction #{id_}?"):
            db_delete(id_)
            self.refresh_table()
            self.refresh_summary()

    def export_csv(self):
        rows = db_fetch_all()
        if not rows:
            messagebox.showinfo("Empty", "No transactions to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"expenses_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if not path:
            return
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ID", "Type", "Category", "Amount", "Note", "Date"])
            w.writerows(rows)
        messagebox.showinfo("Exported", f"Saved {len(rows)} records to:\n{path}")

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for row in db_fetch_all():
            tag = "income" if row[1] == "income" else "expense"
            self.tree.insert("", "end", values=(
                row[0], row[1], row[2], f"${row[3]:.2f}", row[4], row[5]
            ), tags=(tag,))
        self.tree.tag_configure("income",  foreground=GREEN)
        self.tree.tag_configure("expense", foreground=RED)

    def refresh_summary(self):
        income, expenses = db_summary()
        balance = income - expenses
        self.lbl_income.config( text=f"Income:  ${income:.2f}")
        self.lbl_expense.config(text=f"Expense: ${expenses:.2f}")
        bal_color = GREEN if balance >= 0 else RED
        self.lbl_balance.config(text=f"Balance: ${balance:.2f}", fg=bal_color)


if __name__ == "__main__":
    app = ExpenseApp()
    app.mainloop()
