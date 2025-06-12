from flask import Blueprint, request, jsonify
from app.models import User, Role, db, Key, Operation, Device, KeySlot
from app.utils.decorators import require_admin_auth
from sqlalchemy.orm import joinedload
import uuid
import jwt
from datetime import datetime, timedelta

bp = Blueprint("admin", __name__, url_prefix="/admin")

from app.utils.admin_jwt_utils import generate_admin_jwt

@bp.route("/login/", methods=["POST"])
def admin_login():
    """
    Админ логин
    ---
    tags:
      - Admin
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              example: "admin"
            password:
              type: string
              example: "admin1234"
    responses:
      200:
        description: Токен успешно выдан
      401:
        description: Неверный логин или пароль
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if username != "admin" or password != "admin1234":
        return jsonify({"error": "Unauthorized"}), 401

    try:
        token = generate_admin_jwt(admin_id=1)  # Подставь актуальный ID, если берёшь из БД
        return jsonify({"token": token})
    except Exception as e:
        print(f"Ошибка генерации токена: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/operations/", methods=["GET"])
@require_admin_auth
def get_operations():
    """
        Получить логи операций
        ---
        tags:
          - Admin - Operations
        security:
          - BearerAuth: []  # токен админа
        parameters:
          - in: query
            name: user_id
            type: string
            required: false
            description: Фильтрация по ID пользователя
          - in: query
            name: key_number
            type: integer
            required: false
            description: Фильтрация по номеру ключа
          - in: query
            name: device_id
            type: integer
            required: false
            description: Фильтрация по ID устройства
        responses:
          200:
            description: Список операций
        """
    user_id = request.args.get("user_id")
    key_number = request.args.get("key_number")
    device_id = request.args.get("device_id")

    query = Operation.query.options(
        joinedload(Operation.user),
        joinedload(Operation.key),
        joinedload(Operation.device)
    )

    if user_id:
        query = query.join(User).filter(User.id == user_id)
    if key_number:
        query = query.join(Key).filter(Key.key_number == key_number)
    if device_id:
        query = query.join(Device).filter(Device.id == device_id)

    operations = query.order_by(Operation.timestamp.desc()).all()

    result = []
    for op in operations:
        result.append({
            "id": op.id,
            "user_id": op.user.id if op.user else None,
            "key_number": op.key.key_number if op.key else None,
            "device_id": op.device.id if op.device else None,
            "type": op.type,
            "timestamp": op.timestamp.isoformat()
        })

    try:
        return jsonify(result)
    except Exception as e:
        print(f"Ошибка : {e}")
        return jsonify({"error": str(e)}), 500



@bp.route("/create_device/", methods=["POST"])
@require_admin_auth
def create_device():
    """
    Создать новое устройство
    ---
    tags:
      - Admin - Devices
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            ip_address:
              type: string
              example: "192.168.1.10"
            auth_token:
              type: string
              example: "super_secret_key"
            timeout:
              type: integer
              example: 30
    responses:
      200:
        description: Устройство успешно создано
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                device:
                  type: object
                  properties:
                    id:
                      type: string
                    ip_address:
                      type: string
                    auth_token:
                      type: string
                    timeout:
                      type: integer
                    created_at:
                      type: string
                      example: "2025-06-05T12:00:00"
      400:
        description: Ошибка запроса или токен уже используется
    """


    data = request.get_json()
    ip = data.get("ip_address")
    token = data.get("auth_token")
    timeout = data.get("timeout")

    if token and Device.query.filter_by(auth_token=token).first():
        return jsonify({"status": "error", "reason": "Auth token already used"}), 400

    new_device = Device(ip_address=ip, auth_token=token, timeout=timeout)
    db.session.add(new_device)
    db.session.commit()

    return jsonify({
        "status": "ok",
        "device": {
            "id": new_device.id,
            "ip_address": new_device.ip_address,
            "auth_token": new_device.auth_token,
            "timeout": new_device.timeout,
            "created_at": new_device.created_at.isoformat()
        }
    })



@bp.route("/update_device/<string:device_id>/", methods=["PUT"])
@require_admin_auth
def update_device(device_id):
    """
    Обновить данные устройства
    ---
    tags:
      - Admin - Devices
    security:
      - BearerAuth: []
    parameters:
      - name: device_id
        in: path
        required: true
        schema:
          type: string
        description: Уникальный ID устройства
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            ip_address:
              type: string
              example: "192.168.1.20"
            auth_token:
              type: string
              example: "new_secret_key"
            timeout:
              type: integer
              example: 60
    responses:
      200:
        description: Устройство обновлено
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                device:
                  type: object
                  properties:
                    id:
                      type: string
                    ip_address:
                      type: string
                    auth_token:
                      type: string
                    timeout:
                      type: integer
                    updated_at:
                      type: string
                      example: "2025-06-05T12:30:00"
      400:
        description: Ошибка запроса
      404:
        description: Устройство не найдено
    """


    device = Device.query.filter_by(id=device_id).first()
    if not device:
        return jsonify({"status": "error", "reason": "Device not found"}), 404

    data = request.get_json()
    if "ip_address" in data:
        device.ip_address = data["ip_address"]
    if "auth_token" in data:
        device.auth_token = data["auth_token"]
    if "timeout" in data:
        device.timeout = data["timeout"]

    db.session.commit()

    return jsonify({
        "status": "ok",
        "device": {
            "id": device.id,
            "ip_address": device.ip_address,
            "auth_token": device.auth_token,
            "timeout": device.timeout,
            "updated_at": device.updated_at.isoformat()
        }
    })


@bp.route("/delete_device/<string:device_id>/", methods=["DELETE"])
@require_admin_auth
def delete_device(device_id):
    """
    Удалить устройство
    ---
    tags:
      - Admin - Devices
    security:
      - BearerAuth: []
    parameters:
      - name: device_id
        in: path
        required: true
        schema:
          type: string
        description: Уникальный ID устройства
    responses:
      200:
        description: Устройство удалено
      400:
        description: В устройстве есть ключи
      404:
        description: Устройство не найдено
    """
    device = Device.query.filter_by(id=device_id).first()
    if not device:
        return jsonify({"status": "error", "reason": "Device not found"}), 404

    # Проверка: все ли ячейки устройства пусты
    non_empty_slots = [slot for slot in device.key_stores if slot.key is not None]
    if non_empty_slots:
        return jsonify({
            "status": "error",
            "reason": "Device contains keys in its slots. Remove them before deletion."
        }), 400

    db.session.delete(device)
    db.session.commit()
    return jsonify({"status": "ok", "message": f"Device {device_id} deleted"})



@bp.route("/list_devices/", methods=["GET"])
@require_admin_auth
def list_devices():
    """
    Получить список всех устройств
    ---
    tags:
      - Admin - Devices
    security:
      - BearerAuth: []
    responses:
      200:
        description: Список устройств
        content:
          application/json:
            schema:
              type: object
              properties:
                devices:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                      ip_address:
                        type: string
                      auth_token:
                        type: string
                      timeout:
                        type: integer
                      created_at:
                        type: string
                      updated_at:
                        type: string
    """
    devices = Device.query.all()
    device_list = [{
        "id": d.id,
        "ip_address": d.ip_address,
        "auth_token": d.auth_token,
        "timeout": d.timeout,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat()
    } for d in devices]

    return jsonify({"devices": device_list})


# --- Keys ---
@bp.route("/create_key/", methods=["POST"])
@require_admin_auth
def create_key():
    """
    Создать новый ключ
    ---
    tags:
      - Admin - Keys
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - key_number
            - assigned_role_id
            - key_slot_id
          properties:
            key_number:
              type: string
              example: "101"
            assigned_role_id:
              type: string
              example: "role1"
            key_slot_id:
              type: string
              example: "slot1"
    responses:
      200:
        description: Ключ успешно создан
        schema:
          type: object
          properties:
            id:
              type: string
            key_number:
              type: string
            is_taken:
              type: boolean
            key_slot_id:
              type: string
            assigned_role_id:
              type: string
      400:
        description: Ошибка запроса или ключ уже существует
      404:
        description: Роль или ячейка не найдены
    """

    data = request.get_json()
    key_number = data.get("key_number")
    role_id = data.get("assigned_role_id")
    slot_id = data.get("key_slot_id")

    if not key_number or not role_id or not slot_id:
        return jsonify({"status": "error", "reason": "Missing required field(s)"}), 400

    if Key.query.filter_by(key_number=key_number).first():
        return jsonify({"status": "error", "reason": "Key already exists"}), 400

    # Проверка роли
    role = Role.query.get(role_id)
    if not role:
        return jsonify({"status": "error", "reason": "Role not found"}), 400

    # Проверка ячейки
    slot = KeySlot.query.get(slot_id)
    if not slot:
        return jsonify({"status": "error", "reason": "Slot not found"}), 404
    if slot.key:
        return jsonify({"status": "error", "reason": "Slot already occupied"}), 400

    new_key = Key(
        key_number=key_number,
        assigned_role_id=role_id,
        key_slot=slot,
        is_taken=False  # по умолчанию
    )

    db.session.add(new_key)
    db.session.commit()

    return jsonify({
        "status": "ok",
        "id": new_key.id,
        "key_number": new_key.key_number,
        "is_taken": new_key.is_taken,
        "key_slot_id": new_key.key_slot_id,
        "assigned_role_id": new_key.assigned_role_id,
        "created_at": new_key.created_at.isoformat()
    })




@bp.route("/update_key/<string:key_id>/", methods=["PUT"])
@require_admin_auth
def update_key(key_id):
    """
    Обновить данные ключа
    ---
    tags:
      - Admin - Keys
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: key_id
        type: string
        required: true
        description: ID ключа
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            key_number:
              type: string
              example: "102"
            assigned_role_id:
              type: string
              example: "role2"
            key_slot_id:
              type: string
              example: "slot2"
    responses:
      200:
        description: Ключ успешно обновлён
        schema:
          type: object
          properties:
            id:
              type: string
            key_number:
              type: string
            key_slot_id:
              type: string
            assigned_role_id:
              type: string
      400:
        description: Ошибка запроса
      404:
        description: Ключ или ячейка не найдены
    """

    data = request.get_json()
    key = Key.query.get(key_id)
    if not key:
        return jsonify({"status": "error", "reason": "Key not found"}), 404

    new_number = data.get("key_number")
    new_role_id = data.get("assigned_role_id")
    new_slot_id = data.get("key_slot_id")

    # Проверка уникальности номера ключа
    if new_number and new_number != key.key_number:
        if Key.query.filter_by(key_number=new_number).first():
            return jsonify({"status": "error", "reason": "Key number already exists"}), 400
        key.key_number = new_number

    # Проверка существования роли
    if new_role_id:
        role = Role.query.get(new_role_id)
        if not role:
            return jsonify({"status": "error", "reason": "Role not found"}), 400
        key.assigned_role_id = new_role_id

    # Проверка существования и доступности ячейки
    if new_slot_id and new_slot_id != key.key_slot_id:
        new_slot = KeySlot.query.get(new_slot_id)
        if not new_slot:
            return jsonify({"status": "error", "reason": "Slot not found"}), 404
        if new_slot.key and new_slot.key.id != key.id:
            return jsonify({"status": "error", "reason": "Slot already occupied"}), 400

        # Освобождаем старую ячейку
        if key.key_slot:
            key.key_slot.key = None

        key.key_slot = new_slot

    db.session.commit()

    return jsonify({
        "status": "ok",
        "id": key.id,
        "key_number": key.key_number,
        "key_slot_id": key.key_slot_id,
        "assigned_role_id": key.assigned_role_id,
        "updated_at": key.updated_at.isoformat()
    })



@bp.route("/delete_key/<string:key_id>/", methods=["DELETE"])
@require_admin_auth
def delete_key(key_id):
    """
    Удалить ключ
    ---
    tags:
      - Admin - Keys
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: key_id
        type: string
        required: true
        description: ID ключа для удаления
    responses:
      200:
        description: Ключ успешно удалён и ячейка освобождена
      404:
        description: Ключ не найден
    """

    key = Key.query.get(key_id)
    if not key:
        return jsonify({"status": "error", "reason": "Key not found"}), 404

    if key.key_slot:
        key.key_slot.key = None

    db.session.delete(key)
    db.session.commit()

    return jsonify({
        "status": "ok",
        "message": f"Key with id {key_id} deleted"
    })




@bp.route("/keys/", methods=["GET"])
@require_admin_auth
def list_keys():
    """
        Получить список всех ключей
        ---
        tags:
          - Admin - Keys
        security:
          - BearerAuth: []  # токен админа
        responses:
          200:
            description: Список ключей
    """
    keys = Key.query.all()
    result = []
    for key in keys:
        result.append({
            "key_number": key.key_number,
            "id": key.id,
            "is_taken": key.is_taken,
            "key_slot_id": key.key_slot_id,
            "assigned_role_id": key.assigned_role_id,
            "device_id": key.key_slot.device_id if key.key_slot else None,
            "created_at": key.created_at.isoformat() if key.created_at else None,
            "updated_at": key.updated_at.isoformat() if key.updated_at else None
        })
    return jsonify(result)




@bp.route("/create_slot/", methods=["POST"])
@require_admin_auth
def create_slot():
    """
    Создать новую ячейку
    ---
    tags:
      - Admin - KeySlot
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            slot_number:
              type: integer
              example: 5
            device_id:
              type: string
              example: "device_123"
    responses:
      200:
        description: Ячейка успешно создана
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                slot_id:
                  type: integer
                  example: 1
                number:
                  type: integer
                  example: 5
                is_locked:
                  type: boolean
                  example: false
                device_id:
                  type: string
                  example: "device_123"
                created_at:
                  type: string
                  example: "2025-06-05T12:00:00"
      400:
        description: Ошибка запроса или слот уже существует
      404:
        description: Устройство не найдено
    """
    data = request.get_json()
    slot_number = data.get("slot_number")
    device_id = data.get("device_id")

    if not all([slot_number, device_id]):
        return jsonify({"error": "Missing slot_number or device_id"}), 400

    device = Device.query.filter_by(id=device_id).first()
    if not device:
        return jsonify({"error": "Device not found"}), 404

    # Проверка уникальности номера внутри устройства
    if KeySlot.query.filter_by(number=slot_number, device_id=device.id).first():
        return jsonify({"error": "Slot already exists for this device"}), 400

    slot = KeySlot(number=slot_number, device_id=device.id)
    db.session.add(slot)
    db.session.commit()

    return jsonify({
        "status": "ok",
        "id": slot.id,
        "number": slot.number,
        "is_locked": slot.is_locked,
        "device_id": device.id,
        "created_at": slot.created_at.isoformat()
    })


# @bp.route("/update_slot/<string:slot_id>/", methods=["PUT"])
# @require_admin_auth
# def update_slot(slot_id):
#     """
#     Обновить данные ячейки
#     ---
#     tags:
#       - Admin - KeySlot
#     security:
#       - BearerAuth: []
#     parameters:
#       - name: slot_id
#         in: path
#         required: true
#         schema:
#           type: string
#         description: Уникальный ID ячейки (slot_id)
#       - in: body
#         name: body
#         required: true
#         schema:
#           type: object
#           properties:
#             is_locked:
#               type: boolean
#               example: true
#     responses:
#       200:
#         description: Ячейка обновлена
#         content:
#           application/json:
#             schema:
#               type: object
#               properties:
#                 status:
#                   type: string
#                   example: ok
#                 slot_id:
#                   type: string
#                   example: "a1b2c3d4"
#                 number:
#                   type: integer
#                 is_locked:
#                   type: boolean
#                 device_id:
#                   type: string
#                 updated_at:
#                   type: string
#                   example: "2025-06-05T12:30:00"
#       400:
#         description: Ошибка запроса
#       404:
#         description: Ячейка не найдена
#     """
#     data = request.get_json()
#
#     slot = KeySlot.query.filter_by(id=slot_id).first()
#     if not slot:
#         return jsonify({"error": "Slot not found"}), 404
#
#     is_locked = data.get("is_locked")
#     if is_locked is not None:
#         slot.is_locked = bool(is_locked)
#
#     db.session.commit()
#     return jsonify({
#         "status": "ok",
#         "slot_id": slot.id,
#         "number": slot.number,
#         "is_locked": slot.is_locked,
#         "device_id": slot.device_id,
#         "updated_at": slot.updated_at.isoformat()
#     })


