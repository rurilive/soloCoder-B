import pytest
from datetime import datetime, timedelta

from jose import jwt

from app.auth import (
    SECRET_KEY,
    ALGORITHM,
    create_access_token,
)


class TestJWTCreationAndValidation:
    def test_create_access_token_includes_expiry(self):
        token = create_access_token({"sub": "1"})
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        
        assert "exp" in payload
        assert "sub" in payload
    
    def test_create_access_token_with_custom_expiry(self):
        custom_expiry = timedelta(minutes=5)
        token = create_access_token({"sub": "1"}, expires_delta=custom_expiry)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        
        assert "exp" in payload
    
    def test_create_access_token_preserves_sub(self):
        token = create_access_token({"sub": "123"})
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        
        assert payload.get("sub") == "123"
    
    def test_access_token_can_be_decoded(self):
        token = create_access_token({"sub": "1", "role": "user"})
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        
        assert payload.get("sub") == "1"
        assert payload.get("role") == "user"


class TestJWTErrorScenarios:
    def test_decode_token_with_invalid_signature_raises_jwt_error(self):
        token = create_access_token({"sub": "1"})
        
        wrong_key = "wrong-secret-key"
        with pytest.raises(jwt.JWTError):
            jwt.decode(token, wrong_key, algorithms=[ALGORITHM], options={"verify_sub": False})
    
    def test_decode_expired_token_raises_jwt_error(self):
        expired_delta = timedelta(minutes=-10)
        token = create_access_token({"sub": "1"}, expires_delta=expired_delta)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
    
    def test_decode_token_without_sub_returns_none(self):
        to_encode = {"role": "user"}
        expire = datetime.utcnow() + timedelta(minutes=60)
        to_encode.update({"exp": expire})
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        
        assert payload.get("sub") is None
    
    def test_decode_token_with_non_integer_sub_raises_value_error(self):
        token = create_access_token({"sub": "not-an-integer"})
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        user_id_raw = payload.get("sub")
        
        with pytest.raises(ValueError):
            int(user_id_raw)
    
    def test_create_token_with_integer_sub(self):
        token = create_access_token({"sub": 123})
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        
        sub_value = payload.get("sub")
        assert int(sub_value) == 123


class TestTokenIntegration:
    def test_full_token_lifecycle(self):
        user_id = 42
        token = create_access_token({"sub": str(user_id)})
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        
        extracted_id = int(payload.get("sub"))
        assert extracted_id == user_id
