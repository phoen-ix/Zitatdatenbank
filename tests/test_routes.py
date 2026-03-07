def test_index_page(client, app):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Zitatdatenbank' in response.data or b'Quote Database' in response.data


def test_index_with_quote(client, app, make_quote):
    with app.app_context():
        make_quote(text='Testquote for index', author='TestAuthor')
    response = client.get('/')
    assert response.status_code == 200


def test_browse_empty(client, app):
    response = client.get('/browse')
    assert response.status_code == 200


def test_browse_with_quotes(client, app, make_quote):
    with app.app_context():
        for i in range(5):
            make_quote(text=f'Browse quote {i}')
    response = client.get('/browse')
    assert response.status_code == 200
    assert b'Browse quote' in response.data


def test_browse_filter_by_author(client, app, make_quote):
    with app.app_context():
        make_quote(text='Quote by Goethe', author='Goethe')
        make_quote(text='Quote by Schiller', author='Schiller')
    response = client.get('/browse?author=Goethe')
    assert response.status_code == 200
    assert b'Goethe' in response.data


def test_browse_filter_by_tag(client, app, make_quote):
    with app.app_context():
        make_quote(text='A wise quote', tags=['Wisdom'])
    response = client.get('/browse?tag=Wisdom')
    assert response.status_code == 200


def test_browse_sort(client, app, make_quote):
    with app.app_context():
        make_quote(text='First quote', author='Alpha')
        make_quote(text='Second quote', author='Beta')
    response = client.get('/browse?sort=author_az')
    assert response.status_code == 200


def test_authors_page(client, app, make_quote):
    with app.app_context():
        make_quote(author='Goethe')
        make_quote(author='Goethe')
        make_quote(author='Schiller')
    response = client.get('/browse/authors')
    assert response.status_code == 200
    assert b'Goethe' in response.data


def test_authors_letter_filter(client, app, make_quote):
    with app.app_context():
        make_quote(author='Goethe')
        make_quote(author='Schiller')
    response = client.get('/browse/authors?letter=G')
    assert response.status_code == 200
    assert b'Goethe' in response.data


def test_tags_page(client, app, make_quote):
    with app.app_context():
        make_quote(tags=['Liebe'])
        make_quote(tags=['Liebe'])
        make_quote(tags=['Natur'])
    response = client.get('/browse/tags')
    assert response.status_code == 200
    assert b'Liebe' in response.data


def test_search_empty(client, app):
    response = client.get('/search')
    assert response.status_code == 200


def test_search_with_query(client, app, make_quote):
    with app.app_context():
        make_quote(text='UniqueSearchTerm in this quote')
    response = client.get('/search?q=UniqueSearchTerm')
    assert response.status_code == 200
    assert b'UniqueSearchTerm' in response.data


def test_search_no_results(client, app, make_quote):
    with app.app_context():
        make_quote(text='Normal quote')
    response = client.get('/search?q=xyznonexistent')
    assert response.status_code == 200


def test_quote_detail(client, app, make_quote):
    with app.app_context():
        q = make_quote(text='Detail quote text', author='DetailAuthor')
        quote_id = q.id
    response = client.get(f'/quote/{quote_id}')
    assert response.status_code == 200
    assert b'Detail quote text' in response.data


def test_quote_detail_not_found(client, app):
    response = client.get('/quote/99999')
    assert response.status_code == 404


def test_api_random(client, app, make_quote):
    with app.app_context():
        make_quote(text='API random quote')
    response = client.get('/api/random')
    assert response.status_code == 200
    data = response.get_json()
    assert 'text' in data
    assert 'author' in data
    assert 'tags' in data


def test_api_random_empty(client, app):
    response = client.get('/api/random')
    assert response.status_code == 404


def test_api_quotes(client, app, make_quote):
    with app.app_context():
        for i in range(3):
            make_quote(text=f'API quote {i}', author='TestAuthor')
    response = client.get('/api/quotes')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['quotes']) == 3
    assert data['page'] == 1
    assert 'has_next' in data
    assert data['quotes'][0]['author'] == 'TestAuthor'
    assert 'id' in data['quotes'][0]
    assert 'tags' in data['quotes'][0]


