"""Bounded HTTP/1.1 JSON client; no urequests installation required."""
try:
    import usocket as socket
    import ujson as json
except ImportError:
    import socket
    import json


def quote(value):
    result = []
    for byte in str(value).encode("utf-8"):
        if 48 <= byte <= 57 or 65 <= byte <= 90 or 97 <= byte <= 122 or byte in (45, 46, 95, 126):
            result.append(chr(byte))
        else:
            result.append("%%%02X" % byte)
    return "".join(result)


def _read_exact(stream, count):
    result = bytearray()
    while len(result) < count:
        part = stream.read(count - len(result))
        if not part:
            raise ValueError("Incomplete response")
        result.extend(part)
    return result


def get_json(host, path, limit=12288):
    connection = socket.socket()
    stream = None
    try:
        connection.settimeout(4)
        connection.connect(socket.getaddrinfo(host, 80)[0][-1])
        request = ("GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n"
                   "Accept: application/json\r\nAccept-Encoding: identity\r\n\r\n") % (path, host)
        data = request.encode()
        sent = 0
        while sent < len(data):
            count = connection.send(data[sent:])
            if not count:
                raise OSError("Send failed")
            sent += count
        stream = connection.makefile("rb", 0)
        line = stream.readline()
        parts = line.split()
        if len(parts) < 2:
            raise ValueError("Invalid HTTP response")
        status = int(parts[1])
        headers = {}
        header_bytes = 0
        while True:
            line = stream.readline()
            header_bytes += len(line)
            if not line or header_bytes > 4096:
                raise ValueError("Invalid HTTP headers")
            if line in (b"\r\n", b"\n"):
                break
            key, value = line.split(b":", 1)
            headers[key.strip().lower()] = value.strip().lower()
        if status != 200:
            raise ValueError("HTTP %d" % status)
        body = bytearray()
        if b"chunked" in headers.get(b"transfer-encoding", b""):
            while True:
                size = int(stream.readline().split(b";", 1)[0].strip(), 16)
                if size == 0:
                    break
                if len(body) + size > limit:
                    raise ValueError("Response too large")
                body.extend(_read_exact(stream, size))
                if _read_exact(stream, 2) != b"\r\n":
                    raise ValueError("Invalid chunk")
        elif b"content-length" in headers:
            size = int(headers[b"content-length"])
            if size < 0 or size > limit:
                raise ValueError("Response too large")
            body = _read_exact(stream, size)
        else:
            while True:
                part = stream.read(256)
                if not part:
                    break
                body.extend(part)
                if len(body) > limit:
                    raise ValueError("Response too large")
        return json.loads(body.decode("utf-8"))
    finally:
        if stream is not None:
            stream.close()
        connection.close()
