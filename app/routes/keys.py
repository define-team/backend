from flask import Blueprint, request, jsonify
from app.models import User, Key, Operation, db
from app.utils.decorators import require_device_auth
from datetime import datetime

bp = Blueprint("device", __name__, url_prefix="/device")



@bp.route("/take_key/", methods=["POST"])
@require_device_auth
def take_key():
    """
        Взятие ключа
        ---
        tags:
          - Device
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              properties:
                user_id:
                  type: string
                  example: "user123"
                key_number:
                  type: integer
                  example: 101
        responses:
          200:
            description: Ключ успешно выдан
          400:
            description: Ошибка запроса
          404:
            description: Пользователь или ключ не найден
        """
    data = request.get_json()
    return operate_key_action(data, operation="take")


@bp.route("/return_key/", methods=["POST"])
@require_device_auth
def return_key():
    """
        Возврат ключа
        ---
        tags:
          - Device
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              properties:
                user_id:
                  type: string
                  example: "user123"
                key_number:
                  type: integer
                  example: 101
        responses:
          200:
            description: Ключ успешно возвращён
          400:
            description: Ошибка запроса
          404:
            description: Пользователь или ключ не найден
        """
    data = request.get_json()
    return operate_key_action(data, operation="return")


def operate_key_action(data, operation):
    user_id = data.get("user_id")
    key_number = data.get("key_number")

    if not all([user_id, key_number]):
        return jsonify({"status": "error", "reason": "Missing fields"}), 400

    user = User.query.filter_by(user_id=user_id).first()
    key = Key.query.filter_by(key_number=key_number).first()

    if not user or not key:
        return jsonify({"status": "error", "reason": "User or key not found"}), 404

    if operation == "take":
        if key.status == "taken":
            return jsonify({"status": "error", "reason": "Ключ уже взят"})

        user_role_ids = [role.id for role in user.roles]
        if key.assigned_role_id not in user_role_ids:
            return jsonify({"status": "denied", "reason": "Нет доступа к ключу"})

        key.status = "taken"
        key.last_user_id = user.id
        key.last_device_id = request.device_id
        key.updated_at = datetime.utcnow()

    elif operation == "return":
        if key.status == "available":
            return jsonify({"status": "error", "reason": "Ключ уже на месте"})

        key.status = "available"
        key.last_user_id = user.id
        key.last_device_id = request.device_id
        key.updated_at = datetime.utcnow()

    else:
        return jsonify({"status": "error", "reason": "Invalid operation"}), 400

    db.session.add(Operation(
        user_id=user.id,
        key_id=key.id,
        device_id=request.device_id,
        type=operation,
        timestamp=datetime.utcnow()
    ))
    db.session.commit()

    return jsonify({"status": "granted"})
