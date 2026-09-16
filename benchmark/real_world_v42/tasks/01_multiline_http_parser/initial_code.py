class HTTPHeaderParser:
    def parse(self, raw_headers: str) -> dict:
        headers = {}
        for line in raw_headers.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        return headers
