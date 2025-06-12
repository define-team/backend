#general commit
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flasgger import Swagger
from flask_cors import CORS

from config import Config  # Загружаем класс конфигурации
import os

db = SQLAlchemy()
migrate = Migrate()

def register_blueprints(app):
    from app.routes.device import bp as device_bp
    from app.routes.admin import bp

    app.register_blueprint(device_bp, url_prefix='/device')
    app.register_blueprint(bp, url_prefix='/admin')

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    cors = CORS(
        app,
        resources={
            r"/*": {
                "origins": ['http://localhost:8080','http://localhost:8000'
                , 'https://ваш-домен.com', "*",'http://localhost:3000',
                'http://127.0.0.1:5000',
                'http://172.18.0.3:5000'],
                "allow_headers": ["Authorization", "Content-Type"]
            }
        }
    )
    # Подключаем CORS
    # CORS(app, resources={r"/*": {"origins": "*"}})  # Разрешены все домены
    # CORS(app, resources={r"/*": {"origins": ["http://localhost:5173"]}})

    db.init_app(app)
    migrate.init_app(app, db)

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Smart Keybox API",
            "description": "API для управления ключами, пользователями и устройствами",
            "version": "1.0.0"
        },
        "securityDefinitions": {
            "BearerAuth": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "Введите токен в формате **Bearer <ваш JWT>**"
            }
        },
        "security": [
            {
                "BearerAuth": []
            }
        ]
    }

    Swagger(app, template=swagger_template)

    with app.app_context():
        from app import models
        print("Creating all tables...")
        db.create_all()

    register_blueprints(app)

    return app




