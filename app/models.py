from . import db
import uuid
from datetime import datetime


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), unique=True, nullable=False, default=lambda: f"user_{uuid.uuid4().hex[:8]}")
    name = db.Column(db.String)
    nfc_tag = db.Column(db.String, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', backref='users')


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String, unique=True)
    ip_address = db.Column(db.String)
    auth_token = db.Column(db.String, unique=True)
    timeout = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class KeySlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    device_device_id = db.Column(db.String, db.ForeignKey('device.device_id'), nullable=False)
    device = db.relationship('Device', backref='key_stores', foreign_keys=[device_device_id])

class Key(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key_uuid = db.Column(db.String(40), unique=True, nullable=False)  # Уникальный идентификатор ключа
    key_number = db.Column(db.String(20), unique=True, nullable=False)  # Уникальный номер ключа
    status = db.Column(db.String(20), nullable=True)  # in_store | taken по дефолту null - При создании ключа

    key_slot_id = db.Column(db.Integer, db.ForeignKey('key_slot.id'), nullable=True)
    key_slot = db.relationship('KeySlot', backref='keys', uselist=False)

    assigned_role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    assigned_role = db.relationship('Role')

    last_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    last_user = db.relationship('User')

    last_device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    last_device = db.relationship('Device')

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Operation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    key_id = db.Column(db.Integer, db.ForeignKey('key.id'))
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    type = db.Column(db.String)  # "take" | "return"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')
    key = db.relationship('Key')
    device = db.relationship('Device')