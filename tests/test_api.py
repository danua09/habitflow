import json
from app.extensions import db


class TestAPIAuth:

    def test_get_token(self, client, user):
        resp = client.post('/api/v1/auth/token',
                           data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
                           content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'token' in data
        assert data['user']['username'] == 'testuser'

    def test_get_token_wrong_password(self, client, user):
        resp = client.post('/api/v1/auth/token',
                           data=json.dumps({'email': 'test@example.com', 'password': 'wrong'}),
                           content_type='application/json')
        assert resp.status_code == 401

    def test_unauthorized_access(self, client):
        resp = client.get('/api/v1/me')
        assert resp.status_code == 401


class TestAPIHabits:

    def _get_token(self, client, user):
        user.generate_api_token()
        db.session.flush()
        return user.api_token

    def test_list_habits(self, client, user, habit):
        token = self._get_token(client, user)
        resp = client.get('/api/v1/habits', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]['name'] == 'Утренняя зарядка'

    def test_create_habit(self, client, user):
        token = self._get_token(client, user)
        resp = client.post('/api/v1/habits',
                           data=json.dumps({'name': 'Медитация'}),
                           content_type='application/json',
                           headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 201
        assert resp.get_json()['name'] == 'Медитация'

    def test_delete_habit(self, client, user, habit):
        token = self._get_token(client, user)
        resp = client.delete(f'/api/v1/habits/{habit.id}',
                             headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200

    def test_check_habit(self, client, user, habit):
        token = self._get_token(client, user)
        resp = client.post(f'/api/v1/habits/{habit.id}/check',
                           data=json.dumps({}),
                           content_type='application/json',
                           headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 201
        assert 'streak' in resp.get_json()


class TestAPIStats:

    def test_stats(self, client, user, habit):
        user.generate_api_token()
        db.session.flush()
        resp = client.get('/api/v1/stats',
                          headers={'Authorization': f'Bearer {user.api_token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'today' in data
        assert 'habits' in data
