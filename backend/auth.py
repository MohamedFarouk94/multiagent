import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from . import database, models
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

#
# Token Life Span
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # In minutes
# Change it to what's suitable for the usecase
#

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db(): # -> Session:
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class JWTAuthManager:
    """
    Manages JWT-based authentication and authorization.
    Provides methods for password hashing, token creation, decoding, and user retrieval.
    """

    def __init__(self, secret_key: str, algorithm: str, token_expiry_minutes: int):
        """
        Initializes the JWTAuthManager with the necessary configuration.

        Args:
            secret_key (str): The secret key used to sign the JWT.
            algorithm (str): The algorithm used for JWT encoding and decoding.
            token_expiry_minutes (int): The default expiration time for access tokens in minutes.
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry_minutes = token_expiry_minutes

    def get_password_hash(self, password: str) -> str:
        """
        Hashes a plaintext password using bcrypt.

        Args:
            password (str): The plaintext password.

        Returns:
            str: The hashed password.
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifies if a plaintext password matches its hashed version.

        Args:
            plain_password (str): The plaintext password.
            hashed_password (str): The hashed password.

        Returns:
            bool: True if the passwords match, False otherwise.
        """
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Creates a JWT access token with a specific expiration time.

        Args:
            data (dict): The payload data to encode in the token.
            expires_delta (Optional[timedelta]): Optional custom expiration time.
                Defaults to the configured token_expiry_minutes.

        Returns:
            str: The generated JWT access token.
        """
        to_encode = data.copy()
        expire = datetime.now() + (expires_delta or timedelta(minutes=self.token_expiry_minutes))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def _decode_access_token(self, token: str) -> dict:
        """
        Decodes a JWT access token and verifies its validity.
        NOTE: This should be seen as a PRIVATE function, not recommended to use it in other files/classes.

        Args:
            token (str): The JWT access token to decode.

        Returns:
            dict: The decoded token payload.

        Raises:
            HTTPException: If the token is invalid or expired.
        """
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    def get_current_user(self, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User:
        """
        Retrieves the current user based on the provided JWT access token.

        Args:
            db (Session): The database session.
            token (str): The JWT access token.

        Returns:
            models.User: The authenticated user.

        Raises:
            HTTPException: If the token is invalid or the user is not found.
        """
        token_data = self._decode_access_token(token)
        username: str = token_data.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = db.query(models.User).filter(models.User.username == username).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user


# Here is the JWTAuthManager object
# Which should be imported in other files
# In order to use the JWT Auth Manager functionalities.
auth_manager = JWTAuthManager(SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES)
