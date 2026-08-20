from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt, ExpiredSignatureError 
from passlib.context import CryptContext
from config import settings
from auth.exceptions import TokenExpiredException, InvalidTokenException 
# ==================== PASSWORD HASHING ====================

# Use bcrypt for password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10
)

def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password (safe to store in database)
    
    Example:
        password_hash = hash_password("mypassword123")
        # password_hash = "$2b$12$abcd1234..."
    """
    return pwd_context.hash(password)

import asyncio

async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(pwd_context.verify, plain_password, hashed_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if plain password matches hashed password.
    
    Args:
        plain_password: Password user entered
        hashed_password: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    
    Example:
        verify_password("mypassword123", "$2b$12$abcd1234...")
        # Returns: True
    """
    return pwd_context.verify(plain_password, hashed_password)


# ==================== JWT TOKEN ====================

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary to encode in token
               Example: {"user_id": "123", "role": "admin", "college_id": "college_a"}
        expires_delta: How long token is valid (default: 15 minutes)
    
    Returns:
        JWT token string
    
    Example:
        token = create_access_token(
            data={"user_id": "123", "role": "admin"},
            expires_delta=timedelta(minutes=15)
        )
        # Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    to_encode = data.copy()
    
    # Set expiry time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    print("JWT_EXPIRY_MINUTES =", settings.JWT_EXPIRY_MINUTES)
    print("Expire =", expire)
    # Encode with secret
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token data (dictionary)
    
    Raises:
        TokenExpiredException: If token has expired
        InvalidTokenException: If token is invalid or malformed
    
    Example:
        payload = decode_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        # Returns: {"user_id": "123", "role": "admin", "exp": 1234567890}
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    
    # ← CHANGED: Distinguish between expired and invalid
    except ExpiredSignatureError:
        raise TokenExpiredException()
    
    except JWTError:
        raise InvalidTokenException()


def create_refresh_token(data: dict) -> str:
    """
    Create a refresh token (longer expiry).
    
    Refresh tokens last longer (7 days).
    Access tokens are short (15 minutes).
    When access token expires, use refresh token to get new access token.
    
    Args:
        data: Dictionary to encode in token
    
    Returns:
        Refresh token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt