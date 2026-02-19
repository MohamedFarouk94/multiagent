from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import models, schemas, database, auth

app = FastAPI()

models.Base.metadata.create_all(bind=database.engine)


@app.post("/register/", response_model=schemas.UserResponse)
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


@app.post("/login/", response_model=schemas.Token)
def login_user(form_data: schemas.UserLogin, db: Session = Depends(auth.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.auth_manager.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token_data = {"sub": user.username}
    token = auth.auth_manager.create_access_token(data=token_data)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/users/me/", response_model=schemas.UserResponse)
def read_current_user(current_user: models.User = Depends(auth.auth_manager.get_current_user)):
    return current_user


@app.get("/users/{username}/")
def do_action(username: str, current_user: models.User = Depends(auth.auth_manager.get_current_user)):
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden"
        )
    #
    # EXECUTE ACTIONS HERE
    #
    return {'message': 'ok'}
