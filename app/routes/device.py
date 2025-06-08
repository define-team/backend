from flask import Blueprint, request, jsonify
from app.models import Device, User, Key, Operation, KeySlot, db
from app.utils.jwt_utils import generate_jwt
from app.utils.decorators import require_device_auth
from datetime import datetime
import logging
import enum

class OperationType(enum.Enum):
    TAKE = "take"
    RETURN = "return"

bp = Blueprint("device", __name__, url_prefix="")


@bp.route("/auth_card/", methods=["POST"])
@require_device_auth
def scan_card():
    """
    Валидация NFC карты и выдача информации о доступных ключах
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
            nfcId:
              type: string
              example: "04A224B98C6280"
    responses:
      200:
        description: Успешная валидация
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [success]
            available_keys:
              type: array
              items:
                type: object
            unavailable_keys:
              type: array
              items:
                type: object
      401:
        description: Ошибка валидации
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [error]
            log:
              type: string
    """
    data = request.get_json()
    nfc_id = data.get("nfcId")

    if not nfc_id:
        return jsonify({
            "status": "error",
            "log": "NFC ID не передан"
        }), 401

    user = User.query.filter_by(nfc_tag=nfc_id).first()

    if not user:
        return jsonify({
            "status": "error",
            "log": f"Пользователь с меткой '{nfc_id}' не найден"
        }), 401

    device = Device.query.get(request.device_id)
    if not device:
        return jsonify({
            "status": "error",
            "log": "Устройство не найдено"
        }), 401

    # Ключи, соответствующие роли пользователя
    role_keys = Key.query.filter_by(assigned_role_id=user.role_id).all()

    available_keys = []
    unavailable_keys = []

    for key in role_keys:
        key_data = {
            "id": key.id,
            "key_number": key.key_number,
            "is_taken": key.is_taken,
            "key_slot_id": key.key_slot_id,
            "device_id": key.key_slot.device_id if key.key_slot else None,
            "last_user_id": key.last_user_id,
            "last_device_id": key.last_device_id,
            "assigned_role_id": key.assigned_role_id,
            "created_at": key.created_at.isoformat() if key.created_at else None,
            "updated_at": key.updated_at.isoformat() if key.updated_at else None
        }

        if (
            key.key_slot and
            key.key_slot.device_id == device.id and
            not key.is_taken
        ):
            available_keys.append(key_data)
        else:
            unavailable_keys.append(key_data)

    return jsonify({
        "status": "success",
        "available_keys": available_keys,
        "unavailable_keys": unavailable_keys
    }), 200



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

    device = Device.query.filter_by(id=device_id, auth_token=auth_key).first()
    if not device:
        return jsonify({"error": "Unauthorized"}), 401

    token = generate_jwt({"device_id": device.id})
    return jsonify({"token": token})


