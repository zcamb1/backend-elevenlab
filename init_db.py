from src.auth.database.manager import AuthDatabaseManager

if __name__ == "__main__":
    db = AuthDatabaseManager()
    if db.init_database():
        print("✅ Database initialized successfully!")
    else:
        print("❌ Database initialization failed!") 