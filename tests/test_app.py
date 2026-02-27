import copy
import pytest

from fastapi.testclient import TestClient

from src.app import app, activities

# keep a snapshot we can restore before each test
_INITIAL_ACTIVITIES = copy.deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_activities():
    """autouse fixture that restores the in‑memory activities dict."""
    activities.clear()
    activities.update(copy.deepcopy(_INITIAL_ACTIVITIES))


def test_root_redirect():
    # Arrange
    client = TestClient(app)
    # Act (don't follow the redirect automatically)
    response = client.get("/", follow_redirects=False)
    # Assert
    assert response.status_code == 307
    assert response.headers["location"].endswith("/static/index.html")


def test_get_activities():
    # Arrange
    client = TestClient(app)
    # Act
    response = client.get("/activities")
    # Assert
    assert response.status_code == 200
    body = response.json()
    # basic sanity: snapshot keys present
    assert "Chess Club" in body
    assert "Programming Class" in body


def test_signup_and_unregister_cycle():
    # Arrange
    client = TestClient(app)
    email = "newstudent@mergington.edu"
    activity = "Chess Club"
    # Act – sign up
    signup_response = client.post(f"/activities/{activity}/signup", params={"email": email})
    # Assert – successful signup
    assert signup_response.status_code == 200
    assert signup_response.json() == {"message": f"Signed up {email} for {activity}"}
    assert email in activities[activity]["participants"]

    # Act – unregister
    unregister_response = client.delete(f"/activities/{activity}/signup", params={"email": email})
    # Assert – successful removal
    assert unregister_response.status_code == 200
    assert unregister_response.json() == {"message": f"Removed {email} from {activity}"}
    assert email not in activities[activity]["participants"]


def test_duplicate_signup_error():
    # Arrange
    client = TestClient(app)
    email = "dup@mergington.edu"
    activity = "Chess Club"
    client.post(f"/activities/{activity}/signup", params={"email": email})

    # Act – attempt to sign up again
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert – error returned
    assert response.status_code == 400
    assert "already signed up" in response.json()["detail"]


def test_unregister_non_member_error():
    # Arrange
    client = TestClient(app)
    email = "not@member.com"
    activity = "Chess Club"

    # Act
    response = client.delete(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert "not signed up" in response.json()["detail"]


def test_activity_not_found_errors():
    # Arrange
    client = TestClient(app)
    email = "user@mergington.edu"
    bogus = "NoExist"

    # Act – signup for non‑existent activity
    signup_resp = client.post(f"/activities/{bogus}/signup", params={"email": email})
    # Assert
    assert signup_resp.status_code == 404
    assert signup_resp.json()["detail"] == "Activity not found"

    # Act – unregister from non‑existent activity
    unregister_resp = client.delete(f"/activities/{bogus}/signup", params={"email": email})
    # Assert
    assert unregister_resp.status_code == 404
    assert unregister_resp.json()["detail"] == "Activity not found"