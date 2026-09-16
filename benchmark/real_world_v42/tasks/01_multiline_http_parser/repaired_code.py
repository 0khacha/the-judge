class HTTPHeaderParser:
    def parse(self, raw_headers: str) -> dict:
        headers = {}
        last_key = None
        for line in raw_headers.splitlines():
            if line.startswith(" ") or line.startswith("\t"):
                if last_key:
                    headers[last_key] += " " + line.strip()
            elif ":" in line:
                k, v = line.split(":", 1)
                last_key = k.strip().lower()
                headers[last_key] = v.strip()
        return headers
