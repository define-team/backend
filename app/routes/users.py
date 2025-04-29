from flask import Blueprint, request, jsonify
from app.models import User, Role, db
from app.utils.decorators import require_device_auth

bp = Blueprint("user", __name__, url_prefix="/device")



@bp.route("/create_user/", methods=["POST"])
def create_user():
    """
        Создать нового пользователя
        ---
        tags:
          - Users
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
                user_id:
                  type: string
                  example: "user123"
                nfc_tag:
                  type: string
                  example: "04A224B98C6280"
                roles:
                  type: array
                  items:
                    type: string
                  example: ["admin", "user"]
        responses:
          200:
            description: Пользователь успешно создан
          400:
            description: Ошибка запроса
          404:
            description: Роль не найдена
        """
    data = request.get_json()
    name = data.get("name")
    user_id = data.get("user_id")
    nfc_tag = data.get("nfc_tag")
    role_names = data.get("roles", [])

    if not all([name, user_id, nfc_tag, role_names]):
        return jsonify({"status": "error", "reason": "Missing fields"}), 400

    roles = Role.query.filter(Role.name.in_(role_names)).all()
    if len(roles) != len(role_names):
        return jsonify({"status": "error", "reason": "One or more roles not found"}), 404

    new_user = User(name=name, user_id=user_id, nfc_tag=nfc_tag)
    new_user.roles.extend(roles)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"status": "ok", "user_id": new_user.user_id})

@bp.route("/update_user/<string:user_id>/", methods=["PUT"])
def update_user(user_id):
    """
    Обновить данные пользователя
    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
        description: ID пользователя для обновления
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
            roles:
              type: array
              items:
                type: string
              example: ["admin", "user"]
    responses:
      200:
        description: Пользователь успешно обновлён
      400:
        description: Ошибка запроса
      404:
        description: Пользователь не найден
    """
    data = request.get_json()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"status": "error", "reason": "User not found"}), 404

    name = data.get("name")
    nfc_tag = data.get("nfc_tag")
    role_names = data.get("roles", [])

    if name:
        user.name = name
    if nfc_tag:
        user.nfc_tag = nfc_tag
    if role_names:
        roles = Role.query.filter(Role.name.in_(role_names)).all()
        if len(roles) != len(role_names):
            return jsonify({"status": "error", "reason": "One or more roles not found"}), 404
        user.roles = roles

    db.session.commit()
    return jsonify({"status": "ok", "user_id": user.user_id})



@bp.route("/delete_user/<string:user_id>/", methods=["DELETE"])
def delete_user(user_id):
    """
        Удалить пользователя
        ---
        tags:
          - Users
        parameters:
          - in: path
            name: user_id
            type: string
            required: true
            description: ID пользователя
        responses:
          200:
            description: Пользователь успешно удалён
          404:
            description: Пользователь не найден
        """
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"status": "error", "reason": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({"status": "ok", "message": f"User {user_id} deleted"})
