import os
import socket
import time


def main() -> None:
    host = os.environ.get("POSTGRES_HOST", "db")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    timeout_s = int(os.environ.get("DB_WAIT_TIMEOUT", "30"))

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            s = socket.create_connection((host, port), timeout=1)
            s.close()
            return
        except OSError:
            time.sleep(1)

    raise SystemExit(f"Database not reachable at {host}:{port} after {timeout_s}s")


if __name__ == "__main__":
    main()

