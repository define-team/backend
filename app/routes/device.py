from flask import Blueprint, request, jsonify
from app.models import Device, User, Key, Operation, db
from app import db
from app.utils.jwt_utils import generate_jwt
from app.utils.decorators import require_device_auth
from datetime import datetime
bp = Blueprint("device", __name__, url_prefix="")


@bp.route("/scan_card/", methods=["POST"])
@require_device_auth
def scan_card():
    """
        Скан карты
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
                card_id:
                  type: string
                  example: "04A224B98C6280"
        responses:
          200:
            description: Данные пользователя
          400:
            description: Неверные данные карты
          404:
            description: Карта не зарегистрирована
        """
    data = request.get_json()
    tag = data.get("card_id")
    if not tag:
        return jsonify({"status": "error", "reason": "card_id is required"}), 400

    user = User.query.filter_by(nfc_tag=tag).first()
    if not user:
        return jsonify({"status": "error", "reason": "Карта не зарегистрирована"}), 404

    roles = [user.role.name] if user.role else []

    return jsonify({
        "status": "ok",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "roles": roles
        }
    })


@bp.route("/init/", methods=["POST"])
def init_device():
    """
        Инициализация устройства
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
                device_id:
                  type: string
                  example: "device_001"
                auth_key:
                  type: string
                  example: "super_secret_key"
        responses:
          200:
            description: Токен успешно выдан
          401:
            description: Ошибка авторизации устройства
        """
    data = request.get_json()
    device_id = data.get("device_id")
    auth_key = data.get("auth_key")

    device = Device.query.filter_by(device_id=device_id, auth_token=auth_key).first()
    if not device:
        return jsonify({"error": "Unauthorized"}), 401

    token = generate_jwt({"device_id": device.id})
    return jsonify({"token": token})

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

        user_role_ids = [user.role.id] if user.role else []

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
