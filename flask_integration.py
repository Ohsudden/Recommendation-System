import pytest
from main import SpotifyFlaskApp

@pytest.fixture
def client():
    app_instance = SpotifyFlaskApp()
    
    class DummySP:
        def current_user_playlists(self):
            return {'items': [{'name': 'Warps core', 'id': '123'}]}
    
    app_instance.sp = DummySP()
    
    app = app_instance.app
    app.testing = True
    client = app.test_client()
    
    with client.session_transaction() as sess:
        sess['token_info'] = {'access_token': 'fake', 'expires_at': 9999999999}
    return client

def test_playlists_data(client):
    resp = client.get('/playlists-data')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert data[0]['name'] == 'Warps core'

def test_recommend_unauthorized(client):
    with client.session_transaction() as sess:
        sess.pop('token_info', None)
    resp = client.get('/recommend/any_id')
    assert resp.status_code == 302
    assert '/authorization' in resp.headers['Location']

if __name__ == '__main__':
    import pytest
    pytest.main([__file__])