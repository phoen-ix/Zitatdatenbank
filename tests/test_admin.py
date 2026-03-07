def test_admin_requires_login(client, app):
    response = client.get('/admin/')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')


def test_login_page(client, app):
    response = client.get('/login')
    assert response.status_code == 200


def test_login_success(client, app, make_admin):
    with app.app_context():
        make_admin(username='admin', password='secret')
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'secret',
    }, follow_redirects=True)
    assert response.status_code == 200


def test_login_failure(client, app, make_admin):
    with app.app_context():
        make_admin(username='admin', password='secret')
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'wrong',
    }, follow_redirects=True)
    assert response.status_code == 200


def test_logout(client, app, make_admin):
    with app.app_context():
        make_admin(username='admin', password='secret')
    client.post('/login', data={'username': 'admin', 'password': 'secret'})
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200


def test_admin_dashboard(admin_client, app):
    response = admin_client.get('/admin/')
    assert response.status_code == 200


def test_admin_quotes_list(admin_client, app, make_quote):
    with app.app_context():
        make_quote(text='Admin listed quote')
    response = admin_client.get('/admin/quotes')
    assert response.status_code == 200
    assert b'Admin listed quote' in response.data


def test_admin_quotes_search(admin_client, app, make_quote):
    with app.app_context():
        make_quote(text='Searchable admin quote')
    response = admin_client.get('/admin/quotes?q=Searchable')
    assert response.status_code == 200
    assert b'Searchable' in response.data


def test_admin_add_quote_get(admin_client, app):
    response = admin_client.get('/admin/quotes/add')
    assert response.status_code == 200


def test_admin_add_quote_post(admin_client, app):
    with app.app_context():
        response = admin_client.post('/admin/quotes/add', data={
            'text': 'New admin quote',
            'author': 'TestAuthor',
            'tags': 'TestTag, AnotherTag',
        }, follow_redirects=True)
        assert response.status_code == 200

        from models import Quote
        q = Quote.query.filter_by(author='TestAuthor').first()
        assert q is not None
        assert q.text == 'New admin quote'
        tag_names = sorted(t.name for t in q.tags)
        assert tag_names == ['AnotherTag', 'TestTag']


def test_admin_add_quote_empty_text(admin_client, app):
    response = admin_client.post('/admin/quotes/add', data={
        'text': '',
        'author': 'TestAuthor',
    }, follow_redirects=True)
    assert response.status_code == 200


def test_admin_edit_quote(admin_client, app, make_quote):
    with app.app_context():
        q = make_quote(text='Original text', author='OrigAuthor', tags=['OldTag'])
        quote_id = q.id

    with app.app_context():
        response = admin_client.post(f'/admin/quotes/{quote_id}/edit', data={
            'text': 'Updated text',
            'author': 'NewAuthor',
            'tags': 'NewTag',
        }, follow_redirects=True)
        assert response.status_code == 200

        from models import Quote
        from extensions import db
        updated = db.session.get(Quote, quote_id)
        assert updated.text == 'Updated text'
        assert updated.author == 'NewAuthor'
        assert len(updated.tags) == 1
        assert updated.tags[0].name == 'NewTag'


def test_admin_delete_quote(admin_client, app, make_quote):
    with app.app_context():
        q = make_quote(text='To be deleted')
        quote_id = q.id

    response = admin_client.post(f'/admin/quotes/{quote_id}/delete', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        from models import Quote
        from extensions import db
        assert db.session.get(Quote, quote_id) is None


def test_admin_tags_list(admin_client, app, make_quote):
    with app.app_context():
        make_quote(tags=['Philosophy'])
    response = admin_client.get('/admin/tags')
    assert response.status_code == 200
    assert b'Philosophy' in response.data


def test_admin_add_tag(admin_client, app):
    with app.app_context():
        response = admin_client.post('/admin/tags/add', data={
            'name': 'NewTag',
        }, follow_redirects=True)
        assert response.status_code == 200

        from models import Tag
        tag = Tag.query.filter_by(name='NewTag').first()
        assert tag is not None


def test_admin_add_duplicate_tag(admin_client, app, make_quote):
    with app.app_context():
        make_quote(tags=['Existing'])
    with app.app_context():
        response = admin_client.post('/admin/tags/add', data={
            'name': 'Existing',
        }, follow_redirects=True)
        assert response.status_code == 200


def test_admin_delete_tag(admin_client, app, make_quote):
    with app.app_context():
        make_quote(tags=['ToDelete'])
        from models import Tag
        tag = Tag.query.filter_by(name='ToDelete').first()
        tag_id = tag.id

    response = admin_client.post(f'/admin/tags/{tag_id}/delete', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        from models import Tag
        from extensions import db
        assert db.session.get(Tag, tag_id) is None


def test_admin_settings_get(admin_client, app):
    response = admin_client.get('/admin/settings')
    assert response.status_code == 200


def test_admin_settings_general(admin_client, app):
    with app.app_context():
        response = admin_client.post('/admin/settings', data={
            'tab': 'general',
            'quotes_per_page': '30',
            'site_name': 'My Quotes',
        }, follow_redirects=True)
        assert response.status_code == 200

        from helpers import get_setting
        assert get_setting('quotes_per_page') == '30'
        assert get_setting('site_name') == 'My Quotes'


def test_admin_settings_theme(admin_client, app):
    with app.app_context():
        response = admin_client.post('/admin/settings', data={
            'tab': 'themes',
            'theme_name': 'ozean',
        }, follow_redirects=True)
        assert response.status_code == 200

        from helpers import get_setting
        assert get_setting('theme_name') == 'ozean'


def test_admin_backup_page(admin_client, app):
    response = admin_client.get('/admin/backup')
    assert response.status_code == 200


def test_admin_backup_create(admin_client, app, tmp_path):
    """Creating a backup should fail gracefully in test (no mysqldump)."""
    import backup_service
    original = backup_service.BACKUP_DIR
    backup_service.BACKUP_DIR = str(tmp_path)
    try:
        with app.app_context():
            response = admin_client.post('/admin/backup/create', follow_redirects=True)
            assert response.status_code == 200
    finally:
        backup_service.BACKUP_DIR = original
