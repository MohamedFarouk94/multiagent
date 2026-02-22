from sqlalchemy.exc import IntegrityError

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import models, schemas, database, auth
from datetime import datetime
from fastapi import File, UploadFile
from fastapi.responses import FileResponse
from typing import List
import os

from .history_manager import retrieve_messages_for_user
from .chain_wrapper import prepare_data, run_chain

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MultiAgent API",
    description="API for managing users, agents, chats, and messages with audio support",
    version="1.0.0",
    contact={
        "name": "Mohamed Farouk",
        "email": "mohamedfarouk1994@gmail.com",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=database.engine)


@app.post("/register/", response_model=schemas.UserResponse, tags=['Auth'])
def register_user(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    email_existed = db.query(models.User).filter(models.User.email == user.email).first()
    if email_existed:
        raise HTTPException(status_code=400, detail="Email already registered")
    username_existed = db.query(models.User).filter(models.User.username == user.username).first()
    if username_existed:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth.auth_manager.get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login/", response_model=schemas.Token, tags=['Auth'])
def login_user(form_data: schemas.UserLogin, db: Session = Depends(auth.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.auth_manager.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token_data = {"sub": user.username}
    token = auth.auth_manager.create_access_token(data=token_data)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/users/me/", response_model=schemas.UserResponse, tags=['Auth'])
def read_current_user(current_user: models.User = Depends(auth.auth_manager.get_current_user)):
    return current_user


@app.post("/agents/", response_model=schemas.AgentSimple, tags=['Agents'])
def create_agent(
    agent_data: schemas.AgentCreate,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.auth_manager.get_current_user)
):
    new_agent = models.Agent(
        name=agent_data.name,
        system_prompt=agent_data.system_prompt,
        user_id=current_user.id
    )
    try:
        nested = db.begin_nested()   # ← savepoint created FIRST (no pending objects yet)
        db.add(new_agent)
        db.flush()                   # ← flush happens inside the savepoint
        nested.commit()
    except IntegrityError:
        nested.rollback()            # ← only rolls back to savepoint
        raise HTTPException(status_code=400, detail="Agent name already exists")

    db.commit()
    db.refresh(new_agent)
    return new_agent


@app.get("/agents/", response_model=List[schemas.AgentSimple], tags=['Agents'])
def get_agents(
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.auth_manager.get_current_user)
):
    return db.query(models.Agent).filter(
        models.Agent.user_id == current_user.id
    ).all()


@app.get("/agents/{agent_id}/", response_model=schemas.AgentDetail, tags=['Agents'])
def get_agent(
    agent_id: int,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.auth_manager.get_current_user)
):
    agent = db.query(models.Agent).filter(
        models.Agent.id == agent_id,
        models.Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent


@app.put("/agents/{agent_id}/", response_model=schemas.AgentSimple, tags=["Agents"])
def edit_agent(
    agent_id: int,
    agent_data: schemas.AgentCreate,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.auth_manager.get_current_user)
):
    agent = db.query(models.Agent).filter(
        models.Agent.id == agent_id,
        models.Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.name = agent_data.name
    agent.system_prompt = agent_data.system_prompt

    try:
        agent.name = agent_data.name
        agent.system_prompt = agent_data.system_prompt

        db.commit()
        db.refresh(agent)

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Agent name already exists")

    return agent


@app.post("/chats/", response_model=schemas.ChatSimple, tags=['Chats'])
def create_chat(
    chat_data: schemas.ChatCreate,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.auth_manager.get_current_user)
):
    agent = db.query(models.Agent).filter(
        models.Agent.id == chat_data.agent_id,
        models.Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    name = chat_data.name or f"Chat_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    new_chat = models.Chat(
        name=name,
        agent_id=agent.id
    )

    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return new_chat


@app.get("/chats/{chat_id}/messages/", response_model=List[schemas.MessageResponse], tags=['Chats'])
def get_chat(
    chat_id: int,
    start_index: int = -1,
    n: int = 10,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.auth_manager.get_current_user)
):
    chat = db.query(models.Chat).join(models.Agent).filter(
        models.Chat.id == chat_id,
        models.Agent.user_id == current_user.id
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return retrieve_messages_for_user(chat, start_index, n)


@app.post("/chats/{chat_id}/upload-audio/", tags=['Messages'])
def upload_audio(
    chat_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.auth_manager.get_current_user)
):
    chat = db.query(models.Chat).join(models.Agent).filter(
        models.Chat.id == chat_id,
        models.Agent.user_id == current_user.id
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    message = models.Message(
        chat_id=chat.id,
        is_agent=False,
        is_audio=True,
        text=''
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    os.makedirs("backend/media", exist_ok=True)

    file_path = f"backend/media/user_{current_user.username}_{message.id}.wav"

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    return {"message_id": message.id}


@app.post("/send/", response_model=schemas.MessageResponse, tags=['Messages'])
def send(
    payload: schemas.SendRequest,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.auth_manager.get_current_user)
):
    chat = db.query(models.Chat).join(models.Agent).filter(
        models.Chat.id == payload.chat_id,
        models.Agent.user_id == current_user.id
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if payload.audio:
        message = db.query(models.Message).filter(
            models.Message.id == payload.audio,
            models.Message.chat_id == chat.id
        ).first()

        if not message:
            raise HTTPException(status_code=404, detail="Audio message not found")

    else:
        message = models.Message(
            chat_id=chat.id,
            is_agent=False,
            is_audio=False,
            text=payload.text
        )
        db.add(message)
        db.commit()
        db.refresh(message)

    data = prepare_data(message)
    output = run_chain(data)

    agent_message = models.Message(
        chat_id=chat.id,
        is_agent=True,
        is_audio=output.get("is_audio", False),
        text=output.get("agent_text", "")
    )

    db.add(agent_message)
    db.flush()

    if agent_message.is_audio:
        if "agent_audio_bytes" not in output:
            raise HTTPException(status_code=500, detail="Audio bytes missing from chain output")

        os.makedirs("backend/media", exist_ok=True)

        agent_file = f'backend/media/agent_{current_user.username}_{agent_message.id}.mp3'

        try:
            with open(agent_file, "wb") as f:
                f.write(output["agent_audio_bytes"])
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to save agent audio")

    chat.last_message_at = datetime.utcnow()

    db.commit()
    db.refresh(agent_message)

    return {
        "id": agent_message.id,
        "sent_at": agent_message.sent_at,
        "sender": "agent",
        "is_audio": agent_message.is_audio,
        "text": "" if agent_message.is_audio else agent_message.text
    }


@app.get("/messages/{message_id}/download/", tags=['Messages'])
def download_audio(
    message_id: int,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.auth_manager.get_current_user)
):
    message = db.query(models.Message).join(models.Chat).join(models.Agent).filter(
        models.Message.id == message_id,
        models.Agent.user_id == current_user.id
    ).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if not message.is_audio:
        raise HTTPException(status_code=400, detail="Message is not audio")

    if message.is_agent:
        path = f"backend/media/agent_{current_user.username}_{message.id}.mp3"
    else:
        path = f"backend/media/user_{current_user.username}_{message.id}.wav"

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path, media_type="audio/mpeg")
