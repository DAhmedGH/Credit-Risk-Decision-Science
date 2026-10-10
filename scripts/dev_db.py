"""Start only this project's isolated PostgreSQL; never delete resources or print secrets."""

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "credit-risk-phase1"
LABEL = "credit-risk-decision-science"


def docker(*args, capture=True):
    return subprocess.run(["docker", *args], cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE)


def read_env():
    path = ROOT / ".env"
    if not path.exists():
        return {}
    return dict(line.split("=", 1) for line in path.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#"))


def choose_port():
    for port in range(55432, 55452):
        try:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", port))
                return port
        except PermissionError as exc:
            raise RuntimeError("Session cannot check loopback ports; no port was assumed free") from exc
        except OSError:
            continue
    raise RuntimeError("No free host port in 55432..55451")


def ensure_owned_resources():
    containers = docker("ps", "-a", "--filter", f"label=com.docker.compose.project={PROJECT}",
                        "--format", "{{.ID}}").stdout.split()
    for cid in containers:
        info = json.loads(docker("inspect", cid).stdout)[0]
        labels = info["Config"].get("Labels", {})
        if labels.get("com.credit-risk.project") != LABEL:
            raise RuntimeError("Existing Compose resource lacks this project's ownership label")
    # Also refuse adopting a pre-existing volume belonging to another project.
    volumes = docker("volume", "ls", "--format", "{{.Name}}").stdout.split()
    if f"{PROJECT}-pgdata" in volumes:
        info = json.loads(docker("volume", "inspect", f"{PROJECT}-pgdata").stdout)[0]
        if (info.get("Labels") or {}).get("com.credit-risk.project") != LABEL:
            raise RuntimeError("Existing PostgreSQL volume is not owned by this project")
    return containers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "status", "stop"])
    args = parser.parse_args()
    docker("info", "--format", "{{.ServerVersion}}")
    containers = ensure_owned_resources()
    if args.action == "up":
        env = read_env()
        if not env:
            env = {"POSTGRES_DB": "credit_risk_dev", "POSTGRES_USER": "credit_risk_app",
                   "POSTGRES_PASSWORD": secrets.token_hex(24),
                   "POSTGRES_HOST_PORT": str(choose_port())}
            fd = os.open(ROOT / ".env", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write("".join(f"{key}={value}\n" for key, value in env.items()))
        if env.get("POSTGRES_DB") != "credit_risk_dev" or env.get("POSTGRES_USER") != "credit_risk_app":
            raise RuntimeError(".env must name the dedicated project database and role")
        password = env.get("POSTGRES_PASSWORD", "")
        if len(password) < 16 or password == "REPLACE_WITH_RANDOM_LOCAL_PASSWORD":
            raise RuntimeError(".env needs a random local password of at least 16 characters")
        port = int(env["POSTGRES_HOST_PORT"])
        if not containers:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", port))
        docker("compose", "--project-name", PROJECT, "up", "-d", "--wait", capture=False)
        cid = docker("compose", "--project-name", PROJECT, "ps", "-q", "postgres").stdout.strip()
        info = json.loads(docker("inspect", cid).stdout)[0]
        report = {"project": PROJECT, "service": "postgres", "image_id": info["Image"],
                  "image_tag": info["Config"]["Image"], "host": "127.0.0.1", "port": port,
                  "database": "credit_risk_dev", "lifecycle": "disposable-development"}
        target = ROOT / "artifacts/runtime/postgres.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Project PostgreSQL ready at 127.0.0.1:{port}; credentials remain in ignored .env")
    elif args.action == "status":
        docker("compose", "--project-name", PROJECT, "ps", capture=False)
    else:
        docker("compose", "--project-name", PROJECT, "stop", capture=False)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        # Docker's diagnostic can include interpolated configuration. Do not relay it.
        print("Docker command failed. Check Docker Desktop WSL integration and session socket access.",
              file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Database setup stopped: {error}", file=sys.stderr)
        sys.exit(1)
