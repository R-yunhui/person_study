import subprocess, sys, time, atexit, urllib.request, os

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_startup.log")
def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
log(f"Project dir: {PROJECT_DIR}")
log(f"CWD: {os.getcwd()}")

httpd = None
try:
    urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=1)
    log("HTTP server already running")
except Exception:
    log("Starting HTTP server...")
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_DIR + os.pathsep + env.get("PYTHONPATH", "")
    httpd = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=PROJECT_DIR,
        env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    for i in range(20):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=0.5)
            log("HTTP server ready")
            break
        except Exception as e:
            time.sleep(0.3)
    else:
        log(f"HTTP server failed to start: {httpd.stderr.read(500).decode('utf-8', errors='replace')}")
        sys.exit(1)

if httpd:
    atexit.register(lambda: httpd.terminate())
    log("HTTP subprocess registered")

log("Starting MCP server...")
import mcp_server
mcp_server.app.run()
