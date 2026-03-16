"""Local test runner — loads .env and starts HTTP server on port 8080."""
import os
from pathlib import Path
from http.server import HTTPServer

# Load .env
env_file = Path(__file__).parent / ".env"
for line in env_file.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

from api.weekly_report import handler  # noqa: E402

if __name__ == "__main__":
    server = HTTPServer(("localhost", 8080), handler)
    cron_secret = os.environ.get("CRON_SECRET", "")
    print(f"Server running at http://localhost:8080")
    print(f"Test with:")
    print(f'  curl -H "Authorization: Bearer {cron_secret}" http://localhost:8080/api/weekly_report')
    server.serve_forever()
