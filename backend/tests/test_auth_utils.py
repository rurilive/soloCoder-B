import pytest
from datetime import timedelta

from app.auth import (
    _preprocess_password,
    verify_password,
    get_password_hash,
    create_access_token,
)


class TestPasswordPreprocessing:
    def test_preprocess_password_returns_sha256_hash(self):
        password = "TestPassword123"
        result = _preprocess_password(password)
        
        assert isinstance(result, bytes)
        assert len(result) == 64
        
        import hashlib
        expected = hashlib.sha256(password.encode('utf-8')).hexdigest().encode('utf-8')
        assert result == expected


class TestPasswordHashing:
    def test_get_password_hash_returns_valid_hash(self):
        password = "StrongPassword123"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    
    def test_verify_password_with_preprocessed_hash(self):
        password = "TestPassword456"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_with_wrong_password(self):
        password = "CorrectPassword123"
        hashed = get_password_hash(password)
        
        assert verify_password("WrongPassword456", hashed) is False
    
    def test_verify_password_with_direct_plain_hash(self):
        import bcrypt
        
        password = "DirectPassword123"
        plain_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        direct_hash = bcrypt.hashpw(plain_bytes, salt).decode('utf-8')
        
        assert verify_password(password, direct_hash) is True
    
    def test_verify_password_with_invalid_hash(self):
        password = "TestPassword123"
        invalid_hash = "not_a_valid_hash"
        
        assert verify_password(password, invalid_hash) is False
    
    def test_verify_password_empty_password(self):
        password = ""
        hashed = get_password_hash("SomePassword123")
        
        assert verify_password(password, hashed) is False


class TestAccessTokenCreation:
    def test_create_access_token_default_expiry(self):
        data = {"sub": "123"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        from jose import jwt
        from app.auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert "exp" in payload
        assert payload.get("sub") == "123"
    
    def test_create_access_token_custom_expiry(self):
        data = {"sub": "456"}
        custom_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=custom_delta)
        
        from jose import jwt
        from app.auth import SECRET_KEY, ALGORITHM
        from datetime import datetime, timedelta as td
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert "exp" in payload
    
    def test_create_access_token_multiple_claims(self):
        data = {"sub": "789", "role": "admin", "extra": "value"}
        token = create_access_token(data)
        
        from jose import jwt
        from app.auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert payload.get("sub") == "789"
        assert payload.get("role") == "admin"
        assert payload.get("extra") == "value"
