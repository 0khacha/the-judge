import base64
import json
import hmac
import hashlib
import time
from typing import Dict, Any


class TokenExpiredError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _b64_decode(data_str: str) -> bytes:
    padding = 4 - (len(data_str) % 4)
    if padding != 4:
        data_str += '=' * padding
    return base64.urlsafe_b64decode(data_str)


def encode_token(payload: Dict[str, Any], secret: str, expires_in: int = 900) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload_copy = dict(payload)
    payload_copy["exp"] = time.time() + expires_in

    header_b64 = _b64_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _b64_encode(json.dumps(payload_copy).encode('utf-8'))

    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_token(token: str, secret: str) -> Dict[str, Any]:
    parts = token.split('.')
    if len(parts) != 3:
        raise InvalidTokenError("Invalid token format")

    header_b64, payload_b64, sig_b64 = parts
    
    # Signature check
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    expected_sig = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64_encode(expected_sig), sig_b64):
        raise InvalidTokenError("Invalid token signature")

    payload_data = json.loads(_b64_decode(payload_b64).decode('utf-8'))

    # FLAW: Expiration check missing in starter code!
    # exp = payload_data.get("exp")
    # if exp and time.time() > exp:
    #     raise TokenExpiredError("Token has expired")

    return payload_data
