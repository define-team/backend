import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your_admin_secret_key"
ALGORITHM = "HS256"

def generate_admin_jwt(admin_id):
    payload = {
        "admin_id": admin_id,
        "exp": datetime.utcnow() + timedelta(hours=6)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_admin_jwt(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id = payload.get("admin_id")
        if not admin_id:
            return None
        return admin_id
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

