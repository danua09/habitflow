class TestRegistration:

    def test_register_page(self, client):
        resp = client.get('/auth/register')
        assert resp.status_code == 200

    def test_register_success(self, client):
        resp = client.post('/auth/register', data={
            'email': 'new@example.com',
            'username': 'newuser',
            'password': 'password123',
            'password_confirm': 'password123',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_register_duplicate_email(self, client, user):
        resp = client.post('/auth/register', data={
            'email': 'test@example.com',
            'username': 'another',
            'password': 'password123',
            'password_confirm': 'password123',
        }, follow_redirects=True)
        assert 'Регистрация'.encode('utf-8') in resp.data


class TestLogin:

    def test_login_page(self, client):
        resp = client.get('/auth/login')
        assert resp.status_code == 200

    def test_login_success(self, client, user):
        resp = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_login_wrong_password(self, client, user):
        resp = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword',
        }, follow_redirects=True)
        assert 'Неверный email или пароль'.encode() in resp.data

    def test_logout(self, client, user):
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123',
        })
        resp = client.get('/auth/logout', follow_redirects=True)
        assert resp.status_code == 200
