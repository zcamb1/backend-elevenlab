from src.auth.admin.web_interface import create_admin_app
import uvicorn
import os

app = create_admin_app(
    database_url="postgresql://elevenlabs_auth_db_user:vVCP9zqfRfcFOD2OMHS8PJKxHpALAq07@dpg-d1kldjre5dus73enuikg-a/elevenlabs_auth_db",
    admin_username="admin",
    admin_password="admin123"
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port) 