@bp.route("/get_key/", methods=["POST"])
@require_device_auth
def get_key():
    """
    Получение ключа
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
            key_number:
              type: string
              example: "101"
            nfcId:
              type: string
              example: "04A224B98C6280"
    responses:
      200:
        description: Результат получения ключа
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [success, error]
            keyId:
              type: integer
            nfcId:
              type: string
            keySlotNumber:
              type: string
    """
    data = request.get_json()
    key_number = data.get("number")
    nfc_id = data.get("nfcId")

    if not key_number or not nfc_id:
        return jsonify({"status": "error", "message": "Некорректные входные данные"}), 400

    user = User.query.filter_by(nfc_tag=nfc_id).first()
    key = Key.query.filter_by(key_number=key_number).first()
    device = Device.query.get(request.device_id)

    if not user or not key or not device:
        return jsonify({"status": "error", "message": "Пользователь, ключ или устройство не найдены"}), 400

    if key.assigned_role_id and user.role_id != key.assigned_role_id:
        return jsonify({"status": "error", "message": "Данный ключ вам недоступен"}), 403

    if key.is_taken:
        return jsonify({"status": "error", "message": "Данный ключ уже забран"}), 400

    key_slot_number = key.key_slot.number if key.key_slot else None

    key.is_taken = True
    key.key_slot_id = None
    key.last_user_id = user.id
    key.last_device_id = device.id

    # Добавление записи в Operation
    operation = Operation(
        user_id=user.id,
        key_id=key.id,
        device_id=device.id,
        type='TAKE',
        timestamp = datetime.utcnow()
    )
    db.session.add(operation)
    db.session.commit()

    return jsonify({
        "status": "success",
        "keyUuid": key.id,
        "keySlotNumber": key_slot_number
    }), 200



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
            keySlotNumber:
              type: string
              example: "10"
            keyId:
              type: integer
              example: 42
            nfcId:
              type: string
              example: "04A224B98C6280"
    responses:
      200:
        description: Результат возврата ключа
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [success, error]
            keyId:
              type: integer
            nfcId:
              type: string
            keySlotNumber:
              type: string
    """
    data = request.get_json()
    key_slot_number = data.get("keySlotNumber")
    key_id = data.get("keyId")
    nfc_id = data.get("nfcId")

    if not key_slot_number or not key_id or not nfc_id:
        return jsonify({"status": "error"}), 400

    key = Key.query.get(key_id)
    user = User.query.filter_by(nfc_tag=nfc_id).first()
    device = Device.query.get(request.device_id)

    if not key or not key.is_taken or not user or not device:
        return jsonify({"status": "error"}), 400

    key_slot = KeySlot.query.filter_by(
        number=int(key_slot_number),
        device_id=device.id
    ).first()

    if not key_slot:
        return jsonify({"status": "error"}), 404
    if key_slot.is_locked or key_slot.key is not None:
        return jsonify({"status": "error", "message": "Slot already in use"}), 400

    key.is_taken = False
    key.key_slot_id = key_slot.id
    key.last_user_id = user.id
    key.last_device_id = device.id

    # Добавление записи в Operation
    operation = Operation(
        user_id=user.id,
        key_id=key.id,
        device_id=device.id,
        type='RETURN',
        timestamp=datetime.utcnow()
    )
    db.session.add(operation)
    db.session.commit()

    return jsonify({
        "status": "success",
        "keyId": key.id,
        "nfcId": nfc_id,
        "keySlotNumber": key_slot.number
    }), 200


@bp.route("/get_empty_slot/", methods=["GET"])
@require_device_auth
def get_empty_slot():
    """
    Получить свободную ячейку устройства
    ---
    tags:
      - Device
    security:
      - BearerAuth: []  # токен устройства
    responses:
      200:
        description: Свободная ячейка найдена
      404:
        description: Нет свободных ячеек
    """
    device = Device.query.get(request.device_id)
    if not device:
        return jsonify({"status": "error", "reason": "Устройство не найдено"}), 404

    # Найдём ячейку, если:
    # - key_slot относится к текущему устройству
    # - либо нет связанного ключа (Key), либо он есть, но key_number = None
    empty_slot = (
        KeySlot.query
        .filter_by(device_id=device.id)
        .outerjoin(Key)
        .filter((Key.id == None) | (Key.key_number == None))
        .order_by(KeySlot.number.asc())
        .first()
    )

    if not empty_slot:
        return jsonify({"status": "error", "reason": "Нет свободной ячейки"}), 404

    return jsonify({
        "status": "success",
        "keySlotNumber": empty_slot.number,
        "keySlotId": empty_slot.id
    })




# @bp.route("/free_keyslot/", methods=["GET"])
# @require_device_auth
# def get_empty_slot():
#     """
#     Получить номер свободной ячейки
#     ---
#     tags:
#       - Admin - KeySlot
#     security:
#       - BearerAuth: []
#     responses:
#       200:
#         description: Свободная ячейка найдена
#         content:
#           application/json:
#             schema:
#               type: object
#               properties:
#                 status:
#                   type: string
#                   example: ok
#                 keyslot_number:
#                   type: integer
#       404:
#         description: Нет свободных ячеек
#     """
#     keyslot = KeySlot.query.filter_by(status="free").first()
#     if not keyslot:
#         return jsonify({"status": "error", "reason": "No free key slots available"}), 404
#
#     return jsonify({"status": "ok", "keyslot_number": keyslot.number}), 200
