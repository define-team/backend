from . import db
import uuid
import jwt
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


class Key(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key_number = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), default="available", nullable=False)
    assigned_role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    last_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    last_device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Operation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    key_id = db.Column(db.Integer, db.ForeignKey('key.id'))
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    type = db.Column(db.String)  # take/return
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
