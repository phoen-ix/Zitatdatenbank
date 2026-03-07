import os
import sys

# Must set env vars BEFORE importing app
os.environ['FLASK_TESTING'] = '1'
os.environ['SECRET_KEY'] = 'test-key-not-for-production'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

# Add the app directory to sys.path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
from app import app as _app
from extensions import db as _db


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    _app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'RATELIMIT_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
    })
    with _app.app_context():
        _db.create_all()
    yield _app


@pytest.fixture(autouse=True)
def clean_db(app):
    """Roll back all changes after each test."""
    with app.app_context():
        _db.create_all()
        yield
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def client(app):
    """A Flask test client."""
    return app.test_client()


@pytest.fixture
def make_quote(app):
    """Factory fixture to create quotes."""
    _counter = [0]

    def _make(text=None, author=None, category=None, tags=None):
        from models import Quote, Tag
        _counter[0] += 1
        if text is None:
            text = f'Test quote number {_counter[0]}'
        quote = Quote(text=text, author=author or f'Author{_counter[0]}',
                      category=category)
        _db.session.add(quote)
        _db.session.flush()
        if tags:
            for tag_name in tags:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    _db.session.add(tag)
                    _db.session.flush()
                quote.tags.append(tag)
        _db.session.commit()
        return quote

    return _make


@pytest.fixture
def make_admin(app):
    """Factory fixture to create admin users."""
    def _make(username='admin', password='testpass'):
        from models import AdminUser
        from werkzeug.security import generate_password_hash
        admin = AdminUser(
            username=username,
            password_hash=generate_password_hash(password),
        )
        _db.session.add(admin)
        _db.session.commit()
        return admin

    return _make


@pytest.fixture
def admin_client(app, client, make_admin):
    """A test client logged in as admin."""
    with app.app_context():
        make_admin(username='admin', password='testpass')
    client.post('/login', data={'username': 'admin', 'password': 'testpass'})
    return client
