#!/usr/bin/env python3
"""
Render deployment script for ElevenLabs Admin Backend
"""
import os
import sys
from src.auth.admin.web_interface import create_admin_app
import uvicorn

def main():
    print("🚀 Starting ElevenLabs Admin Backend...")
    
    # Get database URL from environment or use default
    database_url = os.environ.get(
        'DATABASE_URL', 
        'postgresql://elevenlabs_auth_db_user:Dta5busSXW4WPPaasBVvjtyTXT2fXU9t@dpg-d21hsaidbo4c73e6ghe0-a/elevenlabs_auth_db_l1le'
    )
    
    # Get admin credentials from environment or use defaults
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    print(f"📊 Admin Username: {admin_username}")
    print(f"🗄️  Database: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    
    # Create FastAPI app
    app = create_admin_app(
        database_url=database_url,
        admin_username=admin_username,
        admin_password=admin_password
    )
    
    # Initialize database on startup
    try:
        from src.auth.database.manager import AuthDatabaseManager
        import urllib.parse
        
        # Parse database URL
        if database_url.startswith('postgresql://'):
            parsed = urllib.parse.urlparse(database_url)
            db_manager = AuthDatabaseManager(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path.lstrip('/'),
                username=parsed.username,
                password=parsed.password
            )
            
            print("🔧 Initializing database...")
            if db_manager.init_database():
                print("✅ Database initialized successfully!")
            else:
                print("❌ Database initialization failed!")
                
        else:
            print("⚠️  Using default database configuration")
            
    except Exception as e:
        print(f"⚠️  Database initialization error: {e}")
        print("Continuing with app startup...")
    
    # Get port from environment (Render uses PORT env var)
    port = int(os.environ.get("PORT", 10000))
    
    print(f"🌐 Starting Admin Interface on port {port}")
    print(f"🔗 Dashboard: https://elevenlabs-auth-backend.onrender.com/admin/dashboard")
    
    # Start the server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main() 