def test_api_quotes_filter_author(client, app, make_quote):
    with app.app_context():
        make_quote(text='By Goethe', author='Goethe')
        make_quote(text='By Schiller', author='Schiller')
    response = client.get('/api/quotes?author=Goethe')
    data = response.get_json()
    assert len(data['quotes']) == 1
    assert data['quotes'][0]['author'] == 'Goethe'


def test_api_quotes_filter_tag(client, app, make_quote):
    from models import Tag
    from extensions import db as _db
    with app.app_context():
        tag = Tag(name='Wisdom')
        _db.session.add(tag)
        _db.session.flush()
        q = make_quote(text='Wise quote', author='Sage')
        q.tags.append(tag)
        _db.session.commit()
        make_quote(text='Other quote', author='Other')
    response = client.get('/api/quotes?tag=Wisdom')
    data = response.get_json()
    assert len(data['quotes']) == 1
    assert 'Wisdom' in data['quotes'][0]['tags']


def test_api_quotes_search(client, app, make_quote):
    with app.app_context():
        make_quote(text='The meaning of life', author='Philosopher')
        make_quote(text='Something else', author='Other')
    response = client.get('/api/quotes?q=meaning')
    data = response.get_json()
    assert len(data['quotes']) >= 1
    assert any('meaning' in q['text'].lower() for q in data['quotes'])


def test_api_quotes_pagination(client, app, make_quote):
    with app.app_context():
        for i in range(5):
            make_quote(text=f'Paginated {i}')
    response = client.get('/api/quotes?per_page=2&page=1')
    data = response.get_json()
    assert len(data['quotes']) == 2
    assert data['has_next'] is True
    assert data['has_prev'] is False

    response = client.get('/api/quotes?per_page=2&page=2')
    data = response.get_json()
    assert len(data['quotes']) == 2
    assert data['has_prev'] is True


def test_api_quotes_per_page_capped(client, app, make_quote):
    with app.app_context():
        make_quote(text='Test')
    response = client.get('/api/quotes?per_page=999')
    data = response.get_json()
    assert data['per_page'] == 100


def test_api_quote_detail(client, app, make_quote):
    with app.app_context():
        q = make_quote(text='Detail quote', author='Author')
        qid = q.id
    response = client.get(f'/api/quotes/{qid}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == qid
    assert data['text'] == 'Detail quote'
    assert data['author'] == 'Author'


def test_api_quote_detail_not_found(client, app):
    response = client.get('/api/quotes/99999')
    assert response.status_code == 404


def test_health(client, app):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert data['checks']['database'] == 'ok'


def test_set_lang(client, app):
    response = client.get('/set-lang/en', follow_redirects=True)
    assert response.status_code == 200
    response = client.get('/')
    assert b'Home' in response.data or b'Quote Database' in response.data


def test_set_lang_invalid(client, app):
    response = client.get('/set-lang/xx', follow_redirects=True)
    assert response.status_code == 200


def test_csp_header(client, app):
    response = client.get('/')
    assert response.status_code == 200
    csp = response.headers.get('Content-Security-Policy')
    assert csp is not None
    assert "script-src 'self' 'nonce-" in csp


def test_csp_not_on_json(client, app):
    response = client.get('/health')
    csp = response.headers.get('Content-Security-Policy')
    assert csp is None


def test_credits_page(client, app):
    response = client.get('/credits')
    assert response.status_code == 200
    assert b'Creative Commons' in response.data
    assert b'BY-SA 3.0' in response.data


def test_search_by_tag(client, app, make_quote):
    with app.app_context():
        make_quote(text='Quote with tag', tags=['Philosophy'])
    response = client.get('/search?q=Philosophy')
    assert response.status_code == 200
    assert b'Quote with tag' in response.data