@bp.route("/delete_slot/<string:slot_id>/", methods=["DELETE"])
@require_admin_auth
def delete_slot(slot_id):
    """
    Удалить ячейку
    ---
    tags:
      - Admin - KeySlot
    security:
      - BearerAuth: []
    parameters:
      - name: slot_id
        in: path
        required: true
        schema:
          type: string
        description: Уникальный ID ячейки (slot_id)
    responses:
      200:
        description: Ячейка удалена
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                message:
                  type: string
                  example: Slot a1b2c3d4 deleted from device device_123
      400:
        description: Ячейка занята
      404:
        description: Ячейка не найдена
    """
    slot = KeySlot.query.filter_by(id=slot_id).first()
    if not slot:
        return jsonify({"error": "Slot not found"}), 404

    if slot.key:
        return jsonify({"error": "Slot is occupied"}), 400

    device_id = slot.device_id
    db.session.delete(slot)
    db.session.commit()
    return jsonify({"status": "ok", "message": f"Slot with id {slot_id} deleted from device with id{device_id}"})


@bp.route("/slots/", methods=["GET"])
@require_admin_auth
def list_slots():
    """
    Получить список всех ячеек
    ---
    tags:
      - Admin - KeySlot
    security:
      - BearerAuth: []
    responses:
      200:
        description: Список ячеек
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  slot_id:
                    type: string
                    example: "a1b2c3d4"
                  slot_number:
                    type: integer
                    example: 5
                  is_locked:
                    type: boolean
                    example: false
                  device_id:
                    type: string
                    example: "device_123"
                  key_number:
                    type: string
                    example: "key-001"
    """
    slots = KeySlot.query.all()
    result = [{
        "slot_id": s.id,
        "slot_number": s.number,
        "device_id": s.device_id,
        "key_number": s.key.key_number if s.key else None
    } for s in slots]
    return jsonify(result)








