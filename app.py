from flask import Flask, render_template
import psutil, platform, socket, datetime

app = Flask(__name__)

def get_uptime():
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    now = datetime.datetime.now()
    return str(now - boot_time).split('.')[0]  # ohne Mikrosekunden

@app.route("/")
def index():
    info = {
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "hostname": socket.gethostname(),
        "system": platform.system(),
        "release": platform.release(),
        "uptime": get_uptime(),
        "net": psutil.net_io_counters(),
    }
    return render_template("index.html", info=info)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
