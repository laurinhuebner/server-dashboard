import os, time, socket, platform, datetime, subprocess, requests
import psutil
from flask import Flask, jsonify, render_template, request, abort

# ---------------------- Konfiguration ----------------------
PORT = int(os.environ.get("PORT", "5050"))
SECRET = os.environ.get("DASHBOARD_SECRET", "")  # optionales Bearer-Token

# Optional: Dienste-Liste & Wetter aus config.toml
SERVICES = []
WEATHER = {"city": "Emden", "lat": 53.3667, "lon": 7.2167}

try:
    import tomllib  # Py 3.11+
except Exception:
    tomllib = None

def load_services_from_toml():
    """Services + Wetter aus config.toml laden (mit Geocoding-Fallback)."""
    global SERVICES, WEATHER
    path = "config.toml"
    if tomllib and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                cfg = tomllib.load(f)
            SERVICES = cfg.get("services", {}).get("list", [])

            w = cfg.get("weather", {})
            if w:
                WEATHER["city"] = w.get("city", WEATHER["city"])
                lat = w.get("latitude")
                lon = w.get("longitude")
                if lat and lon:
                    WEATHER["lat"] = float(lat)
                    WEATHER["lon"] = float(lon)
                else:
                    # Fallback: Stadt -> Koordinaten (OpenStreetMap Nominatim)
                    try:
                        r = requests.get(
                            "https://nominatim.openstreetmap.org/search",
                            params={"q": WEATHER["city"], "format": "json", "limit": 1},
                            headers={"User-Agent": "ServerDashboard/1.0"},
                            timeout=5
                        )
                        if r.ok and r.json():
                            loc = r.json()[0]
                            WEATHER["lat"] = float(loc["lat"])
                            WEATHER["lon"] = float(loc["lon"])
                    except Exception as e:
                        print("Geocoding fehlgeschlagen:", e)
        except Exception as e:
            print("Config laden fehlgeschlagen:", e)
    else:
        SERVICES = []

load_services_from_toml()

# ---------------------- App Setup ----------------------
app = Flask(__name__)
_prev_net = {
    "t": time.time(),
    "tx": psutil.net_io_counters().bytes_sent,
    "rx": psutil.net_io_counters().bytes_recv,
}

def require_auth():
    """Optionales Bearer-Token prüfen (nur wenn SECRET gesetzt)."""
    if not SECRET:
        return
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {SECRET}":
        abort(401)

# ---------------------- Helfer ----------------------
def human_bytes(n: float) -> str:
    units = ["B","KB","MB","GB","TB","PB","EB"]
    n = float(max(0, n))
    for u in units:
        if n < 1024.0:
            return f"{n:.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} ZB"

def uptime_str() -> str:
    boot = datetime.datetime.fromtimestamp(psutil.boot_time())
    diff = datetime.datetime.now() - boot
    return str(datetime.timedelta(seconds=int(diff.total_seconds())))

def disk_list():
    items = []
    for p in psutil.disk_partitions(all=False):
        if not p.fstype:
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
        except PermissionError:
            continue
        items.append({
            "mount": p.mountpoint,
            "total": u.total,
            "used": u.used,
            "percent": u.percent
        })
    return items

def cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        return None
    for key in ("coretemp", "cpu-thermal", "k10temp"):
        if key in temps and temps[key]:
            return temps[key][0].current
    return None

def net_rates():
    global _prev_net
    now = time.time()
    io = psutil.net_io_counters()
    dt = max(0.001, now - _prev_net["t"])
    up_bps  = (io.bytes_sent - _prev_net["tx"]) / dt
    down_bps= (io.bytes_recv - _prev_net["rx"]) / dt
    _prev_net = {"t": now, "tx": io.bytes_sent, "rx": io.bytes_recv}
    return up_bps, down_bps, io.bytes_sent, io.bytes_recv

def service_status(name: str) -> str:
    try:
        out = subprocess.run(
            ["systemctl","is-active",name],
            capture_output=True, text=True, timeout=2
        )
        return (out.stdout or out.stderr).strip() or "unknown"
    except Exception:
        return "unknown"

def docker_ps():
    try:
        out = subprocess.run(
            ["docker","ps","--format","{{.Names}}|{{.Status}}"],
            capture_output=True, text=True, timeout=3
        )
        lines = [l for l in out.stdout.splitlines() if l.strip()]
        items = []
        for l in lines:
            parts = l.split("|",1)
            if len(parts)==2:
                items.append({"name": parts[0], "status": parts[1]})
        return items
    except Exception:
        return []

def top_processes(n=5):
    procs = []
    for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent"]):
        procs.append({
            "pid": p.info.get("pid"),
            "name": p.info.get("name") or "?",
            "cpu_percent": p.info.get("cpu_percent") or 0.0,
            "memory_percent": p.info.get("memory_percent") or 0.0,
        })
    procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
    return procs[:n]

def tail_logs(lines=20):
    for cand in ("/var/log/syslog", "/var/log/messages"):
        if os.path.exists(cand):
            try:
                with open(cand, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    block = 4096
                    data = b""
                    while size > 0 and data.count(b"\n") <= lines:
                        step = min(block, size)
                        size -= step
                        f.seek(size)
                        data = f.read(step) + data
                    return data.decode(errors="ignore").splitlines()[-lines:]
            except Exception:
                return []
    return []

def build_stats():
    up_bps, dn_bps, tx, rx = net_rates()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "hostname": socket.gethostname(),
        "system": f"{platform.system()} {platform.release()}",
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "uptime": uptime_str(),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "cpu_temp": cpu_temp(),
        "mem": {"percent": mem.percent, "used": mem.used, "total": mem.total},
        "swap":{"percent": swap.percent, "used": swap.used, "total": swap.total},
        "disks": disk_list(),
        "net": {
            "up_rate":  human_bytes(up_bps) + "/s",
            "down_rate":human_bytes(dn_bps) + "/s",
            "sent_total":human_bytes(tx),
            "recv_total":human_bytes(rx)
        },
        "services": [{"name": s, "status": service_status(s)} for s in SERVICES] if SERVICES else [],
        "docker": docker_ps(),
        "top": top_processes()
    }

# ---------------------- Routes ----------------------
@app.get("/")
def index():
    require_auth()
    return render_template("index.html", data=build_stats(), weather=WEATHER)

@app.get("/api/stats")
def api_stats():
    require_auth()
    return jsonify(build_stats())

@app.get("/api/logs")
def api_logs():
    require_auth()
    return jsonify(tail_logs(20))

@app.get("/healthz")
def health():
    return "ok", 200

# ---------------------- Main ----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
