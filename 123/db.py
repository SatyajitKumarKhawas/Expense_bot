import sqlite3
from datetime import datetime, timedelta
import calendar

DB_NAME = "expenses.db"

def init_db():
    """Initialize the database with enhanced schema"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Check if expenses table exists and has user_id column
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expenses'")
    expenses_table_exists = c.fetchone() is not None
    
    if expenses_table_exists:
        # Check if user_id column exists
        c.execute("PRAGMA table_info(expenses)")
        columns = [row[1] for row in c.fetchall()]
        has_user_id = 'user_id' in columns
        
        if not has_user_id:
            print("⚠️  Database needs migration to support multi-user functionality!")
            print("Please run: python migrate_db.py")
            conn.close()
            return
    
    # Create main expenses table with user_id field
    c.execute('''CREATE TABLE IF NOT EXISTS expenses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  description TEXT,
                  date TEXT NOT NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  location TEXT,
                  payment_method TEXT,
                  tags TEXT,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Create categories table for better organization
    c.execute('''CREATE TABLE IF NOT EXISTS categories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  color TEXT,
                  icon TEXT,
                  budget_limit REAL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create monthly budgets table
    c.execute('''CREATE TABLE IF NOT EXISTS monthly_budgets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  year INTEGER NOT NULL,
                  month INTEGER NOT NULL,
                  category TEXT,
                  budget_amount REAL NOT NULL,
                  UNIQUE(year, month, category))''')
    
    # Insert default categories if they don't exist
    default_categories = [
        ('food', '#FF6B6B', '🍽️'),
        ('transportation', '#4ECDC4', '🚗'),
        ('entertainment', '#45B7D1', '🎬'),
        ('shopping', '#96CEB4', '🛍️'),
        ('groceries', '#FFEAA7', '🛒'),
        ('dining', '#DDA0DD', '🍴'),
        ('utilities', '#98D8C8', '💡'),
        ('healthcare', '#F7DC6F', '🏥'),
        ('education', '#BB8FCE', '📚'),
        ('other', '#BDC3C7', '📋')
    ]
    
    for category, color, icon in default_categories:
        c.execute("INSERT OR IGNORE INTO categories (name, color, icon) VALUES (?, ?, ?)",
                  (category, color, icon))
    
    # Create indexes for better performance (only if expenses table has user_id)
    if expenses_table_exists and 'user_id' in columns:
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_amount ON expenses(amount)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id)")
    elif not expenses_table_exists:
        # New database, safe to create indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_amount ON expenses(amount)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id)")
    
    conn.commit()
    conn.close()

def add_expense(user_id, amount, category, description, date=None, location=None, payment_method=None, tags=None):
    """Add a new expense with enhanced fields"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Normalize category (lowercase, handle common variations)
    category = normalize_category(category.lower())
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""INSERT INTO expenses (user_id, amount, category, description, date, location, payment_method, tags) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (user_id, amount, category, description, date, location, payment_method, tags))
    conn.commit()
    conn.close()

def normalize_category(category):
    """Normalize category names to standard categories"""
    category_mapping = {
        # Food related
        'food': 'food',
        'meal': 'food',
        'snack': 'food',
        'coffee': 'food',
        'tea': 'food',
        'breakfast': 'food',
        'lunch': 'food',
        'dinner': 'dining',
        'restaurant': 'dining',
        'eating out': 'dining',
        'dine': 'dining',
        
        # Shopping
        'shopping': 'shopping',
        'clothes': 'shopping',
        'clothing': 'shopping',
        'accessories': 'shopping',
        'electronics': 'shopping',
        
        # Transportation
        'transport': 'transportation',
        'transportation': 'transportation',
        'fuel': 'transportation',
        'gas': 'transportation',
        'petrol': 'transportation',
        'uber': 'transportation',
        'taxi': 'transportation',
        'bus': 'transportation',
        'train': 'transportation',
        'metro': 'transportation',
        
        # Groceries
        'grocery': 'groceries',
        'groceries': 'groceries',
        'vegetables': 'groceries',
        'fruits': 'groceries',
        'milk': 'groceries',
        
        # Entertainment
        'entertainment': 'entertainment',
        'movie': 'entertainment',
        'cinema': 'entertainment',
        'game': 'entertainment',
        'games': 'entertainment',
        'music': 'entertainment',
        
        # Utilities
        'utility': 'utilities',
        'utilities': 'utilities',
        'electricity': 'utilities',
        'water': 'utilities',
        'internet': 'utilities',
        'phone': 'utilities',
        'mobile': 'utilities',
        
        # Healthcare
        'health': 'healthcare',
        'healthcare': 'healthcare',
        'medical': 'healthcare',
        'medicine': 'healthcare',
        'doctor': 'healthcare',
        'hospital': 'healthcare',
        
        # Education
        'education': 'education',
        'book': 'education',
        'books': 'education',
        'course': 'education',
        'training': 'education',
    }
    
    return category_mapping.get(category, category)

