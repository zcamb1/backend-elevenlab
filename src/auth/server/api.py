#!/usr/bin/env python3
"""
FastAPI Authentication Server cho ElevenLabs Tool
Cung cấp API endpoints cho authentication và session management
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import uvicorn
import hashlib
import secrets
from datetime import datetime, timedelta
import json
import os

# Import local modules
from ..database.manager import AuthDatabaseManager
from ..utils.fingerprint import DeviceFingerprint

# Initialize
app = FastAPI(
    title="ElevenLabs Authentication API",
    description="Authentication and session management for ElevenLabs Tool",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

# Global database instance với cấu hình đúng
auth_db = AuthDatabaseManager(
    host="dpg-d1kldjre5dus73enuikg-a",
    port=5432,
    database="elevenlabs_auth_db",
    username="elevenlabs_auth_db_user",
    password="vVCP9zqfRfcFOD2OMHS8PJKxHpALAq07"
)

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str
    device_info: Optional[Dict] = None

class LoginResponse(BaseModel):
    success: bool
    session_token: Optional[str] = None
    user_info: Optional[Dict] = None
    error: Optional[str] = None
    expires_at: Optional[str] = None

class SessionVerifyResponse(BaseModel):
    valid: bool
    user_info: Optional[Dict] = None
    error: Optional[str] = None

class CreateUserRequest(BaseModel):
    username: str
    password: str
    account_type: str = "trial"
    duration_days: Optional[int] = None

class UserResponse(BaseModel):
    success: bool
    user_id: Optional[int] = None
    error: Optional[str] = None

# Helper functions
def get_client_ip(request: Request) -> str:
    """Lấy IP address của client"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

def generate_device_fingerprint() -> str:
    """Generate device fingerprint"""
    fingerprinter = DeviceFingerprint()
    return fingerprinter.generate_device_id()

async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Verify admin authentication for admin endpoints"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Simple admin token verification (trong production cần JWT)
    admin_token = "admin_secret_token_12345"  # TODO: Use proper JWT
    
    if credentials.credentials != admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )
    
    return True

# API Endpoints

@app.get("/")
async def root():
    """API status check"""
    return {
        "service": "ElevenLabs Authentication API",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = auth_db.get_connection()
        if conn:
            conn.close()
            db_status = "healthy"
        else:
            db_status = "unhealthy"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "database": db_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request):
    """User login endpoint"""
    try:
        # Generate device fingerprint
        device_fingerprint = generate_device_fingerprint()
        
        # Authenticate user
        auth_result = auth_db.authenticate_user(
            username=request.username,
            password=request.password,
            device_fingerprint=device_fingerprint
        )
        
        if not auth_result or not auth_result.get('success'):
            return LoginResponse(
                success=False,
                error=auth_result.get('error', 'Authentication failed') if auth_result else 'Authentication failed'
            )
        
        # Create session
        session_token = auth_db.create_session(
            user_id=auth_result['user_id'],
            device_fingerprint=device_fingerprint,
            duration_hours=24
        )
        
        if not session_token:
            return LoginResponse(
                success=False,
                error="Failed to create session"
            )
        
        # Calculate expiry
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        
        return LoginResponse(
            success=True,
            session_token=session_token,
            user_info={
                'user_id': auth_result['user_id'],
                'username': auth_result['username'],
                'account_type': auth_result['account_type'],
                'device_fingerprint': device_fingerprint
            },
            expires_at=expires_at
        )
        
    except Exception as e:
        return LoginResponse(
            success=False,
            error=f"Login error: {str(e)}"
        )

@app.post("/auth/verify", response_model=SessionVerifyResponse)
async def verify_session(http_request: Request):
    """Verify session token"""
    try:
        # Extract session token from JSON body
        request_body = await http_request.json()
        session_token = request_body.get('session_token')
        if not session_token:
            return SessionVerifyResponse(
                valid=False,
                error="Missing session_token"
            )
        
        # Generate current device fingerprint
        device_fingerprint = generate_device_fingerprint()
        
        # Verify session
        verify_result = auth_db.verify_session(
            session_token=session_token,
            device_fingerprint=device_fingerprint
        )
        
        if not verify_result or not verify_result.get('valid'):
            return SessionVerifyResponse(
                valid=False,
                error=verify_result.get('error', 'Invalid session') if verify_result else 'Invalid session'
            )
        
        return SessionVerifyResponse(
            valid=True,
            user_info={
                'user_id': verify_result['user_id'],
                'username': verify_result['username'],
                'account_type': verify_result['account_type']
            }
        )
        
    except Exception as e:
        return SessionVerifyResponse(
            valid=False,
            error=f"Session verification error: {str(e)}"
        )

