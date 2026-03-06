from __future__ import annotations

from datetime import UTC, datetime

from flask_login import UserMixin

from extensions import db


class Quote(db.Model):
    __tablename__ = 'quote'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(500), nullable=True, index=True)
    category = db.Column(db.String(500), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None),
                           onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))

    def __repr__(self) -> str:
        return f'<Quote {self.id}>'


class AdminUser(db.Model, UserMixin):
    __tablename__ = 'admin_user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def __repr__(self) -> str:
        return f'<AdminUser {self.username}>'


class Setting(db.Model):
    __tablename__ = 'setting'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=True)


class BackupLog(db.Model):
    __tablename__ = 'backup_log'

    id = db.Column(db.Integer, primary_key=True)
    ran_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    level = db.Column(db.String(10), nullable=False)
    message = db.Column(db.String(500), nullable=False)
