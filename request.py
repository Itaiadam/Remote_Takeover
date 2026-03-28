from dataclasses import dataclass, field
@dataclass
class Request:
    method: str = "GET"
    uri: str = "/"
    version: str = "HTTP/1.1"
    headers: dict[str, list[str]] = field(default_factory=dict)
    body: bytes = b""
    line_break: bytes = b"\r\n"
    #הפעולה בונה בקשה ומחזירה את הבקשה בבייטים
    def dump(self) -> "bytes":
        request_line = f"{self.method} {self.uri} {self.version}".encode() + self.line_break
        headers_bytes = b""
        if self.headers:
            for key, values in self.headers.items():
                for value in values:
                    header_line = f"{key}: {value}".encode() + self.line_break
                    headers_bytes += header_line
        return request_line + headers_bytes + self.line_break + self.body

    # הפעולה מקבלת בקשה בבייטים ומחזירה את הבקשה מתורגמת לאובייקט מטיפוס Request
    @classmethod
    def load(cls, request: bytes, line_break: bytes = b"\r\n") -> "Request":
        parts = request.split(line_break)
        request_line = parts[0].decode()
        method, uri, version = request_line.split(" ", 2)
        headers = {}
        i = 1
        while i < len(parts) and parts[i] != b"":
            line = parts[i].decode()
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            headers.setdefault(key, []).append(value)
            i += 1
        i += 1
        body = b""
        if i < len(parts):
            body = line_break.join(parts[i:])
        return cls(method=method, uri=uri, version=version, headers=headers, body=body, line_break=line_break)
    # מתודה שמעתיקה ומחזירה את האובייקט המועתק
    def copy(self) -> "Request":
        headers_copy = {k: v[:] for k, v in (self.headers or {}).items()}
        return Request(method=self.method, uri=self.uri, version=self.version, headers=headers_copy, body=self.body, line_break=self.line_break)