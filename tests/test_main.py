import os
import shutil
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend import models, database, auth

# ------------------------------------------------------------------
# TEST DATABASE CONFIGURATION
# ------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    if os.path.exists("test.db"):
        os.remove("test.db")

    models.Base.metadata.create_all(bind=engine)
    yield
    os.remove("test.db")


@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[auth.get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def user(client):
    response = client.post("/register/", json={
        "username": "testuser",
        "email": "test@test.com",
        "password": "password123"
    })
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def second_user_headers(client):
    import uuid
    email = f"user_{uuid.uuid4()}@test.com"
    password = "testpass123"

    # Register using the correct route
    register = client.post("/register/", json={
        "username": email,
        "email": email,
        "password": password
    })
    assert register.status_code == 200

    # Login using the correct route
    login = client.post("/login/", json={
        "username": email,
        "password": password
    })
    assert login.status_code == 200
    token = login.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def token(client, user):
    response = client.post("/login/", json={
        "username": "testuser",
        "password": "password123"
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------
# AUTH TESTS
# ------------------------------------------------------------------

def test_register_duplicate_email(client, user):
    response = client.post("/register/", json={
        "username": "newuser",
        "email": "test@test.com",
        "password": "pass"
    })
    assert response.status_code == 400


def test_login_invalid_credentials(client):
    response = client.post("/login/", json={
        "username": "wrong",
        "password": "wrong"
    })
    assert response.status_code == 401


def test_get_current_user(client, auth_headers):
    response = client.get("/users/me/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"


# ------------------------------------------------------------------
# AGENT TESTS
# ------------------------------------------------------------------

def test_create_agent(client, auth_headers):
    response = client.post("/agents/", json={
        "name": "Geography Expert",
        "system_prompt": "You are geography expert."
    }, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Geography Expert"


def test_get_agents(client, auth_headers):
    client.post("/agents/", json={
        "name": "Football Expert",
        "system_prompt": "You are football expert."
    }, headers=auth_headers)

    response = client.get("/agents/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_agent_name_uniqueness_per_user(client, auth_headers, second_user_headers):
    # User A creates an agent
    response1 = client.post("/agents/", json={
        "name": "My Unique Agent",
        "system_prompt": "Prompt"
    }, headers=auth_headers)
    assert response1.status_code == 200

    # User A tries to create same name again → should fail
    response2 = client.post("/agents/", json={
        "name": "My Unique Agent",
        "system_prompt": "Another prompt"
    }, headers=auth_headers)
    assert response2.status_code in (400, 409)

    # User B creates agent with same name → should succeed
    response3 = client.post("/agents/", json={
        "name": "My Unique Agent",
        "system_prompt": "Other user prompt"
    }, headers=second_user_headers)
    assert response3.status_code == 200


def test_edit_agent_and_prevent_duplicate_name(client, auth_headers):
    # ----------------------------------------------------
    # 1) Create two agents
    # ----------------------------------------------------
    agent1 = client.post("/agents/", json={
        "name": "Agent One",
        "system_prompt": "Prompt 1"
    }, headers=auth_headers).json()

    agent2 = client.post("/agents/", json={
        "name": "Agent Two",
        "system_prompt": "Prompt 2"
    }, headers=auth_headers).json()

    # ----------------------------------------------------
    # 2) Edit agent1 successfully
    # ----------------------------------------------------
    edit_response = client.put(
        f"/agents/{agent1['id']}/",
        json={
            "name": "Updated Agent",
            "system_prompt": "Updated prompt"
        },
        headers=auth_headers
    )

    assert edit_response.status_code == 200
    assert edit_response.json()["name"] == "Updated Agent"

    # ----------------------------------------------------
    # 3) Request agent1 after update
    # ----------------------------------------------------
    edited_response = client.get(f"agents/{agent1['id']}", headers=auth_headers)
    assert edited_response.status_code == 200
    assert edited_response.json()['name'] == 'Updated Agent'

    # ----------------------------------------------------
    # 3) Try renaming agent1 to agent2's name → should fail
    # ----------------------------------------------------
    duplicate_response = client.put(
        f"/agents/{agent1['id']}/",
        json={
            "name": "Agent Two",
            "system_prompt": "Another prompt"
        },
        headers=auth_headers
    )

    assert duplicate_response.status_code in (400, 409)

# ------------------------------------------------------------------
# CHAT TESTS
# ------------------------------------------------------------------

def create_agent_and_chat(client, auth_headers, name="Geography Expert"):
    agent = client.post("/agents/", json={
        "name": name,
        "system_prompt": "Expert."
    }, headers=auth_headers).json()

    chat = client.post("/chats/", json={
        "agent_id": agent["id"],
        "name": "Test Chat"
    }, headers=auth_headers).json()

    return agent, chat


def test_create_chat(client, auth_headers):
    agent, chat = create_agent_and_chat(client, auth_headers)
    assert chat["name"] == "Test Chat"


def test_chat_not_found(client, auth_headers):
    response = client.get("/chats/999/messages/", headers=auth_headers)
    assert response.status_code == 404


def test_user_cannot_access_other_users_resources(client, auth_headers, second_user_headers):
    # User A creates agent & chat
    agent = client.post("/agents/", json={
        "name": "Private Agent",
        "system_prompt": "Private"
    }, headers=auth_headers).json()

    chat = client.post("/chats/", json={
        "agent_id": agent["id"],
        "name": "Private Chat"
    }, headers=auth_headers).json()

    # User B tries to access User A's agent
    agent_access = client.get(f"/agents/{agent['id']}/", headers=second_user_headers)
    assert agent_access.status_code in (403, 404)

    # User B tries to access User A's chat
    chat_access = client.get(f"/chats/{chat['id']}/", headers=second_user_headers)
    assert chat_access.status_code in (403, 404)

# ------------------------------------------------------------------
# TEXT MESSAGE TEST
# ------------------------------------------------------------------

def test_send_text_message(client, auth_headers):
    agent, chat = create_agent_and_chat(client, auth_headers)

    response = client.post("/send/", json={
        "chat_id": chat["id"],
        "text": "What is the capital of Japan?"
    }, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["sender"] == "agent"
    assert "Tokyo" in response.json()["text"]

# ------------------------------------------------------------------
# Uploading Wrong File Format
# ------------------------------------------------------------------

def test_upload_non_wav_file(client, auth_headers, tmp_path):
    """Uploading a non-WAV file should be rejected with HTTP 415."""
    # Create a dummy agent and chat to upload against
    agent_resp = client.post(
        "/agents/",
        json={"name": "Test Agent", "system_prompt": "You are helpful."},
        headers=auth_headers,
    )
    assert agent_resp.status_code == 200
    agent_id = agent_resp.json()["id"]

    chat_resp = client.post(
        "/chats/",
        json={"agent_id": agent_id, "name": "Test Chat"},
        headers=auth_headers,
    )
    assert chat_resp.status_code == 200
    chat_id = chat_resp.json()["id"]

    # Use the spam.txt fixture from tests/media
    spam_path = "tests/media/spam.txt"
    with open(spam_path, "rb") as f:
        response = client.post(
            f"/chats/{chat_id}/upload-audio/",
            files={"file": ("spam.txt", f, "text/plain")},
            headers=auth_headers,
        )

    assert response.status_code == 415
    assert "WAV" in response.json()["detail"]

#-------------------------------------------------------------------
# AUDIO FLOW TEST
# ------------------------------------------------------------------

def test_audio_only_chat(client, auth_headers):
    # ----------------------------------------------------
    # 1) Create agent and chat
    # ----------------------------------------------------
    agent = client.post("/agents/", json={
        "name": "Football Expert",
        "system_prompt": "You are a football expert."
    }, headers=auth_headers).json()

    chat = client.post("/chats/", json={
        "agent_id": agent["id"],
        "name": "Football Chat"
    }, headers=auth_headers).json()

    # ----------------------------------------------------
    # 2) Upload AUDIO question
    # ----------------------------------------------------
    with open("tests/media/ucl_2014_question.wav", "rb") as f:
        upload = client.post(
            f"/chats/{chat['id']}/upload-audio/",
            headers=auth_headers,
            files={"file": ("question.wav", f, "audio/wav")}
        )

    assert upload.status_code == 200
    audio_message_id = upload.json()["message_id"]

    # ----------------------------------------------------
    # 3) Send audio message
    # ----------------------------------------------------
    audio_response = client.post("/send/", json={
        "chat_id": chat["id"],
        "audio": audio_message_id
    }, headers=auth_headers)

    assert audio_response.status_code == 200
    assert audio_response.json()["is_audio"] is True

    agent_audio_id = audio_response.json()["id"]

    # ----------------------------------------------------
    # 4) Download agent audio response
    # ----------------------------------------------------
    download = client.get(
        f"/messages/{agent_audio_id}/download/",
        headers=auth_headers
    )

    assert download.status_code == 200

    output_path = "tests/media/ucl_2014_answer.mp3"
    with open(output_path, "wb") as f:
        f.write(download.content)

    assert os.path.exists(output_path)

    # ----------------------------------------------------
    # 5) Fetch chat messages
    # ----------------------------------------------------
    chat_messages = client.get(
        f"/chats/{chat['id']}/messages/",
        headers=auth_headers
    )

    assert chat_messages.status_code == 200
    messages = chat_messages.json()

    # ----------------------------------------------------
    # 6) Assert exactly 2 messages exist
    # ----------------------------------------------------
    assert len(messages) == 2

    assert messages[0]["sender"] == "user"
    assert messages[1]["sender"] == "agent"
    assert messages[1]["is_audio"] is True


# ------------------------------------------------------------------
# TEXT-AUDIO FLOW TEST
# ------------------------------------------------------------------

def test_text_audio_chat(client, auth_headers):
    # ----------------------------------------------------
    # 1) Create agent and chat
    # ----------------------------------------------------
    agent = client.post("/agents/", json={
        "name": "Geography Expert",
        "system_prompt": "You are geography expert."
    }, headers=auth_headers).json()

    chat = client.post("/chats/", json={
        "agent_id": agent["id"],
        "name": "Japan Chat"
    }, headers=auth_headers).json()

    # ----------------------------------------------------
    # 2) Send TEXT question first
    # ----------------------------------------------------
    text_response = client.post("/send/", json={
        "chat_id": chat["id"],
        "text": "What is the capital of Japan?"
    }, headers=auth_headers)

    assert text_response.status_code == 200
    assert "Tokyo" in text_response.json()["text"]

    # ----------------------------------------------------
    # 3) Upload AUDIO question to same chat
    # ----------------------------------------------------
    with open("tests/media/japan_capital_question.wav", "rb") as f:
        upload = client.post(
            f"/chats/{chat['id']}/upload-audio/",
            headers=auth_headers,
            files={"file": ("question.wav", f, "audio/wav")}
        )

    assert upload.status_code == 200
    audio_message_id = upload.json()["message_id"]

    # ----------------------------------------------------
    # 4) Send audio message
    # ----------------------------------------------------
    audio_response = client.post("/send/", json={
        "chat_id": chat["id"],
        "audio": audio_message_id
    }, headers=auth_headers)

    assert audio_response.status_code == 200
    assert audio_response.json()["is_audio"] is True

    agent_audio_id = audio_response.json()["id"]

    # ----------------------------------------------------
    # 5) Download agent audio response
    # ----------------------------------------------------
    download = client.get(
        f"/messages/{agent_audio_id}/download/",
        headers=auth_headers
    )

    assert download.status_code == 200

    output_path = "tests/media/japan_capital_answer.mp3"
    with open(output_path, "wb") as f:
        f.write(download.content)

    assert os.path.exists(output_path)

    # ----------------------------------------------------
    # 6) Fetch chat messages
    # ----------------------------------------------------
    chat_messages = client.get(
        f"/chats/{chat['id']}/messages/",
        headers=auth_headers
    )

    assert chat_messages.status_code == 200
    messages = chat_messages.json()

    # ----------------------------------------------------
    # 7) Assert 4 messages exist
    # ----------------------------------------------------
    assert len(messages) == 4

    # Optional deeper validation
    assert messages[0]["sender"] == "user"
    assert messages[1]["sender"] == "agent"
    assert messages[2]["sender"] == "user"
    assert messages[3]["sender"] == "agent"