def query_expenses(query, user_id=None):
    """Execute a query on the expenses database with optional user filtering"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # If user_id is provided and query doesn't already have WHERE clause for user_id
        if user_id and "user_id" not in query.lower():
            if "WHERE" in query.upper():
                query = query.replace("WHERE", f"WHERE user_id = {user_id} AND", 1)
            else:
                # Add WHERE clause before ORDER BY or LIMIT if they exist
                if "ORDER BY" in query.upper():
                    query = query.replace("ORDER BY", f"WHERE user_id = {user_id} ORDER BY", 1)
                elif "LIMIT" in query.upper():
                    query = query.replace("LIMIT", f"WHERE user_id = {user_id} LIMIT", 1)
                elif "GROUP BY" in query.upper():
                    query = query.replace("GROUP BY", f"WHERE user_id = {user_id} GROUP BY", 1)
                else:
                    query = f"{query} WHERE user_id = {user_id}"
        
        c.execute(query)
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        conn.close()
        raise e

def get_expense_summary(user_id, period='current_month'):
    """Get expense summary for different time periods"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    if period == 'current_month':
        query = "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
    elif period == 'last_month':
        query = "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', date('now', '-1 month'))"
    elif period == 'current_week':
        query = "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date >= date('now', '-7 days')"
    elif period == 'today':
        query = "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date = date('now')"
    else:
        query = "SELECT SUM(amount) FROM expenses WHERE user_id = ?"
    
    c.execute(query, (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_category_breakdown(user_id, period='current_month', limit=10):
    """Get spending breakdown by category"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    if period == 'current_month':
        date_condition = "strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
    elif period == 'last_month':
        date_condition = "strftime('%Y-%m', date) = strftime('%Y-%m', date('now', '-1 month'))"
    elif period == 'current_week':
        date_condition = "date >= date('now', '-7 days')"
    elif period == 'all_time':
        date_condition = "1=1"
    else:
        date_condition = "1=1"
    
    query = f"""SELECT category, SUM(amount) as total 
                FROM expenses 
                WHERE user_id = ? AND {date_condition}
                GROUP BY category 
                ORDER BY total DESC 
                LIMIT {limit}"""
    
    c.execute(query, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_daily_expenses(days=30):
    """Get daily expense totals for the last N days"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    query = """SELECT date, SUM(amount) as total 
               FROM expenses 
               WHERE date >= date('now', '-{} days')
               GROUP BY date 
               ORDER BY date""".format(days)
    
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    return rows

def get_spending_trends():
    """Get spending trends and insights"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Current month vs last month
    current_month = c.execute("""SELECT SUM(amount) FROM expenses 
                                WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')""").fetchone()[0] or 0
    
    last_month = c.execute("""SELECT SUM(amount) FROM expenses 
                             WHERE strftime('%Y-%m', date) = strftime('%Y-%m', date('now', '-1 month'))""").fetchone()[0] or 0
    
    # Average daily spending
    avg_daily = c.execute("""SELECT AVG(daily_total) FROM (
                            SELECT date, SUM(amount) as daily_total 
                            FROM expenses 
                            WHERE date >= date('now', '-30 days')
                            GROUP BY date
                           )""").fetchone()[0] or 0
    
    # Most expensive day
    expensive_day = c.execute("""SELECT date, SUM(amount) as total 
                                FROM expenses 
                                GROUP BY date 
                                ORDER BY total DESC 
                                LIMIT 1""").fetchone()
    
    conn.close()
    
    return {
        'current_month': current_month,
        'last_month': last_month,
        'change_percentage': ((current_month - last_month) / last_month * 100) if last_month > 0 else 0,
        'avg_daily': avg_daily,
        'most_expensive_day': expensive_day
    }

def search_expenses(search_term, limit=50):
    """Search expenses by description, category, or amount"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    query = """SELECT amount, category, description, date 
               FROM expenses 
               WHERE description LIKE ? OR category LIKE ? 
               ORDER BY date DESC 
               LIMIT ?"""
    
    search_pattern = f"%{search_term}%"
    c.execute(query, (search_pattern, search_pattern, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_budget_status(category=None):
    """Get budget status for categories"""
    # This would require implementing budget functionality
    # For now, return a placeholder
    return {"status": "No budgets set"}

def delete_expense(expense_id):
    """Delete an expense by ID"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted > 0

def update_expense(expense_id, amount=None, category=None, description=None, date=None):
    """Update an existing expense"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    updates = []
    params = []
    
    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)
    if category is not None:
        updates.append("category = ?")
        params.append(normalize_category(category.lower()))
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if date is not None:
        updates.append("date = ?")
        params.append(date)
    
    if updates:
        query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
        params.append(expense_id)
        c.execute(query, params)
        updated = c.rowcount
        conn.commit()
    else:
        updated = 0
    
    conn.close()
    return updated > 0