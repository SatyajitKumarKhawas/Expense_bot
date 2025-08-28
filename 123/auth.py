import sqlite3
import hashlib
import secrets
import streamlit as st
from datetime import datetime, timedelta
import re

DB_NAME = "expenses.db"

def init_auth_db():
    """Initialize authentication database tables"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  salt TEXT NOT NULL,
                  full_name TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  last_login DATETIME,
                  is_active BOOLEAN DEFAULT 1,
                  profile_picture TEXT,
                  currency_preference TEXT DEFAULT '₹',
                  timezone TEXT DEFAULT 'Asia/Kolkata')''')
    
    # User sessions table for session management
    c.execute('''CREATE TABLE IF NOT EXISTS user_sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  session_token TEXT UNIQUE NOT NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  expires_at DATETIME NOT NULL,
                  is_active BOOLEAN DEFAULT 1,
                  ip_address TEXT,
                  user_agent TEXT,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Password reset tokens
    c.execute('''CREATE TABLE IF NOT EXISTS password_reset_tokens
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  token TEXT UNIQUE NOT NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  expires_at DATETIME NOT NULL,
                  used BOOLEAN DEFAULT 0,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # User preferences
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  preference_key TEXT NOT NULL,
                  preference_value TEXT NOT NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(user_id, preference_key),
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Create indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)")
    
    conn.commit()
    conn.close()

def hash_password(password, salt=None):
    """Hash a password with salt"""
    if salt is None:
        salt = secrets.token_hex(32)
    
    # Combine password and salt
    password_salt = password + salt
    
    # Hash using SHA-256
    password_hash = hashlib.sha256(password_salt.encode()).hexdigest()
    
    return password_hash, salt

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def register_user(username, email, password, full_name):
    """Register a new user"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Validate input
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if not validate_email(email):
            return False, "Please enter a valid email address"
        
        is_valid, password_msg = validate_password(password)
        if not is_valid:
            return False, password_msg
        
        # Check if user already exists
        c.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if c.fetchone():
            return False, "Username or email already exists"
        
        # Hash password
        password_hash, salt = hash_password(password)
        
        # Insert user
        c.execute("""INSERT INTO users (username, email, password_hash, salt, full_name) 
                     VALUES (?, ?, ?, ?, ?)""",
                  (username, email, password_hash, salt, full_name))
        
        user_id = c.lastrowid
        conn.commit()
        return True, f"User registered successfully with ID: {user_id}"
        
    except sqlite3.IntegrityError as e:
        return False, "Username or email already exists"
    except Exception as e:
        return False, f"Registration failed: {str(e)}"
    finally:
        conn.close()

def authenticate_user(username_or_email, password):
    """Authenticate user login"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Find user by username or email
        c.execute("""SELECT id, username, email, password_hash, salt, full_name, is_active 
                     FROM users 
                     WHERE (username = ? OR email = ?) AND is_active = 1""", 
                  (username_or_email, username_or_email))
        
        user = c.fetchone()
        if not user:
            return False, None, "Invalid username/email or password"
        
        user_id, username, email, stored_hash, salt, full_name, is_active = user
        
        # Verify password
        password_hash, _ = hash_password(password, salt)
        
        if password_hash != stored_hash:
            return False, None, "Invalid username/email or password"
        
        # Update last login
        c.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        conn.commit()
        
        user_info = {
            'id': user_id,
            'username': username,
            'email': email,
            'full_name': full_name
        }
        
        return True, user_info, "Login successful"
        
    except Exception as e:
        return False, None, f"Authentication failed: {str(e)}"
    finally:
        conn.close()

def create_session(user_id, ip_address=None, user_agent=None):
    """Create a new user session"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=30)  # 30-day expiry
        
        # Insert session
        c.execute("""INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                     VALUES (?, ?, ?, ?, ?)""",
                  (user_id, session_token, expires_at, ip_address, user_agent))
        
        conn.commit()
        return session_token
        
    except Exception as e:
        return None
    finally:
        conn.close()

