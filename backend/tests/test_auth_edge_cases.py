import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.auth import (
    SECRET_KEY,
    ALGORITHM,
    create_access_token,
    get_current_user,
    verify_password,
    get_password_hash,
    _preprocess_password,
)
from app.models import User


class TestGetAccessTokenErrorHandling:
    def test_create_token_without_sub(self):
        token = create_access_token({"other": "data"})
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        
        assert payload.get("sub") is None


class TestVerifyPasswordEdgeCases:
    def test_verify_password_with_none_hash(self):
        result = verify_password("password", None)
        assert result is False
    
    def test_verify_password_with_empty_hash(self):
        result = verify_password("password", "")
        assert result is False
    
    def test_verify_password_with_invalid_hash_format(self):
        invalid_hashes = [
            "not_a_valid_bcrypt_hash",
            "$2b$",
            "$2b$10$",
            "12345",
        ]
        for invalid_hash in invalid_hashes:
            result = verify_password("password", invalid_hash)
            assert result is False


class TestPreprocessPassword:
    def test_preprocess_empty_password(self):
        result = _preprocess_password("")
        assert isinstance(result, bytes)
    
    def test_preprocess_special_characters(self):
        special_password = "!@#$%^&*()_+"
        result = _preprocess_password(special_password)
        assert isinstance(result, bytes)
    
    def test_preprocess_unicode_password(self):
        unicode_password = "密码123"
        result = _preprocess_password(unicode_password)
        assert isinstance(result, bytes)


class TestPasswordHashRoundTrip:
    def test_hash_and_verify_roundtrip(self):
        password = "TestPassword123!@#"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_hash_and_verify_wrong_password(self):
        password = "CorrectPassword123"
        wrong_password = "WrongPassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestTokenExpiration:
    def test_token_with_past_expiration(self):
        past_expiry = timedelta(minutes=-60)
        token = create_access_token({"sub": "1"}, expires_delta=past_expiry)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
    
    def test_token_with_valid_expiration(self):
        future_expiry = timedelta(minutes=60)
        token = create_access_token({"sub": "1"}, expires_delta=future_expiry)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        
        assert payload.get("sub") == "1"


class TestInvalidUserScenarios:
    def test_token_with_non_integer_sub(self):
        token = create_access_token({"sub": "not_an_integer"})
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        sub_value = payload.get("sub")
        
        with pytest.raises(ValueError):
            int(sub_value)
    
    def test_token_with_integer_sub_as_string(self):
        token = create_access_token({"sub": "123"})
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        sub_value = payload.get("sub")
        
        assert int(sub_value) == 123


class TestInvalidSignature:
    def test_token_with_wrong_secret(self):
        token = create_access_token({"sub": "1"})
        wrong_secret = "wrong_secret_key"
        
        with pytest.raises(JWTError):
            jwt.decode(token, wrong_secret, algorithms=[ALGORITHM], options={"verify_sub": False})


class TestTokenAlgorithms:
    def test_token_with_different_algorithm(self):
        to_encode = {"sub": "1"}
        from datetime import datetime
        from app.auth import ACCESS_TOKEN_EXPIRE_MINUTES
        
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        
        token = jwt.encode(to_encode, SECRET_KEY, algorithm="HS512")
        
        with pytest.raises(JWTError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
