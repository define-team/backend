import jwt
import os
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
EXPIRATION_MINUTES = 60

def generate_jwt(payload, expires_delta=timedelta(minutes=EXPIRATION_MINUTES)):
    payload = payload.copy()
    payload["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_jwt(token):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