def validate_session(session_token):
    """Validate user session"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute("""SELECT s.user_id, u.username, u.email, u.full_name 
                     FROM user_sessions s 
                     JOIN users u ON s.user_id = u.id 
                     WHERE s.session_token = ? AND s.is_active = 1 
                     AND s.expires_at > CURRENT_TIMESTAMP""", (session_token,))
        
        result = c.fetchone()
        if result:
            user_id, username, email, full_name = result
            return True, {
                'id': user_id,
                'username': username,
                'email': email,
                'full_name': full_name
            }
        
        return False, None
        
    except Exception as e:
        return False, None
    finally:
        conn.close()

def logout_user(session_token):
    """Logout user by deactivating session"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute("UPDATE user_sessions SET is_active = 0 WHERE session_token = ?", (session_token,))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def get_user_preferences(user_id):
    """Get user preferences"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute("SELECT preference_key, preference_value FROM user_preferences WHERE user_id = ?", (user_id,))
        preferences = dict(c.fetchall())
        return preferences
    except Exception as e:
        return {}
    finally:
        conn.close()

def set_user_preference(user_id, key, value):
    """Set user preference"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute("""INSERT OR REPLACE INTO user_preferences (user_id, preference_key, preference_value, updated_at)
                     VALUES (?, ?, ?, CURRENT_TIMESTAMP)""", (user_id, key, value))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def update_user_profile(user_id, full_name=None, email=None, currency_preference=None):
    """Update user profile"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        updates = []
        params = []
        
        if full_name:
            updates.append("full_name = ?")
            params.append(full_name)
        
        if email:
            if validate_email(email):
                updates.append("email = ?")
                params.append(email)
            else:
                return False, "Invalid email format"
        
        if currency_preference:
            updates.append("currency_preference = ?")
            params.append(currency_preference)
        
        if updates:
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            params.append(user_id)
            c.execute(query, params)
            conn.commit()
            return True, "Profile updated successfully"
        
        return False, "No updates provided"
        
    except sqlite3.IntegrityError:
        return False, "Email already exists"
    except Exception as e:
        return False, f"Update failed: {str(e)}"
    finally:
        conn.close()

def change_password(user_id, current_password, new_password):
    """Change user password"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Get current password details
        c.execute("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,))
        result = c.fetchone()
        
        if not result:
            return False, "User not found"
        
        stored_hash, salt = result
        
        # Verify current password
        current_hash, _ = hash_password(current_password, salt)
        if current_hash != stored_hash:
            return False, "Current password is incorrect"
        
        # Validate new password
        is_valid, password_msg = validate_password(new_password)
        if not is_valid:
            return False, password_msg
        
        # Hash new password
        new_hash, new_salt = hash_password(new_password)
        
        # Update password
        c.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", 
                  (new_hash, new_salt, user_id))
        conn.commit()
        
        return True, "Password changed successfully"
        
    except Exception as e:
        return False, f"Password change failed: {str(e)}"
    finally:
        conn.close()

def get_user_stats(user_id):
    """Get user statistics"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Get user info
        c.execute("SELECT username, full_name, created_at, last_login FROM users WHERE id = ?", (user_id,))
        user_info = c.fetchone()
        
        # Get expense count
        c.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,))
        expense_count = c.fetchone()[0]
        
        # Get total spent
        c.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (user_id,))
        total_spent = c.fetchone()[0] or 0
        
        # Get first expense date
        c.execute("SELECT MIN(date) FROM expenses WHERE user_id = ?", (user_id,))
        first_expense = c.fetchone()[0]
        
        return {
            'username': user_info[0] if user_info else None,
            'full_name': user_info[1] if user_info else None,
            'member_since': user_info[2] if user_info else None,
            'last_login': user_info[3] if user_info else None,
            'total_expenses': expense_count,
            'total_spent': total_spent,
            'first_expense_date': first_expense
        }
        
    except Exception as e:
        return None
    finally:
        conn.close()