@app.post("/auth/logout")
async def logout(session_token: str):
    """Logout user (revoke session)"""
    try:
        success = auth_db.revoke_session(session_token)
        
        return {
            "success": success,
            "message": "Logged out successfully" if success else "Session not found"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Logout error: {str(e)}"
        }

# Admin endpoints
@app.post("/admin/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest, 
    http_request: Request,
    admin_verified: bool = Depends(verify_admin_token)
):
    """Create new user (admin only)"""
    try:
        user_id = auth_db.create_user(
            username=request.username,
            password=request.password,
            account_type=request.account_type,
            duration_days=request.duration_days
        )
        
        if user_id:
            return UserResponse(
                success=True,
                user_id=user_id
            )
        else:
            return UserResponse(
                success=False,
                error="Failed to create user (username may already exist)"
            )
            
    except Exception as e:
        return UserResponse(
            success=False,
            error=f"Create user error: {str(e)}"
        )

@app.get("/admin/users")
async def get_users(
    include_inactive: bool = False,
    admin_verified: bool = Depends(verify_admin_token)
):
    """Get list of users (admin only)"""
    try:
        users = auth_db.get_users(include_inactive=include_inactive)
        
        return {
            "success": True,
            "users": users,
            "count": len(users)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Get users error: {str(e)}"
        }

@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin_verified: bool = Depends(verify_admin_token)
):
    """Delete user (admin only)"""
    try:
        success = auth_db.delete_user(user_id)
        
        return {
            "success": success,
            "message": "User deleted successfully" if success else "User not found"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Delete user error: {str(e)}"
        }

@app.get("/admin/sessions")
async def get_active_sessions(
    admin_verified: bool = Depends(verify_admin_token)
):
    """Get active sessions (admin only)"""
    try:
        sessions = auth_db.get_active_sessions()
        
        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Get sessions error: {str(e)}"
        }

@app.post("/admin/sessions/{session_token}/revoke")
async def revoke_session_admin(
    session_token: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """Revoke session (admin only)"""
    try:
        success = auth_db.revoke_session(session_token)
        
        return {
            "success": success,
            "message": "Session revoked successfully" if success else "Session not found"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Revoke session error: {str(e)}"
        }

@app.get("/admin/stats")
async def get_stats(
    admin_verified: bool = Depends(verify_admin_token)
):
    """Get system statistics (admin only)"""
    try:
        users = auth_db.get_users(include_inactive=False)
        sessions = auth_db.get_active_sessions()
        
        # Count by account type
        trial_users = len([u for u in users if u['account_type'] == 'trial'])
        paid_users = len([u for u in users if u['account_type'] == 'paid'])
        
        # Count expired trial accounts
        expired_trials = 0
        for user in users:
            if user['account_type'] == 'trial' and user['expires_at']:
                if datetime.fromisoformat(user['expires_at'].replace('Z', '+00:00')) < datetime.now():
                    expired_trials += 1
        
        return {
            "success": True,
            "stats": {
                "total_users": len(users),
                "trial_users": trial_users,
                "paid_users": paid_users,
                "expired_trials": expired_trials,
                "active_sessions": len(sessions),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Get stats error: {str(e)}"
        }

# Utility endpoints
@app.get("/device/fingerprint")
async def get_device_fingerprint():
    """Get current device fingerprint (for debugging)"""
    try:
        fingerprinter = DeviceFingerprint()
        device_info = fingerprinter.get_device_info_summary()
        
        return {
            "success": True,
            "device_info": device_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Device fingerprint error: {str(e)}"
        }

# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "path": str(request.url.path)}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

# Server configuration
class ServerConfig:
    HOST = "localhost"
    PORT = 8000
    RELOAD = False  # Tắt reload để tránh lỗi
    LOG_LEVEL = "info"

def run_server():
    """Start the authentication server"""
    print("🚀 Starting ElevenLabs Authentication Server...")
    print(f"📍 Server will be available at: http://{ServerConfig.HOST}:{ServerConfig.PORT}")
    print(f"📖 API Documentation: http://{ServerConfig.HOST}:{ServerConfig.PORT}/docs")
    print(f"🔧 Admin endpoints require token: admin_secret_token_12345")
    print("=" * 60)
    
    # Initialize database
    print("🗄️  Initializing database...")
    if auth_db.init_database():
        print("✅ Database initialized successfully")
    else:
        print("❌ Database initialization failed")
        return
    
    # Start server
    uvicorn.run(
        "src.auth.server.api:app",
        host=ServerConfig.HOST,
        port=ServerConfig.PORT,
        reload=ServerConfig.RELOAD,
        log_level=ServerConfig.LOG_LEVEL
    )

if __name__ == "__main__":
    run_server() 