@bp.route("/create_user/", methods=["POST"])
@require_admin_auth
def create_user():
    """
            Создать нового пользователя
    ---
    tags:
      - Admin - User
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
              name:
                type: string
                example: "Иван Иванов"
              nfc_tag:
                type: string
                example: "04A224B98C6280"
              role_id:
                type: string
                example: "a1b2c3d4"
    responses:
      200:
        description: Пользователь успешно создан
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                user_id:
                  type: string
                  example: "a1b2c3d4"
                role_id:
                  type: string
                  example: "1"
      400:
        description: Ошибка запроса
      404:
        description: Роль не найдена

    """

    data = request.get_json()
    name = data.get("name")
    nfc_tag = data.get("nfc_tag")
    role_id = data.get("role_id")

    if not all([name, nfc_tag, role_id]):
        return jsonify({"status": "error", "reason": "Missing fields"}), 400

    role = Role.query.filter_by(id=role_id).first()
    if not role:
        return jsonify({"status": "error", "reason": "Role not found"}), 404

    # Проверка уникальности NFC-тега
    if User.query.filter_by(nfc_tag=nfc_tag).first():
        return jsonify({"status": "error", "reason": "NFC tag already exists"}), 400

    try:
        new_user = User(name=name, nfc_tag=nfc_tag, role_id=role.id)
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "reason": str(e)}), 500

    return jsonify({
        "status": "ok",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "nfc_tag": new_user.nfc_tag,
            "created_at": new_user.created_at.isoformat(),
            "role": role.name
        }
    }), 200


