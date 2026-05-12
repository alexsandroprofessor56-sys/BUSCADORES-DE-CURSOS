from datetime import datetime, timezone
from core import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'app_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    otp_secret = db.Column(db.String(64))
    otp_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Curso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(300), nullable=False)
    descricao = db.Column(db.Text)
    plataforma = db.Column(db.String(100))
    certificacao = db.Column(db.String(200))
    confiabilidade = db.Column(db.String(200))
    areas = db.Column(db.String(300))
    exemplos = db.Column(db.Text)
    link_afiliado = db.Column(db.String(500))
    ativo = db.Column(db.Boolean, default=True)
    cliques = db.Column(db.Integer, default=0)
    nivel = db.Column(db.String(50), default='iniciante')
    preco_tipo = db.Column(db.String(20), default='gratuito')
    rating = db.Column(db.Float, default=4.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id'))
    favoritado_por = db.relationship('User', secondary='favorito', backref='favoritos')


favorito = db.Table('favorito',
    db.Column('user_id', db.Integer, db.ForeignKey('app_user.id')),
    db.Column('curso_id', db.Integer, db.ForeignKey('curso.id'))
)


class AccessEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50))
    path = db.Column(db.String(300))
    method = db.Column(db.String(10))
    user_agent = db.Column(db.String(500))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    provider = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    is_bot = db.Column(db.Boolean, default=False)
    is_vpn = db.Column(db.Boolean, default=False)
    is_tor = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class LogAcesso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50))
    data = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'))


class SecurityEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50))
    event_type = db.Column(db.String(100))
    severity = db.Column(db.String(20))
    message = db.Column(db.String(500))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class IPBanido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True, nullable=False)


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.String(500))
