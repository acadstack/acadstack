import pytest
from quart import session


def test_login(client, auth):
    # login request set the user in the session
    # check that the user is loaded from the session
    with client:
        assert client.get("/acadstack").status_code in [200, 308]
        assert auth.login().status_code == 200
        client.get("/acadstack/index.html")
        assert "user" in session and session["user"]["login_id"] == "test"


def test_logout(client, auth):
    with client as c:
        assert auth.logout().status_code == 200
        assert "user" not in session


def test_load_user(client, auth):
    with client:
        assert auth.login().status_code == 200
        res = client.get("/acadstack/user/23")
        assert res.status_code == 200
        assert res.json["status"] == "OK"
        

def test_current_user(client, auth):
    with client:
        assert auth.login().status_code == 200
        res = client.get("/acadstack/current_user")
        assert res.status_code == 200
        assert res.json["status"] == "OK"
        assert res.json["body"]["user"]["login_id"] == "test"
        