@bp.route("/update_user/<string:user_id>/", methods=["PUT"])
@require_admin_auth
def update_user(user_id):
    """
    Обновление данных пользователя (частичное обновление)
    ---
    tags:
      - Admin - User
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: string
        description: Уникальный ID пользователя
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Пётр Петров"
            nfc_tag:
              type: string
              example: "04B193D821AB"
            role_id:
              type: string
              example: "role_a1b2c3"
    responses:
      200:
        description: Пользователь обновлён
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                user:
                  type: object
                  properties:
                    id:
                      type: string
                    name:
                      type: string
                    nfc_tag:
                      type: string
                    role:
                      type: string
                    updated_at:
                      type: string
                      example: "2025-06-05T12:00:00"
      400:
        description: Неверные данные запроса
      404:
        description: Пользователь или роль не найдены
    """


    data = request.get_json()
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"status": "error", "reason": "User not found"}), 404

    # Обновляем только переданные поля
    if "name" in data:
        user.name = data["name"]

    if "nfc_tag" in data:
        nfc_tag = data["nfc_tag"]
        existing_user = User.query.filter_by(nfc_tag=nfc_tag).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({"status": "error", "reason": "NFC tag already in use"}), 400
        user.nfc_tag = nfc_tag

    if "role_id" in data:
        role = Role.query.filter_by(id=data["role_id"]).first()
        if not role:
            return jsonify({"status": "error", "reason": "Role not found"}), 404
        user.role_id = role.id

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "reason": str(e)}), 500

    return jsonify({
        "status": "ok",
        "user": {
            "id": user.id,
            "name": user.name,
            "nfc_tag": user.nfc_tag,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "role": user.role.name if user.role else None
        }
    }), 200


