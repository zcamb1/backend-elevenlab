#!/usr/bin/env python3
"""
Render deployment script for ElevenLabs Auth API Server
"""
import os
import uvicorn

def create_safe_api_app():
    """Create API app with error handling"""
    try:
        from src.auth.server.api import app
        
        # Database URL
        database_url = os.environ.get(
            'DATABASE_URL', 
            'postgresql://elevenlabs_auth_db_user:Dta5busSXW4WPPaasBVvjtyTXT2fXU9t@dpg-d21hsaidbo4c73e6ghe0-a/elevenlabs_auth_db_l1le'
        )
        
        print(f"✅ API app imported successfully")
        print(f"🗄️  Database: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
        
        # Try to initialize database
        try:
            from src.auth.database.manager import AuthDatabaseManager
            db = AuthDatabaseManager()
            if db.init_database():
                print("✅ Database initialized")
            else:
                print("⚠️  Database init skipped")
        except Exception as e:
            print(f"⚠️  Database init error: {e}")
        
        return app
        
    except Exception as e:
        print(f"❌ Error creating API app: {e}")
        # Return basic FastAPI app if import fails
        from fastapi import FastAPI
        app = FastAPI(title="ElevenLabs Auth API (Error)")
        
        @app.get("/")
        def health():
            return {"status": "error", "message": str(e), "service": "auth_api"}
            
        @app.get("/health")
        def health_check():
            return {"status": "error", "message": str(e)}
            
        return app

def main():
    print("🚀 Starting ElevenLabs Auth API Server...")
    
    # Create app with error handling
    app = create_safe_api_app()
    
    # Get port from environment (Render uses PORT env var)
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🌐 Starting Auth API on port {port}")
    print(f"📋 API Documentation: https://backend-elevenlab.onrender.com/docs")
    print(f"🔗 Health Check: https://backend-elevenlab.onrender.com/health")
    
    # Start the server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main() 