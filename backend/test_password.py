import bcrypt
import hashlib


def _preprocess_password(password: str) -> bytes:
    return hashlib.sha256(password.encode('utf-8')).hexdigest().encode('utf-8')


def get_password_hash_old(password: str) -> str:
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def get_password_hash_new(password: str) -> str:
    preprocessed = _preprocess_password(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(preprocessed, salt)
    return hashed.decode('utf-8')


def verify_password_old(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode('utf-8')
    if len(plain_bytes) > 72:
        plain_bytes = plain_bytes[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def verify_password_new(plain_password: str, hashed_password: str) -> bool:
    preprocessed = _preprocess_password(plain_password)
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(preprocessed, hashed_bytes)


def test_password_length():
    print("=" * 60)
    print("测试密码哈希功能")
    print("=" * 60)
    
    test_cases = [
        ("短密码", "Test123"),
        ("普通长度密码", "MyTestPassword123!"),
        ("50字节密码", "a" * 50),
        ("70字节密码", "a" * 70),
        ("72字节密码", "a" * 72),
        ("73字节密码", "a" * 73),
        ("100字节密码", "a" * 100),
        ("200字节密码", "a" * 200),
        ("含特殊字符的长密码", "TestPassword!@#$%^&*()" * 10),
    ]
    
    print("\n1. 测试旧方法（直接 bcrypt 哈希）：")
    print("-" * 60)
    for name, password in test_cases:
        byte_length = len(password.encode('utf-8'))
        try:
            hashed = get_password_hash_old(password)
            verified = verify_password_old(password, hashed)
            print(f"  ✓ {name}: {len(password)} 字符 ({byte_length} 字节) - 成功, 验证: {verified}")
        except Exception as e:
            print(f"  ✗ {name}: {len(password)} 字符 ({byte_length} 字节) - 失败: {e}")
    
    print("\n2. 测试新方法（SHA-256 预处理 + bcrypt 哈希）：")
    print("-" * 60)
    for name, password in test_cases:
        byte_length = len(password.encode('utf-8'))
        preprocessed = _preprocess_password(password)
        preprocessed_length = len(preprocessed)
        
        try:
            hashed = get_password_hash_new(password)
            verified = verify_password_new(password, hashed)
            print(f"  ✓ {name}: {len(password)} 字符 ({byte_length} 字节)")
            print(f"    预处理后: {preprocessed_length} 字节 (SHA-256 哈希)")
            print(f"    验证结果: {verified}")
        except Exception as e:
            print(f"  ✗ {name}: {len(password)} 字符 ({byte_length} 字节) - 失败: {e}")
    
    print("\n3. 测试向后兼容性：")
    print("-" * 60)
    
    test_password = "TestPassword123!"
    
    print(f"\n  使用旧方法创建密码哈希: {test_password}")
    old_hash = get_password_hash_old(test_password)
    print(f"  哈希值: {old_hash[:30]}...")
    
    print(f"\n  测试新验证函数是否能验证旧哈希：")
    
    def verify_password_backward_compatible(plain_password: str, hashed_password: str) -> bool:
        preprocessed = _preprocess_password(plain_password)
        hashed_bytes = hashed_password.encode('utf-8')
        
        try:
            if bcrypt.checkpw(preprocessed, hashed_bytes):
                return True
        except Exception:
            pass
        
        try:
            plain_bytes = plain_password.encode('utf-8')
            if len(plain_bytes) > 72:
                plain_bytes = plain_bytes[:72]
            if bcrypt.checkpw(plain_bytes, hashed_bytes):
                return True
        except Exception:
            pass
        
        return False
    
    result = verify_password_backward_compatible(test_password, old_hash)
    print(f"  ✓ 新验证函数验证旧哈希: {result}")
    
    print(f"\n4. 测试密码复杂度要求：")
    print("-" * 60)
    
    import re
    
    def validate_password_complexity(password: str):
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_symbol = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        categories = sum([has_upper, has_lower, has_digit, has_symbol])
        
        return {
            'valid': categories >= 2,
            'categories': {
                'has_upper': has_upper,
                'has_lower': has_lower,
                'has_digit': has_digit,
                'has_symbol': has_symbol
            },
            'categories_count': categories
        }
    
    complexity_test_cases = [
        ("全小写", "password"),
        ("全大写", "PASSWORD"),
        ("全数字", "123456"),
        ("小写+大写", "Password"),
        ("小写+数字", "password123"),
        ("大写+数字", "PASSWORD123"),
        ("小写+符号", "password!"),
        ("三类：小写+大写+数字", "Password123"),
        ("四类：全部", "Password123!"),
    ]
    
    for name, password in complexity_test_cases:
        result = validate_password_complexity(password)
        status = "✓ 通过" if result['valid'] else "✗ 不通过"
        cats = []
        if result['categories']['has_upper']: cats.append("大写")
        if result['categories']['has_lower']: cats.append("小写")
        if result['categories']['has_digit']: cats.append("数字")
        if result['categories']['has_symbol']: cats.append("符号")
        print(f"  {status}: {name} ({password}) - 包含: {', '.join(cats) or '无'} ({result['categories_count']} 类)")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_password_length()
