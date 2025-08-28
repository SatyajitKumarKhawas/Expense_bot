import sqlite3

DB_NAME = "expenses.db"

def migrate():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Check if column already exists
    c.execute("PRAGMA table_info(expenses)")
    columns = [row[1] for row in c.fetchall()]
    if "user_id" not in columns:
        print("➡️ Adding user_id column to expenses table...")
        c.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER DEFAULT 1")
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id)")
        conn.commit()
        print("✅ Migration complete: user_id added")
    else:
        print("✔️ user_id column already exists")

    conn.close()

if __name__ == "__main__":
    migrate()
