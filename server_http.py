from dataclasses import dataclass, field
from request import Request
from api import API
import socket

@dataclass
class Server:
    api: API
    connection: socket.socket = field(default_factory=socket.socket)

    def open(self, address: tuple[str, int]) -> None:
        self.connection = socket.socket()
        self.connection.bind(address)

    def handle(self, client: socket.socket = None, close: bool = True) -> None:
        if client is None:
            client, client_address = self.connection.accept()
        data = client.recv(4096)
        request = Request.load(data, b"\r\n")
        response = self.api.respond(request)
        client.sendall(response.dump())
        if close:
            client.close()