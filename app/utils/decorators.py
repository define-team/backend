from flask import request, jsonify
from app.utils.jwt_utils import decode_jwt
from functools import wraps
from app.utils.admin_jwt_utils import verify_admin_jwt

def require_admin_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Authorization header is missing"}), 401
        token = auth_header.split(" ")[1]
        admin_id = verify_admin_jwt(token)
        if not admin_id:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.admin_id = admin_id
        return f(*args, **kwargs)
    return decorated_function
def require_device_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Authorization header missing or invalid"}), 401
        token = auth.split("Bearer ")[-1]
        try:
            payload = decode_jwt(token)
            request.device_id = payload.get("device_id")
            if not request.device_id:
                return jsonify({"error": "Invalid token payload"}), 403
        except Exception as e:
            return jsonify({"error": "Invalid or expired token", "details": str(e)}), 403
        return f(*args, **kwargs)
    return decorated

