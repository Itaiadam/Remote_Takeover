from endpoint import Endpoint
from dataclasses import dataclass, field
from request import Request
from response import Response

@dataclass
class API:
    headers: dict[str, list[str]] = field(default_factory=dict)
    endpoints:dict[tuple[str, str], Endpoint] = field(default_factory=dict)

    def add(self, endpoint: Endpoint) -> None:
        if (endpoint.method, endpoint.uri) in self.endpoints:
            raise ValueError("endpoint is already exists")
        self.endpoints[(endpoint.method, endpoint.uri)] = endpoint

    def remove(self, endpoint: Endpoint) -> None:
        try:
            self.endpoints.pop((endpoint.method, endpoint.uri))
        except KeyError:
            raise ValueError("endpoint doesn't exist")

    def respond(self, request: Request) -> Response:
        found_uri = False
        method, uri = request.method, request.uri
        endpoint = self.endpoints.get((method, uri))
        if endpoint is None:
            for key in self.endpoints:
                if key[1] == request.uri:
                    found_uri = True
                    break
            if not found_uri:
                response = Response(status=404, message="Not Found")
            else:
                method_matches_uri = any(m == method and u == uri for m, u in self.endpoints.keys())
                if not method_matches_uri:
                    response = Response(status=405, message="Method Not Allowed")
        else:
            try:
                response = endpoint.call(request)
            except Exception:
                response = Response(status=504, message="Internal Server Error")
        for key, value in self.headers.items():
            if key not in response.headers:
                response.headers[key] = value.copy()
        return response