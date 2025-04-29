from .device import bp as device_bp
from .admin import bp as admin_bp
from .keys import bp as key_bp

def register_blueprints(app):
    app.register_blueprint(device_bp)
    app.register_blueprint(admin_bp)

