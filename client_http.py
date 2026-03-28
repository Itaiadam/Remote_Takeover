from dataclasses import dataclass, field
from request import Request
from response import Response
import socket

@dataclass
class Client:
    connection: socket.socket = field(default_factory=socket.socket)

    def open(self, address: tuple[str, int]) -> None:
        self.connection = socket.socket()
        self.connection.connect(address)

    def request(self, request: Request, close: bool = True) -> "Response":
        self.connection.sendall(request.dump())
        response = Response.load(self.connection.recv(4096))
        if close:
            self.connection.close()
        return response


