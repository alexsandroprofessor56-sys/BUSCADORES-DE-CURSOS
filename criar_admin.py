import os

from app import app, bcrypt
from core import db
from core.models import User

with app.app_context():
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    user = User.query.filter_by(username=username).first()
    if user:
        user.password = password_hash
        db.session.commit()
        print(f"Usuário admin atualizado: {username}")
    else:
        novo_admin = User(username=username, password=password_hash)
        db.session.add(novo_admin)
        db.session.commit()
        print(f"Usuário admin criado: {username}")

    print("Senha definida a partir de ADMIN_PASSWORD ou padrão local admin123.")
