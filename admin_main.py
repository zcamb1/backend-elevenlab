from src.auth.admin.web_interface import create_admin_app
import uvicorn

app = create_admin_app(
    admin_username="admin",
    admin_password="admin123"
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000) 