@bp.route("/delete_user/<string:user_id>/", methods=["DELETE"])
@require_admin_auth
def delete_user(user_id):
    """
    Удалить пользователя
    ---
    tags:
      - Admin - User
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: user_id
        required: true
        schema:
          type: string
        description: Уникальный ID пользователя
    responses:
      200:
        description: Пользователь успешно удалён
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                message:
                  type: string
                  example: "User abc123 deleted"
      404:
        description: Пользователь не найден
    """

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"status": "error", "reason": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "ok", "message": f"User deleted"})



@bp.route("/users/", methods=["GET"])
@require_admin_auth
def list_users():
    """
    Получить список всех пользователей
    ---
    tags:
      - Admin - User
    security:
      - BearerAuth: []
    responses:
      200:
        description: Список пользователей
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  user_id:
                    type: string
                  name:
                    type: string
                  nfc_tag:
                    type: string
                  role_id:
                    type: string
                  role_name:
                    type: string
    """

    users = User.query.all()
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "name": user.name,
            "nfc_tag": user.nfc_tag,
            "role_id": user.role_id,
            "role_name": user.role.name if user.role else None
        })
    return jsonify(result)



SECRET_KEY = "your_admin_secret_key"  # тот же, что в декораторе



@bp.route('/roles/', methods=['POST'])
@require_admin_auth
def create_role():
    """
    Создание новой категории сотрудников
    ---
    tags:
      - Admin - Roles
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Преподаватель"
          required:
            - name
    responses:
      201:
        description: Role created successfully
      400:
        description: Role already exists or invalid data
    """
    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({"error": "Role name is required"}), 400

    if Role.query.filter_by(name=name).first():
        return jsonify({"error": "Role already exists"}), 400

    role = Role(name=name)
    db.session.add(role)
    db.session.commit()

    return jsonify({"message": "Role created", "id": role.id}), 201


