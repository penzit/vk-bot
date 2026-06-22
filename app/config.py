import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN", "")
GROUP_ID = os.getenv("GROUP_ID", "")
ADMIN_VK_ID = os.getenv("ADMIN_VK_ID", "")
ADMIN_PANEL_PORT = int(os.getenv("ADMIN_PANEL_PORT", "8080"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.db")

DATABASE_URL = os.getenv("DATABASE_URL", "")

VK_MINI_APP_ID = int(os.getenv("VK_MINI_APP_ID", "54647954"))

ADMIN_VK_DOMAIN = os.getenv("ADMIN_VK_DOMAIN", "bulken")
