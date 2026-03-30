from api import API
from endpoint import Endpoint
from server_http import Server
from request import Request
from response import Response

def download(request: Request) -> Response:
    with open("rs_worker.exe", "rb") as f:
        exe_bytes = f.read()
    return Response(
        status=200,
        message="OK",
        headers={"Content-Type": ["application/octet-stream"], "Content-Length": [str(len(exe_bytes))]},
        body=exe_bytes,
    )

api = API()
api.add(Endpoint(uri="/download", method="GET", endpoint=download, basic=True))

server = Server(api=api)
server.open(("0.0.0.0", 8080))
server.connection.listen(1)
print("[*] File server listening on port 8080...")

while True:
    client, addr = server.connection.accept()
    print(f"[+] Connection from {addr}")
    server.handle(client)