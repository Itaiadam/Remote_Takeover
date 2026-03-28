from typing import Callable
from dataclasses import dataclass, field
from request import Request
from response import Response
import json
@dataclass
class Endpoint:
    uri: str
    method: str
    endpoint: Callable = None
    default: Response = field(default_factory=Response)
    basic: bool = True

    def call(self, request: Request) -> Response:
        if self.endpoint is None:
            return self.default.copy()
        elif self.basic:
            output = self.endpoint(request)
        else:
            try:
                parameters = json.loads(request.body or "{}")
            except json.JSONDecodeError:
                # Return 422 Unprocessable Entity
                return Response(
                    status=422,
                    message="Unprocessable Entity",
                )
            if isinstance(parameters, dict):
                output = self.endpoint(**parameters)
            elif isinstance(parameters, list):
                output = self.endpoint(*parameters)
            else:
                output = self.endpoint(parameters)
        if isinstance(output, Response):
            return output
        body = json.dumps(output).encode()
        response = Response(body=body)
        if "Content-Type" not in response.headers:
            response.headers["Content-Type"] = ["application/json"]
        return response

