import pytest
from werkzeug.security import generate_password_hash, check_password_hash


def test_create_quote(app, make_quote):
    with app.app_context():
        quote = make_quote(text='Life is short.', author='Seneca', category='Philosophy')
        from extensions import db
        from models import Quote
        fetched = db.session.get(Quote, quote.id)
        assert fetched is not None
        assert fetched.text == 'Life is short.'
        assert fetched.author == 'Seneca'
        assert fetched.category == 'Philosophy'


def test_quote_defaults(app):
    with app.app_context():
        from extensions import db
        from models import Quote
        q = Quote(text='Some text')
        db.session.add(q)
        db.session.commit()
        assert q.created_at is not None
        assert q.updated_at is not None


def test_admin_user_creation(app):
    with app.app_context():
        from extensions import db
        from models import AdminUser
        admin = AdminUser(
            username='testadmin',
            password_hash=generate_password_hash('secret123'),
        )
        db.session.add(admin)
        db.session.commit()

        fetched = AdminUser.query.filter_by(username='testadmin').first()
        assert fetched is not None
        assert check_password_hash(fetched.password_hash, 'secret123')


def test_admin_user_unique_username(app):
    with app.app_context():
        from extensions import db
        from models import AdminUser
        db.session.add(AdminUser(username='unique', password_hash='hash1'))
        db.session.commit()
        with pytest.raises(Exception):
            db.session.add(AdminUser(username='unique', password_hash='hash2'))
            db.session.commit()


def test_setting_model(app):
    with app.app_context():
        from extensions import db
        from models import Setting
        s = Setting(key='test_key', value='test_value')
        db.session.add(s)
        db.session.commit()

        fetched = db.session.get(Setting, 'test_key')
        assert fetched.value == 'test_value'


def test_backup_log_model(app):
    with app.app_context():
        from extensions import db
        from models import BackupLog
        log = BackupLog(level='INFO', message='Test message')
        db.session.add(log)
        db.session.commit()

        fetched = BackupLog.query.first()
        assert fetched.level == 'INFO'
        assert fetched.message == 'Test message'
        assert fetched.ran_at is not None


def test_quote_nullable_fields(app):
    with app.app_context():
        from extensions import db
        from models import Quote
        q = Quote(text='Just a quote', author=None, category=None)
        db.session.add(q)
        db.session.commit()
        fetched = db.session.get(Quote, q.id)
        assert fetched.author is None
        assert fetched.category is None