@bp.route('/roles/', methods=['GET'])
@require_admin_auth
def list_roles():
    """
        Вывод списка всех категорий сотрудников
        ---
        tags:
          - Admin - Roles
        responses:
          200:
            description: List of all roles
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: integer
                      name:
                        type: string
        """
    roles = Role.query.all()
    return jsonify([{"id": role.id, "name": role.name} for role in roles])


@bp.route('/roles/<string:role_id>/', methods=['PUT'])
@require_admin_auth
def update_role(role_id):
    """
    Обновление категории сотрудника
    ---
    tags:
      - Admin - Roles
    parameters:
      - name: role_id
        in: path
        type: string
        required: true
        description: ID роли для обновления
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Научный сотрудник"
          required:
            - name
    responses:
      200:
        description: Role updated successfully
      400:
        description: Invalid input
      404:
        description: Role not found
    """
    data = request.get_json()
    name = data.get('name')

    role = Role.query.get(role_id)
    if not role:
        return jsonify({"error": "Role not found"}), 404

    if not name:
        return jsonify({"error": "New name is required"}), 400

    # Проверка на уникальность названия (без учёта текущей роли)
    existing_role = Role.query.filter(Role.name == name, Role.id != role_id).first()
    if existing_role:
        return jsonify({"error": "Role name already exists"}), 400

    role.name = name
    db.session.commit()

    return jsonify({"message": "Role updated"})



@bp.route('/roles/<string:role_id>/', methods=['DELETE'])
@require_admin_auth
def delete_role(role_id):
    """
    Удаление категории сотрудников
    ---
    tags:
      - Admin - Roles
    parameters:
      - name: role_id
        in: path
        type: string
        required: true
        description: ID of the role to delete
    responses:
      200:
        description: Role deleted successfully
      400:
        description: Role is in use and cannot be deleted
      404:
        description: Role not found
    """
    role = Role.query.get(role_id)
    if not role:
        return jsonify({"error": "Role not found"}), 404

    if role.users or role.assigned_keys:
        return jsonify({
            "error": "Role is assigned to users or keys and cannot be deleted"
        }), 400

    db.session.delete(role)
    db.session.commit()

    return jsonify({"message": "Role deleted"})
