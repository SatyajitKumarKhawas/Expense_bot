import streamlit as st
import google.generativeai as genai
import sqlite3
import re
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db import init_db, add_expense, query_expenses, get_expense_summary, get_category_breakdown
from auth import (init_auth_db, register_user, authenticate_user, create_session, 
                  validate_session, logout_user, get_user_stats, update_user_profile, 
                  change_password, get_user_preferences, set_user_preference)
from datetime import datetime, timedelta
import calendar

# 🔹 Configure Gemini
genai.configure(api_key="AIzaSyCXSeedyFs2z1QNQ58N7tIRkGJNJrPzNd4")
model = genai.GenerativeModel("gemini-1.5-flash")

# 🔹 Page Config
st.set_page_config(
    page_title="💰 Smart Expense Assistant",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔹 Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .auth-container {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        border: 1px solid #e9ecef;
        max-width: 500px;
        margin: 0 auto;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .expense-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .user-profile {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .success-msg {
        background: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    
    .error-msg {
        background: #f8d7da;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
    
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .login-tab {
        background: #ffffff;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 🔹 Initialize Databases
try:
    init_db()
    init_auth_db()
except Exception as e:
    st.error(f"⚠️ Database initialization error: {str(e)}")
    st.error("Please run the migration script: `python migrate_db.py`")
    st.stop()

# 🔹 Authentication Functions
def show_auth_page():
    """Show authentication page"""
    st.markdown("""
    <div class="main-header">
        <h1>💰 Smart Expense Assistant</h1>
        <p>Your AI-powered personal finance companion</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for login and register
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
        
        with tab1:
            st.markdown('<div class="login-tab">', unsafe_allow_html=True)
            st.subheader("Welcome Back!")
            
            with st.form("login_form"):
                username_or_email = st.text_input("Username or Email", placeholder="Enter your username or email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    login_btn = st.form_submit_button("🔑 Login", use_container_width=True)
                with col_b:
                    forgot_password = st.form_submit_button("🔄 Forgot Password", use_container_width=True)
                
                if login_btn and username_or_email and password:
                    success, user_info, message = authenticate_user(username_or_email, password)
                    
                    if success:
                        # Create session
                        session_token = create_session(user_info['id'])
                        if session_token:
                            st.session_state.user = user_info
                            st.session_state.session_token = session_token
                            st.session_state.authenticated = True
                            st.success(f"Welcome back, {user_info['full_name']}!")
                            st.rerun()
                        else:
                            st.error("Failed to create session. Please try again.")
                    else:
                        st.error(message)
                
                elif login_btn:
                    st.warning("Please fill in all fields")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            st.markdown('<div class="login-tab">', unsafe_allow_html=True)
            st.subheader("Create Your Account")
            
            with st.form("register_form"):
                full_name = st.text_input("Full Name", placeholder="Enter your full name")
                username = st.text_input("Username", placeholder="Choose a username")
                email = st.text_input("Email", placeholder="Enter your email address")
                password = st.text_input("Password", type="password", placeholder="Create a strong password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                
                # Password requirements
                st.caption("Password must contain: 8+ characters, uppercase, lowercase, number, and special character")
                
                terms_agreed = st.checkbox("I agree to the Terms of Service and Privacy Policy")
                
                register_btn = st.form_submit_button("📝 Create Account", use_container_width=True)
                
                if register_btn:
                    if not all([full_name, username, email, password, confirm_password]):
                        st.warning("Please fill in all fields")
                    elif password != confirm_password:
                        st.error("Passwords don't match")
                    elif not terms_agreed:
                        st.warning("Please agree to the terms and conditions")
                    else:
                        success, message = register_user(username, email, password, full_name)
                        
                        if success:
                            st.success("Account created successfully! Please login to continue.")
                            st.balloons()
                        else:
                            st.error(message)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_main_app():
    """Show main application for authenticated users"""
    user = st.session_state.user
    
    # 🔹 Header with user info
    st.markdown(f"""
    <div class="main-header">
        <h1>💰 Smart Expense Assistant</h1>
        <p>Welcome back, <strong>{user['full_name']}</strong>! 👋</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 🔹 Sidebar with Dashboard
    with st.sidebar:
        # User profile section
        st.markdown(f"""
        <div class="user-profile">
            <h3>👤 {user['full_name']}</h3>
            <p>@{user['username']}</p>
            <p>📧 {user['email']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Profile management buttons
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if st.button("⚙️ Profile", use_container_width=True):
                st.session_state.show_profile = True
        with col_p2:
            if st.button("🚪 Logout", use_container_width=True):
                logout_user(st.session_state.session_token)
                st.session_state.clear()
                st.rerun()
        
        st.divider()
        
        st.header("📊 Financial Dashboard")
        
        # Get current month summary
        summary = get_expense_summary(user['id'])
        if summary:
            total_spent = summary[0] if summary[0] else 0
            st.metric("💸 This Month's Spending", f"₹{total_spent:,.2f}")
        
        # Category breakdown
        category_data = get_category_breakdown(user['id'])
        if category_data:
            df_categories = pd.DataFrame(category_data, columns=['Category', 'Amount'])
            
            # Pie chart for categories
            fig = px.pie(df_categories, values='Amount', names='Category', 
                        title="Spending by Category")
            fig.update_layout(height=300, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
            
            # Top spending categories
            st.subheader("🏆 Top Categories")
            for i, (category, amount) in enumerate(category_data[:3], 1):
                st.write(f"{i}. **{category}**: ₹{amount:,.2f}")
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        if st.button("📊 View All Expenses", use_container_width=True):
            st.session_state.show_all_expenses = True
        
        if st.button("📈 Analytics", use_container_width=True):
            st.session_state.show_analytics = True
        
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Show profile management if requested
    if st.session_state.get("show_profile", False):
        show_profile_management()
        return
    
    # Show analytics if requested
    if st.session_state.get("show_analytics", False):
        show_analytics_dashboard()
        return
    
    # 🔹 Main Chat Interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("💬 Chat with your Finance Assistant")
        
        # Initialize chat history with context
        if "messages" not in st.session_state:
            st.session_state.messages = []
            # Add personalized welcome message
            welcome_msg = f"""👋 Hello {user['full_name']}! I'm your Smart Expense Assistant. I can help you:

• **Track expenses**: "I spent ₹500 on groceries" or "₹200 for coffee with friends"
• **Query spending**: "How much did I spend on food this month?"
• **Analyze patterns**: "Show me my top spending categories"
• **Budget insights**: "Am I overspending on entertainment?"

Just type naturally - I understand context and can handle multiple expenses at once!"""
            
            st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

        # Display chat messages
        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Enhanced user input with context
        if user_input := st.chat_input("💭 Tell me about your expenses or ask me anything..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)

            # Build context from recent messages
            recent_context = ""
            if len(st.session_state.messages) > 1:
                recent_msgs = st.session_state.messages[-6:]  # Last 6 messages for context
                for msg in recent_msgs:
                    if msg["role"] == "user":
                        recent_context += f"User: {msg['content']}\n"

            # Get current date info for better context
            today = datetime.now()
            current_date = today.strftime("%Y-%m-%d")
            current_month = today.strftime("%B %Y")
            yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Enhanced prompt with context and examples
            enhanced_prompt = f"""
            You are an advanced expense management AI assistant with full context awareness.
            
            CONTEXT INFORMATION:
            - User: {user['full_name']} (@{user['username']})
            - Today's date: {current_date}
            - Yesterday's date: {yesterday}
            - Current month: {current_month}
            
            RECENT CONVERSATION CONTEXT:
            {recent_context}
            
            CURRENT USER INPUT: {user_input}
            
            TASK: Extract structured JSON from the user input. Consider the conversation context.
            
            SUPPORTED INTENTS:
            1. add_expense - Adding new expenses
            2. query_expense - Querying existing expenses
            3. general_query - General financial questions/analysis
            
            ENHANCED PARSING RULES:
            - Handle relative dates: "yesterday", "last week", "this month", "2 days ago"
            - Infer categories smartly: "coffee" → "food", "uber" → "transportation"
            - Handle multiple currencies and formats
            - Extract locations and people when mentioned
            - Context-aware descriptions
            
            EXAMPLES:
            
            Input: "I grabbed coffee with Sarah yesterday for ₹350"
            Output: [{{"intent": "add_expense", "amount": 350, "category": "food", "description": "Coffee with Sarah", "date": "{yesterday}"}}]
            
            Input: "Spent 2000 on groceries, 500 on fuel, and 1200 eating out"
            Output: [
                {{"intent": "add_expense", "amount": 2000, "category": "groceries", "description": "Groceries", "date": "{current_date}"}},
                {{"intent": "add_expense", "amount": 500, "category": "transportation", "description": "Fuel", "date": "{current_date}"}},
                {{"intent": "add_expense", "amount": 1200, "category": "dining", "description": "Eating out", "date": "{current_date}"}}
            ]
            
            Input: "How much have I spent on food this month?"
            Output: [{{"intent": "query_expense", "query": "SELECT SUM(amount) FROM expenses WHERE category IN ('food', 'groceries', 'dining', 'restaurants') AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')", "description": "Total food spending this month"}}]
            
            Input: "Show me my biggest expenses this week"
            Output: [{{"intent": "query_expense", "query": "SELECT amount, category, description, date FROM expenses WHERE date >= date('now', '-7 days') ORDER BY amount DESC LIMIT 5", "description": "Top expenses this week"}}]
            
            Input: "Am I overspending on entertainment?"
            Output: [{{"intent": "general_query", "analysis_type": "category_analysis", "category": "entertainment", "query": "SELECT AVG(amount) as avg_spending, SUM(amount) as total, COUNT(*) as count FROM expenses WHERE category='entertainment' AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"}}]
            
            Return ONLY valid JSON. No explanations or additional text.
            """

            try:
                # Generate response with context
                response = model.generate_content(enhanced_prompt)
                parsed = response.text.strip()

                # Clean and extract JSON
                match = re.search(r"(\[.*\]|\{.*\})", parsed, re.DOTALL)
                if match:
                    parsed = match.group(0)

                # Process the parsed data
                data = json.loads(parsed)
                if isinstance(data, dict):
                    data = [data]

                replies = []
                charts_data = []

                for item in data:
                    if item["intent"] == "add_expense":
                        # Add expense to database with user_id
                        add_expense(
                            user['id'],
                            item["amount"],
                            item["category"],
                            item.get("description", ""),
                            item.get("date", current_date),
                        )
                        replies.append(f"✅ **Added**: ₹{item['amount']:,.2f} for {item['category']} - {item.get('description', '')}")

                    elif item["intent"] == "query_expense":
                        # Execute query with user filtering
                        try:
                            rows = query_expenses(item["query"], user['id'])
                            if rows:
                                if len(rows) == 1 and len(rows[0]) == 1:
                                    # Single result (like SUM)
                                    result = rows[0][0] if rows[0][0] else 0
                                    replies.append(f"📊 **Result**: ₹{result:,.2f}")
                                else:
                                    # Multiple results
                                    replies.append(f"📊 **Found {len(rows)} records:**")
                                    for row in rows[:10]:  # Limit to 10 results
                                        if len(row) >= 4:
                                            replies.append(f"• ₹{row[0]:,.2f} - {row[1]} ({row[2]}) on {row[3]}")
                                        else:
                                            replies.append(f"• {row}")
                            else:
                                replies.append("❌ No records found for your query.")
                        except Exception as query_error:
                            replies.append(f"❌ Query error: {str(query_error)}")

                    elif item["intent"] == "general_query":
                        # Handle general analysis
                        analysis_type = item.get("analysis_type", "general")
                        if analysis_type == "category_analysis":
                            try:
                                rows = query_expenses(item["query"], user['id'])
                                if rows and rows[0]:
                                    avg_spending, total, count = rows[0]
                                    category = item.get("category", "that category")
                                    replies.append(f"📈 **{category.title()} Analysis:**")
                                    replies.append(f"• Total this month: ₹{total:,.2f}")
                                    replies.append(f"• Average per transaction: ₹{avg_spending:,.2f}")
                                    replies.append(f"• Number of transactions: {count}")
                            except:
                                replies.append("❌ Unable to analyze that category.")

                    else:
                        replies.append("🤔 I'm not sure how to help with that. Try asking about expenses or spending patterns!")

                # Combine all replies
                final_reply = "\n\n".join(replies)

                # Add contextual suggestions
                suggestions = []
                if any(item["intent"] == "add_expense" for item in data):
                    suggestions.append("💡 **Tip**: You can add multiple expenses at once!")
                    # Check if spending is high today
                    today_total = query_expenses(f"SELECT SUM(amount) FROM expenses WHERE date = '{current_date}'", user['id'])
                    if today_total and today_total[0][0] and today_total[0][0] > 2000:
                        suggestions.append("⚠️ **Notice**: You've spent quite a bit today. Consider reviewing your budget!")

                if suggestions:
                    final_reply += "\n\n" + "\n".join(suggestions)

            except json.JSONDecodeError as e:
                final_reply = f"❌ **Error**: I couldn't understand that format. Could you try rephrasing? (JSON Error: {str(e)})"
            except Exception as e:
                final_reply = f"❌ **Error**: Something went wrong: {str(e)}"

            # Add assistant response
            st.session_state.messages.append({"role": "assistant", "content": final_reply})
            with st.chat_message("assistant"):
                st.write(final_reply)

            # Update sidebar metrics after new expenses
            st.rerun()

    # 🔹 Right column - Recent Activity & Insights
    with col2:
        st.header("🔍 Recent Activity")
        
        # Show recent expenses
        recent_expenses = query_expenses("SELECT amount, category, description, date FROM expenses ORDER BY date DESC, id DESC LIMIT 5", user['id'])
        
        if recent_expenses:
            for expense in recent_expenses:
                amount, category, description, date = expense
                st.markdown(f"""
                <div class="expense-card">
                    <strong>₹{amount:,.2f}</strong> - {category}<br>
                    <small>{description} • {date}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No expenses recorded yet. Start chatting to add some!")
        
        # Quick stats
        st.header("📈 Quick Stats")
        
        # This week vs last week
        this_week_query = "SELECT SUM(amount) FROM expenses WHERE date >= date('now', '-7 days')"
        last_week_query = "SELECT SUM(amount) FROM expenses WHERE date >= date('now', '-14 days') AND date < date('now', '-7 days')"
        
        this_week = query_expenses(this_week_query, user['id'])
        last_week = query_expenses(last_week_query, user['id'])
        
        this_week_total = this_week[0][0] if this_week and this_week[0][0] else 0
        last_week_total = last_week[0][0] if last_week and last_week[0][0] else 0
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("This Week", f"₹{this_week_total:,.0f}")
        with col_b:
            change = this_week_total - last_week_total
            st.metric("vs Last Week", f"₹{last_week_total:,.0f}", f"₹{change:+,.0f}")

def show_profile_management():
    """Show profile management page"""
    user = st.session_state.user
    
    if st.button("← Back to Dashboard"):
        st.session_state.show_profile = False
        st.rerun()
    
    st.header("⚙️ Profile Management")
    
    # Get user statistics
    stats = get_user_stats(user['id'])
    
    if stats:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 Total Expenses", stats['total_expenses'])
        with col2:
            st.metric("💰 Total Spent", f"₹{stats['total_spent']:,.2f}")
        with col3:
            if stats['member_since']:
                member_since = datetime.strptime(stats['member_since'], "%Y-%m-%d %H:%M:%S").strftime("%b %Y")
                st.metric("📅 Member Since", member_since)
    
    # Profile update form
    st.subheader("Update Profile")
    
    with st.form("profile_update"):
        new_full_name = st.text_input("Full Name", value=user.get('full_name', ''))
        new_email = st.text_input("Email", value=user.get('email', ''))
        
        currency_options = ["₹", "$", "€", "£", "¥"]
        currency = st.selectbox("Currency Preference", currency_options)
        
        if st.form_submit_button("Update Profile"):
            success, message = update_user_profile(user['id'], new_full_name, new_email, currency)
            if success:
                st.success(message)
                # Update session user info
                st.session_state.user['full_name'] = new_full_name
                st.session_state.user['email'] = new_email
                st.rerun()
            else:
                st.error(message)
    
    st.divider()
    
    # Password change form
    st.subheader("Change Password")
    
    with st.form("password_change"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")
        
        if st.form_submit_button("Change Password"):
            if new_password != confirm_new_password:
                st.error("New passwords don't match")
            elif len(new_password) < 8:
                st.error("New password must be at least 8 characters long")
            else:
                success, message = change_password(user['id'], current_password, new_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)

def show_analytics_dashboard():
    """Show detailed analytics dashboard"""
    user = st.session_state.user
    
    if st.button("← Back to Dashboard"):
        st.session_state.show_analytics = False
        st.rerun()
    
    st.header("📈 Analytics Dashboard")
    
    # Monthly spending trend
    monthly_data = query_expenses("""
        SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
        FROM expenses 
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
        LIMIT 12
    """, user['id'])
    
    if monthly_data:
        df_monthly = pd.DataFrame(monthly_data, columns=['Month', 'Amount'])
        df_monthly = df_monthly.sort_values('Month')
        
        fig_line = px.line(df_monthly, x='Month', y='Amount', 
                          title="Monthly Spending Trend",
                          markers=True)
        fig_line.update_layout(height=400)
        st.plotly_chart(fig_line, use_container_width=True)
    
    # Category comparison
    col1, col2 = st.columns(2)
    
    with col1:
        current_month_categories = get_category_breakdown(user['id'], 'current_month')
        if current_month_categories:
            df_current = pd.DataFrame(current_month_categories, columns=['Category', 'Amount'])
            fig_bar = px.bar(df_current, x='Category', y='Amount', 
                           title="Current Month by Category")
            fig_bar.update_xaxis(tickangle=45)
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        last_month_categories = get_category_breakdown(user['id'], 'last_month')
        if last_month_categories:
            df_last = pd.DataFrame(last_month_categories, columns=['Category', 'Amount'])
            fig_pie = px.pie(df_last, values='Amount', names='Category', 
                           title="Last Month Distribution")
            st.plotly_chart(fig_pie, use_container_width=True)

# 🔹 Main Application Logic
def main():
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if 'session_token' not in st.session_state:
        st.session_state.session_token = None
    
    # Check if user has valid session
    if st.session_state.authenticated and st.session_state.session_token:
        valid, user_info = validate_session(st.session_state.session_token)
        if valid:
            st.session_state.user = user_info
            show_main_app()
        else:
            # Session expired
            st.session_state.clear()
            st.error("Your session has expired. Please login again.")
            show_auth_page()
    else:
        show_auth_page()
    
    # 🔹 Show all expenses table (if requested)
    if st.session_state.get("show_all_expenses", False) and st.session_state.authenticated:
        st.header("📋 All Expenses")
        all_expenses = query_expenses("SELECT amount, category, description, date FROM expenses ORDER BY date DESC", st.session_state.user['id'])
        
        if all_expenses:
            df = pd.DataFrame(all_expenses, columns=['Amount', 'Category', 'Description', 'Date'])
            df['Amount'] = df['Amount'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df, use_container_width=True)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"expenses_{st.session_state.user['username']}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No expenses found.")
        
        if st.button("❌ Close"):
            st.session_state.show_all_expenses = False
            st.rerun()

if __name__ == "__main__":
    main()