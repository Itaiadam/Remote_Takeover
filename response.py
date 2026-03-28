from dataclasses import dataclass, field

@dataclass
class Response:
    message: str = "OK"
    status: int = 200
    version: str = "HTTP/1.1"
    headers: dict[str, list[str]] = field(default_factory=dict)
    body: bytes = b""
    line_break: bytes = b"\r\n"

    #הפעולה בונה תגובה ומחזירה את התגובה בבייטים
    def dump(self) -> bytes:
        status_line = f"{self.version} {self.status} {self.message}".encode() + self.line_break
        headers_bytes = b""
        if self.headers:
            for key, values in self.headers.items():
                for value in values:
                    header_line = f"{key}: {value}".encode() + self.line_break
                    headers_bytes += header_line
        return status_line + headers_bytes + self.line_break + self.body

    # הפעולה מקבלת תגובה בבייטים ומחזירה את התגובה מתורגמת לאובייקט מטיפוס Response
    @classmethod
    def load(cls, response: bytes, line_break: bytes = b"\r\n") -> "Response":
        parts = response.split(line_break)
        status_line = parts[0].decode()
        version, status, message = status_line.split(" ", 2)
        status = int(status)
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
        return cls(message=message, status=status, version=version, headers=headers, body=body, line_break=line_break)

    # מתודה שמעתיקה ומחזירה את האובייקט המועתק
    def copy(self) -> "Response":
        headers_copy = {k: v[:] for k, v in (self.headers or {}).items()}
        return Response(message=self.message, status=self.status, version=self.version, headers=headers_copy, body=self.body, line_break=self.line_break)