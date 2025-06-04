from flask import Blueprint, request, jsonify
from app.models import Device, User, Key, Operation, KeySlot, db
from app.utils.jwt_utils import generate_jwt
from app.utils.decorators import require_device_auth
from datetime import datetime
import logging

bp = Blueprint("device", __name__, url_prefix="")


@bp.route("/auth_card/", methods=["POST"])
@require_device_auth
def scan_card():
    """
        Валидация NFC карты
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
            description: Карта успешно валидирована
            schema:
              type: object
              properties:
                status:
                  type: string
                  enum: [success]
          401:
            description: Ошибка валидации карты
            schema:
              type: object
              properties:
                status: 
                  type: string
                  enum: [error]
    """
    data = request.get_json()
    nfc_id = data.get("nfcId")

    if not nfc_id:
        return jsonify({"status": "error"}), 401

    user = User.query.filter_by(nfc_tag=nfc_id).first()

    if user:
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error"}), 401


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
                number:
                  type: string
                  example: "101"
                  description: Номер ключа
                nfcId:
                  type: string
                  example: "04A224B98C6280"
                  description: Идентификатор NFC пользователя
              required:
                - number
                - nfcId
        responses:
          200:
            description: Результат запроса ключа
            schema:
              oneOf:
                - type: object
                  properties:
                    status:
                      type: string
                      example: "error"
                    errorCode:
                      type: string
                      example: "bad_request"
                - type: object
                  properties:
                    keySlotNumber:
                      type: string
                      example: "10"
                      description: Номер ячейки ключа (если есть)
                    keyUuid:
                      type: string
                      example: "uuid-1234"
          401:
            description: Ошибка авторизации устройства
    """
    data = request.get_json()
    key_number = data.get("number")
    nfc_id = data.get("nfcId")

    if not key_number or not nfc_id:
        return jsonify({"status": "error", "errorCode": "bad_request"}), 400

    user = User.query.filter_by(nfc_tag=nfc_id).first()
    key = Key.query.filter_by(key_number=key_number).first()

    if not user or not key:
        return jsonify({"status": "error", "errorCode": "not_found"}), 400

    if key.status == "taken":
        return jsonify({"status": "error", "errorCode": "already_taken"}), 400

    if key.assigned_role_id and (not user.role or user.role.id != key.assigned_role_id):
        return jsonify({"status": "error", "errorCode": "no_access"}), 401

    key_slot_number = key.key_slot.number if key.key_slot else None

    key.status = "taken"
    key.last_user_id = user.id
    key.last_device_id = request.device_id
    key.key_slot_id = None
    key.updated_at = datetime.utcnow()

    db.session.add(Operation(
        user_id=user.id,
        key_id=key.id,
        device_id=request.device_id,
        type="take",
        timestamp=datetime.utcnow()
    ))

    db.session.commit()

    return jsonify({
        "keySlotNumber": key_slot_number,
        "keyUuid": key.key_uuid
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
                  example: "1"
                  description: Номер ячейки ключа
                keyUuid:
                  type: string
                  example: "uuid1"
                  description: Идентификатор ключа
                nfcId:
                  type: string
                  example: "04A224B98C6280"
                  description: Идентификатор NFC пользователя (необязательно)
              required:
                - keySlotNumber
                - keyUuid
        responses:
          200:
            description: Результат возврата ключа
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: "success"
          401:
            description: Ошибка авторизации устройства
    """
    data = request.get_json()
    key_slot_number = data.get("keySlotNumber")
    key_uuid = data.get("keyUuid")
    nfc_id = data.get("nfcId")

    if not key_slot_number or not key_uuid:
        return jsonify({"status": "error", "errorCode": "bad_request"}), 400

    key = Key.query.filter_by(key_uuid=key_uuid).first()
    if not key:
        return jsonify({"status": "error", "errorCode": "key_not_found"}), 400

    if key.status == "in_store":
        return jsonify({"status": "error", "errorCode": "already_returned"}), 400

    device = Device.query.get(request.device_id)
    if not device:
        return jsonify({"status": "error", "errorCode": "device_not_found"}), 401

    key_slot = KeySlot.query.filter_by(number=key_slot_number, device_device_id=device.device_id).first()
    if not key_slot:
        return jsonify({"status": "error", "errorCode": "key_slot_not_found"}), 404

    key.status = "in_store"
    key.key_slot_id = key_slot.id
    key.last_device_id = request.device_id
    key.updated_at = datetime.utcnow()

    if nfc_id:
        user = User.query.filter_by(nfc_tag=nfc_id).first()
        if user:
            key.last_user_id = user.id

    db.session.add(Operation(
        user_id=key.last_user_id,
        key_id=key.id,
        device_id=request.device_id,
        type="return",
        timestamp=datetime.utcnow()
    ))

    db.session.commit()

    return jsonify({"status": "success"}), 200


@bp.route("/get_empty_slot/", methods=["GET"])
@require_device_auth
def get_empty_slot():
    """
    Получить свободную ячейку устройства
    ---
    tags:
      - Device
    responses:
      200:
        description: Свободная ячейка найдена
      404:
        description: Нет свободных ячеек
    """
    # 1. Найдём устройство по внутреннему ID
    device = Device.query.get(request.device_id)
    if not device:
        return jsonify({"status": "error", "reason": "Устройство не найдено"}), 404

    # 2. Используем device.device_id для фильтрации
    empty_slot = (
        KeySlot.query
        .filter_by(device_device_id=device.device_id)
        .outerjoin(Key, Key.key_slot_id == KeySlot.id)
        .filter(Key.id == None)
        .order_by(KeySlot.number.asc())
        .first()
    )

    logging.warning(f"device_id (external): {device.device_id}")

    if not empty_slot:
        return jsonify({"status": "error", "reason": "Нет свободной ячейки"}), 404

    return jsonify({"status": "ok", "keySlotNumber": empty_slot.number})
