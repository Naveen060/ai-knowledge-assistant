import hmac
import json
import os
from fastapi import Header, HTTPException

def current_user(authorization: str = Header(default='')) -> str:
    tokens = json.loads(os.getenv('USER_TOKENS', '{}'))
    if not tokens:
        raise HTTPException(503, 'Configure USER_TOKENS on the server')
    scheme, _, supplied = authorization.partition(' ')
    if scheme.lower() == 'bearer' and supplied:
        for token, user in tokens.items():
            if hmac.compare_digest(supplied, token):
                return user
    raise HTTPException(401, 'Invalid access token')
