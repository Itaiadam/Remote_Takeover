import threading, sys
from server_http import Server
from api import API
import flet as ft
from gui import main as build_gui
from rs_multiple_master_functions import Master, send_command

IP = "192.168.68.55"
PORT = 9999

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
    ft.run(main=lambda page: build_gui(page, master))

if __name__ == "__main__":
    main()




