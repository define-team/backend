#general commit
from . import db
import uuid
from datetime import datetime
from enum import Enum

class OperationType(Enum):
    TAKE = "take"
    RETURN = "return"

class Role(db.Model):
    id = db.Column(db.String(64), primary_key=True, unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:8])
    name = db.Column(db.String, unique=True, nullable=False)
    users = db.relationship('User', back_populates='role')
    assigned_keys = db.relationship('Key', back_populates='assigned_role')


class User(db.Model):
    id = db.Column(db.String(64), primary_key=True, unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:8])
    name = db.Column(db.String)
    nfc_tag = db.Column(db.String, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    role_id = db.Column(db.String, db.ForeignKey('role.id'))
    role = db.relationship('Role', back_populates='users')
    used_keys = db.relationship('Key', back_populates='last_user')
    operations = db.relationship('Operation', back_populates='user')


class Device(db.Model):
    id = db.Column(db.String(64), primary_key=True, unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:8])
    ip_address = db.Column(db.String)
    auth_token = db.Column(db.String, unique=True)
    timeout = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    key_stores = db.relationship('KeySlot', back_populates='device')
    used_keys = db.relationship('Key', back_populates='last_device')
    operations = db.relationship('Operation', back_populates='device')


class KeySlot(db.Model):
    id = db.Column(db.String(64), primary_key=True, unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:8])
    number = db.Column(db.Integer, nullable=False)
    is_locked = db.Column(db.Boolean, default=False)
    device_id = db.Column(db.String, db.ForeignKey('device.id'), nullable=False)
    device = db.relationship('Device', back_populates='key_stores')
    key = db.relationship(
        'Key',
        back_populates='key_slot',
        uselist=False,
        passive_deletes=True
    )
    __table_args__ = (
        db.UniqueConstraint('number', 'device_id', name='uq_slot_per_device'),
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class Key(db.Model):
    id = db.Column(db.String(40), primary_key=True, unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:8])
    key_number = db.Column(db.String(20), unique=True, nullable=False)
    is_taken = db.Column(db.Boolean, default=False)
    key_slot_id = db.Column(db.String, db.ForeignKey('key_slot.id', ondelete='SET NULL'), nullable=True)
    key_slot = db.relationship('KeySlot', back_populates='key', post_update=True)
    assigned_role_id = db.Column(db.String, db.ForeignKey('role.id'), nullable=False)
    assigned_role = db.relationship('Role', back_populates='assigned_keys')
    last_user_id = db.Column(db.String, db.ForeignKey('user.id'), nullable=True)
    last_user = db.relationship('User', back_populates='used_keys')
    last_device_id = db.Column(db.String, db.ForeignKey('device.id'), nullable=True)
    last_device = db.relationship('Device', back_populates='used_keys')
    operations = db.relationship('Operation', back_populates='key')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class Operation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('user.id'))
    key_id = db.Column(db.String, db.ForeignKey('key.id'))
    device_id = db.Column(db.String, db.ForeignKey('device.id'))
    type = db.Column(db.Enum('TAKE', 'RETURN', name='operationtype'), nullable=False)
    # type = db.Column(db.String)  # "take" | "return"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='operations')
    key = db.relationship('Key', back_populates='operations')
    device = db.relationship('Device', back_populates='operations')
