#!/usr/bin/env python3
"""
Quick setup script for Expense Chatbot
Handles database migration and initial setup
"""

import os
import sys
import subprocess
from migrate_db import migrate_database, reset_admin_password, backup_database

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'streamlit',
        'google-generativeai', 
        'pandas',
        'plotly'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("📦 Installing missing packages...")
        for package in missing_packages:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print("✅ All packages installed successfully!")

def setup_database():
    """Setup database with migration if needed"""
    db_file = "expenses.db"
    
    if os.path.exists(db_file):
        print("🔍 Existing database found...")
        
        # Check if migration is needed
        import sqlite3
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        
        try:
            # Check if expenses table has user_id column
            c.execute("PRAGMA table_info(expenses)")
            columns = [row[1] for row in c.fetchall()]
            has_user_id = 'user_id' in columns
            
            if not has_user_id:
                print("🔄 Database migration required...")
                response = input("Migrate existing database? (Y/n): ")
                
                if response.lower() in ['', 'y', 'yes']:
                    migrate_database()
                    reset_admin_password()
                    print("\n✅ Migration completed!")
                    print("Default admin login:")
                    print("  Username: admin")
                    print("  Password: Admin@123")
                    print("  ⚠️  Please change this password after first login!")
                else:
                    print("❌ Migration skipped. The app may not work properly.")
                    return False
            else:
                print("✅ Database is up to date!")
            
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            return False
        finally:
            conn.close()
    else:
        print("📝 Creating fresh database...")
        # Fresh install, no migration needed
        
    return True

def check_api_key():
    """Check if Gemini API key is configured"""
    # This is a placeholder - in production, you'd want to use environment variables
    print("\n🔑 API Configuration:")
    print("Make sure to update your Gemini API key in app.py")
    print("Current key in app.py: AIzaSyCXSeedyFs2z1QNQ58N7tIRkGJNJrPzNd4")
    print("⚠️  Please replace with your own API key for production use!")

def main():
    """Main setup function"""
    print("🚀 EXPENSE CHATBOT SETUP")
    print("=" * 40)
    
    # Step 1: Check requirements
    print("\n1. Checking requirements...")
    check_requirements()
    
    # Step 2: Setup database
    print("\n2. Setting up database...")
    if not setup_database():
        print("❌ Database setup failed!")
        return
    
    # Step 3: API key reminder
    check_api_key()
    
    # Step 4: Ready to run
    print("\n🎉 Setup completed successfully!")
    print("\n▶️  To start the application:")
    print("   streamlit run app.py")
    print("\n📚 First-time setup:")
    print("   1. If migrated: Login with admin/Admin@123")
    print("   2. If fresh: Create a new account")
    print("   3. Change default password if using admin account")
    print("   4. Start tracking your expenses!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
    except Exception as e:
        print(f"\n💥 Setup failed: {str(e)}")
        print("Please check the error and try again.")