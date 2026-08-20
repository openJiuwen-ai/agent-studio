#!/usr/bin/env python3
"""Nginx load balancing launcher for agent-runtime.

Generates nginx.conf from jinja2 template, starts multiple uvicorn single-worker
processes on sequential ports, then starts nginx to proxy traffic to them.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("ERROR: jinja2 is required. Install with: pip install jinja2", file=sys.stderr)
    sys.exit(1)


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def get_env_int(name: str, default: int = 0) -> int:
    val = get_env(name)
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def compute_worker_ports(server_port: int, worker_num: int) -> list[int]:
    """Worker ports = SERVER_PORT+1 to SERVER_PORT+GUNICORN_WORK_NUM."""
    return [server_port + i for i in range(1, worker_num + 1)]


def render_nginx_config(
    template_dir: str,
    output_path: str,
    log_dir: str,
    pid_file: str,
    lb_strategy: str,
    worker_ports: list[int],
    listen_addr: str,
    enable_ssl: bool,
    ssl_cert: str = "",
    ssl_key: str = "",
) -> str:
    """Render nginx.conf from jinja2 template and write to output_path."""
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("nginx.conf.j2")
    content = template.render(
        log_dir=log_dir,
        pid_file=pid_file,
        lb_strategy=lb_strategy,
        worker_ports=worker_ports,
        listen_addr=listen_addr,
        enable_ssl=enable_ssl,
        ssl_cert=ssl_cert,
        ssl_key=ssl_key,
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


def wait_for_health(port: int, timeout: int = 60, interval: float = 1.0) -> bool:
    """Wait for a worker to respond on /v1/health endpoint."""
    import urllib.request

    scheme = "https" if get_env("HTTPS") == "true" else "http"
    url = f"{scheme}://127.0.0.1:{port}/v1/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url)
            if scheme == "https":
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                urllib.request.urlopen(req, timeout=3, context=ctx)
            else:
                urllib.request.urlopen(req, timeout=3)
            return True
        except Exception:
            time.sleep(interval)
    return False


def start_workers(
    script_dir: str, server_port: int, worker_num: int
) -> list[subprocess.Popen]:
    """Start worker processes using existing start_server.sh."""
    processes = []
    start_server_sh = os.path.join(script_dir, "start_server.sh")
    for i in range(1, worker_num + 1):
        port = server_port + i
        print(f"Starting worker on port {port}...")
        proc = subprocess.Popen(
            ["bash", start_server_sh, str(port)],
        )
        processes.append(proc)
    return processes


def start_nginx(config_path: str) -> subprocess.Popen:
    """Start nginx with the generated config."""
    print(f"Starting nginx with config: {config_path}")
    proc = subprocess.Popen(
        ["nginx", "-c", config_path],
    )
    return proc


def main():
    # --- Read configuration from environment ---
    # PORT is the primary env var in K8s/docker-compose; SERVER_PORT is the pydantic alias
    server_port = get_env_int("PORT", 0) or get_env_int("SERVER_PORT", 8000)
    worker_num = get_env_int("GUNICORN_WORK_NUM", 1)
    if worker_num < 1:
        worker_num = 1
    lb_strategy = get_env("LB_STRATEGY", "least_conn")
    enable_ssl = get_env("HTTPS") == "true"
    ssl_cert = get_env("TLS_CERT_PATH", "")
    ssl_key = get_env("TLS_CERT_KEY_PATH", "")
    run_with_engine = get_env("RUN_WITH_ENGINE")
    log_dir = get_env("NGINX_LOG_DIR") or get_env("LOGGING_LOG_PATH", "/opt/cloud/logs")

    # --- Compute derived values ---
    worker_ports = compute_worker_ports(server_port, worker_num)

    if run_with_engine == "true":
        listen_addr = f"127.0.0.1:{server_port}"
    else:
        listen_addr = f"0.0.0.0:{server_port}"

    # --- Paths ---
    this_dir = Path(__file__).parent
    template_dir = str(this_dir)
    script_dir = str(this_dir.parent / "bin")
    nginx_conf_path = os.path.join(log_dir, "nginx.conf")
    pid_file = os.path.join(log_dir, "nginx.pid")

    # --- Create log directories ---
    os.makedirs(os.path.join(log_dir, "nginx"), exist_ok=True)

    # --- Render nginx config ---
    print(f"Rendering nginx config: strategy={lb_strategy}, "
          f"workers={worker_ports}, listen={listen_addr}")
    render_nginx_config(
        template_dir=template_dir,
        output_path=nginx_conf_path,
        log_dir=log_dir,
        pid_file=pid_file,
        lb_strategy=lb_strategy,
        worker_ports=worker_ports,
        listen_addr=listen_addr,
        enable_ssl=enable_ssl,
        ssl_cert=ssl_cert,
        ssl_key=ssl_key,
    )
    print(f"Nginx config written to: {nginx_conf_path}")

    # --- Start workers ---
    worker_processes = start_workers(script_dir, server_port, worker_num)

    # --- Wait for workers to be healthy ---
    print("Waiting for workers to be healthy...")
    for i, port in enumerate(worker_ports):
        if wait_for_health(port, timeout=120):
            print(f"Worker on port {port} is healthy")
        else:
            print(f"WARNING: Worker on port {port} did not become healthy within timeout", file=sys.stderr)

    # --- Start nginx ---
    nginx_process = start_nginx(nginx_conf_path)
    print("Nginx started")

    # --- Signal handling and process monitoring ---
    shutting_down = False

    def shutdown_handler(signum, frame):
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print(f"\nReceived signal {signum}, shutting down...")

        # Stop nginx first (drain connections)
        if nginx_process.poll() is None:
            nginx_process.send_signal(signal.SIGTERM)
            try:
                nginx_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                nginx_process.kill()
            print("Nginx stopped")

        # Stop workers
        for i, proc in enumerate(worker_processes):
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
        for i, proc in enumerate(worker_processes):
            if proc.poll() is None:
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("All workers stopped")

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # --- Main loop: monitor child processes ---
    print("Nginx load balancing is running. Press Ctrl+C to stop.")
    while not shutting_down:
        # Check nginx
        if nginx_process.poll() is not None:
            print(f"ERROR: Nginx exited with code {nginx_process.returncode}", file=sys.stderr)
            break
        # Check workers
        for i, proc in enumerate(worker_processes):
            if proc.poll() is not None:
                port = worker_ports[i]
                print(f"WARNING: Worker on port {port} exited with code {proc.returncode}", file=sys.stderr)
                # Restart the worker
                print(f"Restarting worker on port {port}...")
                start_server_sh = os.path.join(script_dir, "start_server.sh")
                new_proc = subprocess.Popen(
                    ["bash", start_server_sh, str(port)],
                )
                worker_processes[i] = new_proc
                if wait_for_health(port, timeout=60):
                    print(f"Worker on port {port} restarted and healthy")
                else:
                    print(f"WARNING: Restarted worker on port {port} not healthy", file=sys.stderr)
        time.sleep(5)

    # Cleanup if not already done
    if not shutting_down:
        shutdown_handler(signal.SIGTERM, None)


if __name__ == "__main__":
    main()
