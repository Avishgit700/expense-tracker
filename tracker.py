import sqlite3
import csv
import os
from datetime import datetime

DB_FILE = "expenses.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_transaction(type_, category, amount, note=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (type, category, amount, note, date) VALUES (?, ?, ?, ?, ?)",
        (type_, category, round(amount, 2), note, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()
    print(f"  Added {type_}: ${amount:.2f} [{category}]")


def view_all():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, type, category, amount, note, date FROM transactions ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("  No transactions yet.")
        return

    print(f"\n  {'ID':<5} {'Type':<10} {'Category':<15} {'Amount':>8}  {'Note':<20} {'Date'}")
    print("  " + "-" * 75)
    for row in rows:
        print(f"  {row[0]:<5} {row[1]:<10} {row[2]:<15} ${row[3]:>7.2f}  {row[4]:<20} {row[5]}")


def show_summary():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
    income = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
    expenses = c.fetchone()[0] or 0
    conn.close()

    balance = income - expenses
    print(f"\n  Total Income:   ${income:.2f}")
    print(f"  Total Expenses: ${expenses:.2f}")
    print(f"  Balance:        ${balance:.2f}")


def delete_transaction(id_):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?", (id_,))
    if c.rowcount == 0:
        print(f"  No transaction with ID {id_}.")
    else:
        print(f"  Deleted transaction #{id_}.")
    conn.commit()
    conn.close()


def export_csv():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, type, category, amount, note, date FROM transactions ORDER BY id")
    rows = c.fetchall()
    conn.close()

    filename = f"expenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Type", "Category", "Amount", "Note", "Date"])
        writer.writerows(rows)
    print(f"  Exported {len(rows)} records to {filename}")


def get_input(prompt, type_fn=str, valid=None):
    while True:
        val = input(prompt).strip()
        try:
            val = type_fn(val)
            if valid and val not in valid:
                print(f"  Choose from: {', '.join(valid)}")
                continue
            return val
        except ValueError:
            print("  Invalid input, try again.")


def menu():
    print("\n" + "=" * 40)
    print("   EXPENSE TRACKER")
    print("=" * 40)
    print("  1. Add income")
    print("  2. Add expense")
    print("  3. View all transactions")
    print("  4. Summary (balance)")
    print("  5. Delete a transaction")
    print("  6. Export to CSV")
    print("  0. Quit")
    print("=" * 40)
    return get_input("  Choose: ", str, ["0","1","2","3","4","5","6"])


def main():
    init_db()
    print("\n  Welcome to Expense Tracker!")

    while True:
        choice = menu()

        if choice == "1":
            category = get_input("  Category (e.g. salary, freelance): ")
            amount = get_input("  Amount: $", float)
            note = input("  Note (optional): ").strip()
            add_transaction("income", category, amount, note)

        elif choice == "2":
            category = get_input("  Category (e.g. food, rent, transport): ")
            amount = get_input("  Amount: $", float)
            note = input("  Note (optional): ").strip()
            add_transaction("expense", category, amount, note)

        elif choice == "3":
            view_all()

        elif choice == "4":
            show_summary()

        elif choice == "5":
            view_all()
            id_ = get_input("\n  Enter ID to delete: ", int)
            delete_transaction(id_)

        elif choice == "6":
            export_csv()

        elif choice == "0":
            print("\n  Bye!\n")
            break


if __name__ == "__main__":
    main()
