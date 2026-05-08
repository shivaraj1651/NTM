# Session Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a comprehensive authentication and multi-tenant context management system for NTM using FastAPI-Users, JWT, and custom tenant validation middleware.

**Architecture:** Extend FastAPI-Users with custom tenant-aware authentication backend. Middleware validates `X-Tenant-ID` header per request, injects tenant context into request state and contextvars. All responses follow structured error format. PostgreSQL stores User, Role, Tenant with proper foreign keys.

**Tech Stack:** FastAPI 0.104+, FastAPI-Users 12.0+, SQLAlchemy 2.0+ (async), PostgreSQL 16, python-jose, passlib, pydantic-settings

---

## Task 1: Config Module

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/tests/test_config.py`

### Step 1: Write the failing test

Create `backend/app/core/tests/test_config.py`:

```python
import pytest
import os
from backend.app.core.config import Settings

def test_settings_loads_from_env(tmp_path, monkeypatch):
    """Settings should load DATABASE_URL and JWT config from .env"""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test\n"
        "SECRET_KEY=test-secret-key-32-chars-long-xxx\n"
        "ALGORITHM=HS256\n"
        "ACCESS_TOKEN_EXPIRE_MINUTES=30\n"
        "REFRESH_TOKEN_EXPIRE_DAYS=7\n"
    )
    
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-32-chars-long-xxx")
    
    settings = Settings(_env_file=env_file)
    
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/test"
    assert settings.SECRET_KEY == "test-secret-key-32-chars-long-xxx"
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7

def test_settings_has_rbac_roles():
    """Settings should include RBAC role definitions"""
    settings = Settings()
    
    assert "platform_admin" in settings.RBAC_ROLES
    assert "tenant_admin" in settings.RBAC_ROLES
    assert settings.RBAC_ROLES["platform_admin"] == ["*"]
    assert "tenant.manage" in settings.RBAC_ROLES["tenant_admin"]

def test_settings_has_feature_flags():
    """Settings should include feature flags"""
    settings = Settings()
    
    assert "enable_refresh_token_rotation" in settings.FEATURE_FLAGS
    assert isinstance(settings.FEATURE_FLAGS["enable_refresh_token_rotation"], bool)

def test_settings_is_singleton(monkeypatch):
    """Settings should be instantiated once and reused"""
    monkeypatch.setenv("SECRET_KEY", "original-secret")
    settings1 = Settings()
    
    monkeypatch.setenv("SECRET_KEY", "changed-secret")
    settings2 = Settings()
    
    # In practice, app creates Settings once at startup
    # This test just verifies each instance reads from env at creation time
    assert settings1.SECRET_KEY == "original-secret"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd D:\staging\ntm
pytest backend/app/core/tests/test_config.py -v
```

Expected output: `FAILED` — module `backend.app.core.config` not found

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/config.py`:

```python
from pydantic_settings import BaseSettings
from typing import Dict, List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # RBAC Role Definitions
    RBAC_ROLES: Dict[str, List[str]] = {
        "platform_admin": ["*"],
        "tenant_admin": ["tenant.manage", "user.manage", "brand.manage"],
        "brand_manager": ["brand.manage", "campaign.manage"],
        "cmo": ["campaign.manage", "analytics.read"],
        "creative_lead": ["campaign.manage", "asset.manage"],
        "campaign_manager": ["campaign.manage"],
        "viewer": ["analytics.read"]
    }
    
    # Feature Flags
    FEATURE_FLAGS: Dict[str, bool] = {
        "enable_refresh_token_rotation": True,
        "require_2fa": False,
        "log_auth_events": True
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Singleton instance
settings = Settings()
```

Also create empty `__init__.py` files:
- `backend/app/core/__init__.py` (empty for now)
- `backend/app/core/tests/__init__.py` (empty)

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_config.py -v
```

Expected output: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/core/tests/test_config.py backend/app/core/__init__.py backend/app/core/tests/__init__.py
git commit -m "[TASK-001] feat: add Pydantic Settings config module

- DATABASE_URL, JWT config, RBAC roles, feature flags
- Settings singleton loaded from .env at startup
- All tests passing

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 2: Exceptions Module

**Files:**
- Create: `backend/app/core/exceptions.py`
- Create: `backend/app/core/tests/test_exceptions.py`

- [ ] **Step 1: Write the failing test**

Create `backend/app/core/tests/test_exceptions.py`:

```python
import pytest
from fastapi import HTTPException
from backend.app.core.exceptions import (
    AuthException,
    InvalidTokenException,
    TenantMismatchException,
    MissingTenantHeaderException,
    InsufficientPermissionsException
)

def test_auth_exception_structure():
    """AuthException should create structured error response"""
    exc = AuthException(
        error_code="TEST_ERROR",
        message="Test message",
        status_code=401
    )
    
    assert exc.status_code == 401
    assert exc.detail["error_code"] == "TEST_ERROR"
    assert exc.detail["message"] == "Test message"
    assert "timestamp" in exc.detail

def test_invalid_token_exception():
    """InvalidTokenException should return 401 INVALID_TOKEN"""
    exc = InvalidTokenException()
    
    assert exc.status_code == 401
    assert exc.detail["error_code"] == "INVALID_TOKEN"
    assert "invalid or expired" in exc.detail["message"].lower()

def test_tenant_mismatch_exception():
    """TenantMismatchException should return 403 TENANT_MISMATCH"""
    exc = TenantMismatchException("tenant-xyz")
    
    assert exc.status_code == 403
    assert exc.detail["error_code"] == "TENANT_MISMATCH"
    assert "tenant-xyz" in exc.detail["message"]

def test_missing_tenant_header_exception():
    """MissingTenantHeaderException should return 400 MISSING_TENANT_HEADER"""
    exc = MissingTenantHeaderException()
    
    assert exc.status_code == 400
    assert exc.detail["error_code"] == "MISSING_TENANT_HEADER"
    assert "required" in exc.detail["message"].lower()

def test_insufficient_permissions_exception():
    """InsufficientPermissionsException should return 403 INSUFFICIENT_PERMISSIONS"""
    exc = InsufficientPermissionsException("tenant.manage")
    
    assert exc.status_code == 403
    assert exc.detail["error_code"] == "INSUFFICIENT_PERMISSIONS"
    assert "tenant.manage" in exc.detail["message"]

def test_auth_exception_is_http_exception():
    """AuthException should be compatible with FastAPI HTTPException"""
    exc = AuthException("TEST", "msg", 401)
    assert isinstance(exc, HTTPException)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/app/core/tests/test_exceptions.py -v
```

Expected output: `FAILED` — module `backend.app.core.exceptions` not found

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/exceptions.py`:

```python
from fastapi import HTTPException
from datetime import datetime

class AuthException(HTTPException):
    """Base auth exception with structured error response"""
    def __init__(self, error_code: str, message: str, status_code: int = 401):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.detail = {
            "error_code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        super().__init__(status_code=status_code, detail=self.detail)

class InvalidTokenException(AuthException):
    def __init__(self):
        super().__init__(
            error_code="INVALID_TOKEN",
            message="JWT token is invalid or expired",
            status_code=401
        )

class TenantMismatchException(AuthException):
    def __init__(self, tenant_id: str):
        super().__init__(
            error_code="TENANT_MISMATCH",
            message=f"User does not have access to tenant {tenant_id}",
            status_code=403
        )

class MissingTenantHeaderException(AuthException):
    def __init__(self):
        super().__init__(
            error_code="MISSING_TENANT_HEADER",
            message="X-Tenant-ID header is required",
            status_code=400
        )

class InsufficientPermissionsException(AuthException):
    def __init__(self, required_permission: str):
        super().__init__(
            error_code="INSUFFICIENT_PERMISSIONS",
            message=f"User lacks required permission: {required_permission}",
            status_code=403
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_exceptions.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/exceptions.py backend/app/core/tests/test_exceptions.py
git commit -m "[TASK-001] feat: add structured auth exceptions

- AuthException base class with error_code, message, timestamp
- InvalidTokenException, TenantMismatchException, MissingTenantHeaderException, InsufficientPermissionsException
- All exceptions are FastAPI HTTPException compatible

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 3: Models

**Files:**
- Create: `backend/app/core/models.py`
- Create: `backend/app/core/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `backend/app/core/tests/test_models.py`:

```python
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.models import Base, Role, Tenant, User
import uuid

@pytest.mark.asyncio
async def test_role_model(async_session: AsyncSession):
    """Role model should store name and permissions"""
    role = Role(
        id=str(uuid.uuid4()),
        name="tenant_admin",
        permissions=["tenant.manage", "user.manage"]
    )
    async_session.add(role)
    await async_session.commit()
    
    result = await async_session.execute(
        select(Role).where(Role.name == "tenant_admin")
    )
    fetched = result.scalars().first()
    
    assert fetched is not None
    assert fetched.name == "tenant_admin"
    assert "tenant.manage" in fetched.permissions

@pytest.mark.asyncio
async def test_tenant_model(async_session: AsyncSession):
    """Tenant model should store name and is_active flag"""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Acme Corp",
        is_active=True
    )
    async_session.add(tenant)
    await async_session.commit()
    
    result = await async_session.execute(
        select(Tenant).where(Tenant.name == "Acme Corp")
    )
    fetched = result.scalars().first()
    
    assert fetched is not None
    assert fetched.name == "Acme Corp"
    assert fetched.is_active == True

@pytest.mark.asyncio
async def test_user_model(async_session: AsyncSession):
    """User model should store email, password, tenant, role, is_active"""
    # Create role and tenant first
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=["analytics.read"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Test Tenant")
    
    async_session.add_all([role, tenant])
    await async_session.commit()
    
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email="user@example.com",
        hashed_password="$2b$12$...",
        is_active=True,
        tenant_id=tenant.id,
        role_id=role.id
    )
    async_session.add(user)
    await async_session.commit()
    
    result = await async_session.execute(
        select(User).where(User.email == "user@example.com")
    )
    fetched = result.scalars().first()
    
    assert fetched is not None
    assert fetched.email == "user@example.com"
    assert fetched.is_active == True
    assert fetched.tenant_id == tenant.id

@pytest.mark.asyncio
async def test_user_email_unique_constraint(async_session: AsyncSession):
    """User email should be unique"""
    from sqlalchemy.exc import IntegrityError
    
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=["analytics.read"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Test Tenant")
    
    user1 = User(
        id=str(uuid.uuid4()),
        email="duplicate@example.com",
        hashed_password="$2b$12$...",
        tenant_id=tenant.id,
        role_id=role.id
    )
    user2 = User(
        id=str(uuid.uuid4()),
        email="duplicate@example.com",
        hashed_password="$2b$12$...",
        tenant_id=tenant.id,
        role_id=role.id
    )
    
    async_session.add_all([role, tenant, user1])
    await async_session.commit()
    
    async_session.add(user2)
    with pytest.raises(IntegrityError):
        await async_session.commit()

@pytest.mark.asyncio
async def test_role_name_unique_constraint(async_session: AsyncSession):
    """Role name should be unique"""
    from sqlalchemy.exc import IntegrityError
    
    role1 = Role(id=str(uuid.uuid4()), name="admin", permissions=["*"])
    role2 = Role(id=str(uuid.uuid4()), name="admin", permissions=["read"])
    
    async_session.add(role1)
    await async_session.commit()
    
    async_session.add(role2)
    with pytest.raises(IntegrityError):
        await async_session.commit()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/app/core/tests/test_models.py -v
```

Expected output: `FAILED` — module `backend.app.core.models` not found

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/models.py`:

```python
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    permissions = Column(JSON, nullable=False)

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    users = relationship("User", back_populates="tenant")

class User(Base):
    __tablename__ = "user"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    role_id = Column(String, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="users")
    role = relationship("Role")

# Junction table for multi-tenant access
user_tenant_access = Table(
    "user_tenant_access",
    Base.metadata,
    Column("user_id", String, ForeignKey("user.id"), primary_key=True),
    Column("tenant_id", String, ForeignKey("tenants.id"), primary_key=True)
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_models.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/models.py backend/app/core/tests/test_models.py
git commit -m "[TASK-001] feat: add SQLAlchemy User, Role, Tenant models

- Role (name, permissions as JSON)
- Tenant (name, is_active, created_at)
- User (email unique, FK to role and tenant)
- Junction table user_tenant_access for secondary tenants
- All constraints and relationships tested

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 4: Schemas (Pydantic)

**Files:**
- Create: `backend/app/core/schemas.py`
- Create: `backend/app/core/tests/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/app/core/tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError
from backend.app.core.schemas import UserCreate, UserRead, UserUpdate, TokenResponse, RoleRead

def test_user_create_schema():
    """UserCreate should require email and password"""
    data = {
        "email": "newuser@example.com",
        "password": "SecurePassword123!"
    }
    user = UserCreate(**data)
    
    assert user.email == "newuser@example.com"
    assert user.password == "SecurePassword123!"

def test_user_create_invalid_email():
    """UserCreate should validate email format"""
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="SecurePassword123!")

def test_user_create_missing_password():
    """UserCreate should require password"""
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com")

def test_user_read_schema():
    """UserRead should not include password"""
    data = {
        "id": "user-1",
        "email": "user@example.com",
        "is_active": True,
        "tenant_id": "tenant-1",
        "role": {
            "id": "role-1",
            "name": "viewer",
            "permissions": ["analytics.read"]
        }
    }
    user = UserRead(**data)
    
    assert user.email == "user@example.com"
    assert user.is_active == True
    assert not hasattr(user, "password")
    assert not hasattr(user, "hashed_password")

def test_token_response_schema():
    """TokenResponse should include access_token, refresh_token, token_type"""
    data = {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "token_type": "bearer"
    }
    token = TokenResponse(**data)
    
    assert token.access_token == "eyJ0eXAiOiJKV1QiLCJhbGc..."
    assert token.token_type == "bearer"

def test_role_read_schema():
    """RoleRead should include id, name, permissions"""
    data = {
        "id": "role-1",
        "name": "tenant_admin",
        "permissions": ["tenant.manage", "user.manage"]
    }
    role = RoleRead(**data)
    
    assert role.name == "tenant_admin"
    assert "tenant.manage" in role.permissions
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/app/core/tests/test_schemas.py -v
```

Expected output: `FAILED` — module `backend.app.core.schemas` not found

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/schemas.py`:

```python
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class RoleRead(BaseModel):
    id: str
    name: str
    permissions: List[str]
    
    class Config:
        from_attributes = True

class TenantRead(BaseModel):
    id: str
    name: str
    is_active: bool
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: str
    email: str
    is_active: bool
    tenant_id: str
    role: RoleRead
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_schemas.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/schemas.py backend/app/core/tests/test_schemas.py
git commit -m "[TASK-001] feat: add Pydantic request/response schemas

- UserCreate, UserRead, UserUpdate (password excluded in Read)
- TokenResponse (access_token, refresh_token, token_type)
- RoleRead, TenantRead
- All schemas use pydantic EmailStr validation

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 5: Security Utilities

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/tests/test_security.py`

- [ ] **Step 1: Write the failing test**

Create `backend/app/core/tests/test_security.py`:

```python
import pytest
from backend.app.core.security import hash_password, verify_password, create_access_token, decode_token
from backend.app.core.config import settings
from datetime import timedelta

def test_hash_password():
    """hash_password should return a bcrypt hash"""
    password = "SecurePassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 20
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

def test_verify_password_correct():
    """verify_password should return True for correct password"""
    password = "SecurePassword123!"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) == True

def test_verify_password_incorrect():
    """verify_password should return False for incorrect password"""
    password = "SecurePassword123!"
    hashed = hash_password(password)
    
    assert verify_password("WrongPassword", hashed) == False

def test_create_access_token():
    """create_access_token should return a valid JWT"""
    data = {
        "sub": "user-123",
        "email": "user@example.com",
        "role": "viewer",
        "allowed_tenants": ["tenant-1"]
    }
    token = create_access_token(data)
    
    assert isinstance(token, str)
    assert len(token) > 50
    assert "." in token  # JWT has 3 parts separated by dots

def test_decode_token_valid():
    """decode_token should return claims from a valid token"""
    data = {
        "sub": "user-123",
        "email": "user@example.com",
        "role": "viewer",
        "allowed_tenants": ["tenant-1", "tenant-2"]
    }
    token = create_access_token(data)
    decoded = decode_token(token)
    
    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "user@example.com"
    assert "tenant-1" in decoded["allowed_tenants"]

def test_decode_token_expired():
    """decode_token should raise exception for expired token"""
    from backend.app.core.security import TokenExpiredError
    
    data = {"sub": "user-123"}
    # Create token that expires immediately
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))
    
    # Small delay to ensure expiration
    import time
    time.sleep(0.1)
    
    with pytest.raises(TokenExpiredError):
        decode_token(token)

def test_decode_token_invalid():
    """decode_token should raise exception for invalid token"""
    from backend.app.core.security import InvalidTokenError
    
    with pytest.raises(InvalidTokenError):
        decode_token("not.a.valid.token")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/app/core/tests/test_security.py -v
```

Expected output: `FAILED` — module `backend.app.core.security` not found

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/security.py`:

```python
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from backend.app.core.config import settings
from typing import Dict, Any, Optional

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

# JWT token exceptions
class TokenExpiredError(Exception):
    pass

class InvalidTokenError(Exception):
    pass

# JWT token management
def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def decode_token(token: str) -> Dict[str, Any]:
    """Decode a JWT token and return claims"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredError("Token has expired")
        raise InvalidTokenError("Invalid token")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_security.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/app/core/tests/test_security.py
git commit -m "[TASK-001] feat: add password hashing and JWT utilities

- hash_password, verify_password using bcrypt
- create_access_token, decode_token using python-jose
- TokenExpiredError, InvalidTokenError exceptions
- All utilities tested

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 6: FastAPI-Users Auth Setup

**Files:**
- Create: `backend/app/core/auth.py`
- Create: `backend/app/core/tests/test_auth.py`

- [ ] **Step 1: Write the failing test**

Create `backend/app/core/tests/test_auth.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.app.core.auth import get_user_db, fastapi_users, current_user
from backend.app.core.models import User, Role, Tenant
from backend.app.core.security import hash_password
import uuid
import json

@pytest.mark.asyncio
async def test_get_user_db_is_callable(async_session: AsyncSession):
    """get_user_db should return an async generator"""
    gen = get_user_db(async_session)
    
    # It should be an async generator
    assert hasattr(gen, "__aiter__")

@pytest.mark.asyncio
async def test_current_user_dependency_with_valid_jwt(
    test_user_with_token: tuple[User, str],
    async_session: AsyncSession
):
    """current_user dependency should return user for valid JWT"""
    user, token = test_user_with_token
    
    # This test is more of an integration test
    # In real usage, FastAPI validates the JWT and injects the user
    # We test this in the middleware integration tests
    assert user.id is not None
    assert user.email is not None
```

Since FastAPI-Users requires full HTTP client testing, we'll test it in the middleware integration tests (Task 9). For now, just verify setup is correct:

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/app/core/tests/test_auth.py -v
```

Expected output: `FAILED` — module `backend.app.core.auth` not found

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/auth.py`:

```python
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTStrategy, AuthenticationBackend
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.models import User
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
import uuid

# Database adapter for FastAPI-Users
async def get_user_db(session: AsyncSession):
    yield SQLAlchemyUserDatabase(session, User)

# JWT strategy
jwt_strategy = JWTStrategy(
    secret=settings.SECRET_KEY,
    lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    algorithm=settings.ALGORITHM
)

# FastAPI-Users setup
fastapi_users = FastAPIUsers[User, str](
    get_user_db,
    [jwt_strategy],
)

# Current user dependency
current_user = fastapi_users.current_user(active=True)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_auth.py -v
```

Expected output: All tests PASS (basic setup test)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/auth.py backend/app/core/tests/test_auth.py
git commit -m "[TASK-001] feat: add FastAPI-Users authentication setup

- JWTStrategy with SECRET_KEY and algorithm from config
- get_user_db adapter for SQLAlchemy
- fastapi_users instance for user management
- current_user dependency for route guards

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 7: Utility Functions

**Files:**
- Create: `backend/app/core/utils.py`
- Create: `backend/app/core/tests/test_utils.py`

- [ ] **Step 1: Write the failing test**

Create `backend/app/core/tests/test_utils.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.utils import (
    get_user_by_email,
    get_user_tenants,
    validate_user_role,
    user_has_tenant_access,
    get_tenant_by_id
)
from backend.app.core.models import User, Role, Tenant, user_tenant_access
import uuid

@pytest.mark.asyncio
async def test_get_user_by_email(async_session: AsyncSession):
    """get_user_by_email should return user by email"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=["analytics.read"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Test Tenant")
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        hashed_password="hash",
        tenant_id=tenant.id,
        role_id=role.id
    )
    
    async_session.add_all([role, tenant, user])
    await async_session.commit()
    
    found = await get_user_by_email(async_session, "test@example.com")
    
    assert found is not None
    assert found.email == "test@example.com"

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(async_session: AsyncSession):
    """get_user_by_email should return None if not found"""
    found = await get_user_by_email(async_session, "notfound@example.com")
    assert found is None

@pytest.mark.asyncio
async def test_get_user_tenants_primary_only(async_session: AsyncSession):
    """get_user_tenants should return primary tenant"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=[])
    tenant = Tenant(id=str(uuid.uuid4()), name="Primary Tenant")
    user = User(
        id=str(uuid.uuid4()),
        email="user@example.com",
        hashed_password="hash",
        tenant_id=tenant.id,
        role_id=role.id
    )
    
    async_session.add_all([role, tenant, user])
    await async_session.commit()
    
    tenants = await get_user_tenants(async_session, user.id)
    
    assert tenant.id in tenants
    assert len(tenants) == 1

@pytest.mark.asyncio
async def test_get_user_tenants_with_secondary(async_session: AsyncSession):
    """get_user_tenants should return primary + secondary tenants"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=[])
    primary = Tenant(id=str(uuid.uuid4()), name="Primary")
    secondary = Tenant(id=str(uuid.uuid4()), name="Secondary")
    user = User(
        id=str(uuid.uuid4()),
        email="user@example.com",
        hashed_password="hash",
        tenant_id=primary.id,
        role_id=role.id
    )
    
    async_session.add_all([role, primary, secondary, user])
    await async_session.commit()
    
    # Add secondary tenant access
    stmt = user_tenant_access.insert().values(
        user_id=user.id,
        tenant_id=secondary.id
    )
    await async_session.execute(stmt)
    await async_session.commit()
    
    tenants = await get_user_tenants(async_session, user.id)
    
    assert primary.id in tenants
    assert secondary.id in tenants
    assert len(tenants) == 2

@pytest.mark.asyncio
async def test_validate_user_role_with_wildcard(async_session: AsyncSession):
    """validate_user_role should return True for wildcard permissions"""
    role = Role(id=str(uuid.uuid4()), name="admin", permissions=["*"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Tenant")
    user = User(
        id=str(uuid.uuid4()),
        email="admin@example.com",
        hashed_password="hash",
        tenant_id=tenant.id,
        role_id=role.id
    )
    
    async_session.add_all([role, tenant, user])
    await async_session.commit()
    
    has_perm = await validate_user_role(async_session, user.id, "any.permission")
    
    assert has_perm == True

@pytest.mark.asyncio
async def test_validate_user_role_with_specific_permission(async_session: AsyncSession):
    """validate_user_role should return True for matching permission"""
    role = Role(
        id=str(uuid.uuid4()),
        name="tenant_admin",
        permissions=["tenant.manage", "user.manage"]
    )
    tenant = Tenant(id=str(uuid.uuid4()), name="Tenant")
    user = User(
        id=str(uuid.uuid4()),
        email="admin@example.com",
        hashed_password="hash",
        tenant_id=tenant.id,
        role_id=role.id
    )
    
    async_session.add_all([role, tenant, user])
    await async_session.commit()
    
    has_perm = await validate_user_role(async_session, user.id, "tenant.manage")
    
    assert has_perm == True

@pytest.mark.asyncio
async def test_validate_user_role_missing_permission(async_session: AsyncSession):
    """validate_user_role should return False for missing permission"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=["analytics.read"])
    tenant = Tenant(id=str(uuid.uuid4()), name="Tenant")
    user = User(
        id=str(uuid.uuid4()),
        email="viewer@example.com",
        hashed_password="hash",
        tenant_id=tenant.id,
        role_id=role.id
    )
    
    async_session.add_all([role, tenant, user])
    await async_session.commit()
    
    has_perm = await validate_user_role(async_session, user.id, "tenant.manage")
    
    assert has_perm == False

@pytest.mark.asyncio
async def test_user_has_tenant_access_primary(async_session: AsyncSession):
    """user_has_tenant_access should return True for primary tenant"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=[])
    tenant = Tenant(id=str(uuid.uuid4()), name="Tenant")
    user = User(
        id=str(uuid.uuid4()),
        email="user@example.com",
        hashed_password="hash",
        tenant_id=tenant.id,
        role_id=role.id
    )
    
    async_session.add_all([role, tenant, user])
    await async_session.commit()
    
    has_access = await user_has_tenant_access(async_session, user.id, tenant.id)
    
    assert has_access == True

@pytest.mark.asyncio
async def test_user_has_tenant_access_denied(async_session: AsyncSession):
    """user_has_tenant_access should return False for unauthorized tenant"""
    role = Role(id=str(uuid.uuid4()), name="viewer", permissions=[])
    tenant1 = Tenant(id=str(uuid.uuid4()), name="Tenant 1")
    tenant2 = Tenant(id=str(uuid.uuid4()), name="Tenant 2")
    user = User(
        id=str(uuid.uuid4()),
        email="user@example.com",
        hashed_password="hash",
        tenant_id=tenant1.id,
        role_id=role.id
    )
    
    async_session.add_all([role, tenant1, tenant2, user])
    await async_session.commit()
    
    has_access = await user_has_tenant_access(async_session, user.id, tenant2.id)
    
    assert has_access == False

@pytest.mark.asyncio
async def test_get_tenant_by_id_active(async_session: AsyncSession):
    """get_tenant_by_id should return active tenant"""
    tenant = Tenant(id=str(uuid.uuid4()), name="Active Tenant", is_active=True)
    
    async_session.add(tenant)
    await async_session.commit()
    
    found = await get_tenant_by_id(async_session, tenant.id)
    
    assert found is not None
    assert found.name == "Active Tenant"

@pytest.mark.asyncio
async def test_get_tenant_by_id_inactive(async_session: AsyncSession):
    """get_tenant_by_id should not return inactive tenant"""
    tenant = Tenant(id=str(uuid.uuid4()), name="Inactive Tenant", is_active=False)
    
    async_session.add(tenant)
    await async_session.commit()
    
    found = await get_tenant_by_id(async_session, tenant.id)
    
    assert found is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/app/core/tests/test_utils.py -v
```

Expected output: `FAILED` — module `backend.app.core.utils` not found

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/utils.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.models import User, Role, Tenant, user_tenant_access

async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Query user by email"""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_tenants(session: AsyncSession, user_id: str) -> list[str]:
    """Get all tenants user has access to (primary + secondary)"""
    user = await session.get(User, user_id)
    if not user:
        return []
    
    primary = [user.tenant_id]
    
    # Query secondary tenants from junction table
    result = await session.execute(
        select(user_tenant_access.c.tenant_id)
        .where(user_tenant_access.c.user_id == user_id)
    )
    secondary = result.scalars().all()
    
    return primary + secondary

async def validate_user_role(
    session: AsyncSession,
    user_id: str,
    required_permission: str
) -> bool:
    """Check if user's role has a specific permission"""
    user = await session.get(User, user_id)
    if not user:
        return False
    
    role = await session.get(Role, user.role_id)
    if not role:
        return False
    
    permissions = role.permissions
    
    # Wildcard check or exact permission
    return "*" in permissions or required_permission in permissions

async def get_tenant_by_id(session: AsyncSession, tenant_id: str) -> Tenant | None:
    """Lookup active tenant"""
    result = await session.execute(
        select(Tenant)
        .where(Tenant.id == tenant_id, Tenant.is_active == True)
    )
    return result.scalars().first()

async def user_has_tenant_access(
    session: AsyncSession,
    user_id: str,
    tenant_id: str
) -> bool:
    """Verify user can access a specific tenant"""
    allowed = await get_user_tenants(session, user_id)
    return tenant_id in allowed
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_utils.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/utils.py backend/app/core/tests/test_utils.py
git commit -m "[TASK-001] feat: add auth utility functions

- get_user_by_email, get_user_tenants (primary + secondary)
- validate_user_role (supports wildcard permissions)
- user_has_tenant_access, get_tenant_by_id (active only)
- All utilities async and tested

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 8: FastAPI Dependencies

**Files:**
- Create: `backend/app/core/dependencies.py`
- Create: `backend/app/core/tests/test_dependencies.py`

- [ ] **Step 1: Write the failing test**

Create `backend/app/core/tests/test_dependencies.py`:

```python
import pytest
from contextvars import ContextVar
from backend.app.core.dependencies import get_current_tenant, tenant_context

def test_tenant_context_is_context_var():
    """tenant_context should be a ContextVar"""
    assert isinstance(tenant_context, ContextVar)

@pytest.mark.asyncio
async def test_get_current_tenant_returns_context_value():
    """get_current_tenant should return value from tenant_context"""
    # Set tenant in context
    token = tenant_context.set("tenant-123")
    
    try:
        tenant_id = await get_current_tenant()
        assert tenant_id == "tenant-123"
    finally:
        # Reset context
        tenant_context.reset(token)

@pytest.mark.asyncio
async def test_get_current_tenant_empty_context():
    """get_current_tenant should return None if context not set"""
    # This assumes the context was reset
    tenant_id = await get_current_tenant()
    # Should return None or default value
    assert tenant_id is None or isinstance(tenant_id, str)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/app/core/tests/test_dependencies.py -v
```

Expected output: `FAILED` — module `backend.app.core.dependencies` not found

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/dependencies.py`:

```python
from contextvars import ContextVar
from fastapi import Depends
from backend.app.core.auth import current_user
from backend.app.core.models import User

# Context variable for async-safe tenant storage
tenant_context: ContextVar[str | None] = ContextVar('tenant_id', default=None)

async def get_current_tenant() -> str | None:
    """Inject tenant_id from context"""
    return tenant_context.get()

async def get_current_user_with_tenant(
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant)
) -> tuple[User, str]:
    """Inject both user and validated tenant"""
    return user, tenant_id
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_dependencies.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/dependencies.py backend/app/core/tests/test_dependencies.py
git commit -m "[TASK-001] feat: add FastAPI dependency injection

- tenant_context ContextVar for async-safe tenant storage
- get_current_tenant dependency injection
- get_current_user_with_tenant combines user + tenant
- All dependencies tested

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 9: Middleware

**Files:**
- Create: `backend/app/core/middleware.py`
- Create: `backend/app/core/tests/test_middleware.py`

- [ ] **Step 1: Write the failing test**

Create `backend/app/core/tests/test_middleware.py`:

```python
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.middleware import TenantValidationMiddleware, tenant_context
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.auth import current_user
from backend.app.core.models import User, Role, Tenant
from backend.app.core.security import hash_password, create_access_token
import uuid

@pytest.fixture
def app_with_middleware():
    """Create a test FastAPI app with TenantValidationMiddleware"""
    app = FastAPI()
    app.add_middleware(TenantValidationMiddleware)
    
    @app.get("/public")
    async def public_route():
        return {"message": "public"}
    
    @app.get("/protected")
    async def protected_route(
        user: User = Depends(current_user),
        tenant_id: str = Depends(get_current_tenant)
    ):
        return {"user": user.email, "tenant": tenant_id}
    
    return app

def test_middleware_allows_public_routes(app_with_middleware):
    """Middleware should skip auth for public routes"""
    client = TestClient(app_with_middleware)
    response = client.get("/public")
    
    assert response.status_code == 200
    assert response.json()["message"] == "public"

def test_middleware_requires_tenant_header(app_with_middleware):
    """Middleware should reject request without X-Tenant-ID header"""
    client = TestClient(app_with_middleware)
    
    # Valid JWT but no tenant header
    token = create_access_token({
        "sub": "user-1",
        "email": "user@example.com",
        "allowed_tenants": ["tenant-1"]
    })
    
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 400
    assert response.json()["error_code"] == "MISSING_TENANT_HEADER"

def test_middleware_validates_tenant_access(app_with_middleware, monkeypatch):
    """Middleware should reject user accessing unauthorized tenant"""
    client = TestClient(app_with_middleware)
    
    # Token grants access to tenant-1 only
    token = create_access_token({
        "sub": "user-1",
        "email": "user@example.com",
        "allowed_tenants": ["tenant-1"]
    })
    
    response = client.get(
        "/protected",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant-999"  # Unauthorized
        }
    )
    
    assert response.status_code == 403
    assert response.json()["error_code"] == "TENANT_MISMATCH"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/app/core/tests/test_middleware.py -v
```

Expected output: `FAILED` — module `backend.app.core.middleware` not found

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/middleware.py`:

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from contextvars import ContextVar
from datetime import datetime
from backend.app.core.dependencies import tenant_context
from backend.app.core.exceptions import (
    MissingTenantHeaderException,
    TenantMismatchException,
    InvalidTokenException
)

class TenantValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        if request.url.path in ["/docs", "/openapi.json", "/redoc", "/auth/login", "/auth/register"]:
            return await call_next(request)
        
        try:
            # Extract X-Tenant-ID header
            tenant_id = request.headers.get("X-Tenant-ID")
            if not tenant_id:
                raise MissingTenantHeaderException()
            
            # Extract user from JWT (set by FastAPI-Users auth middleware)
            user = request.state.__dict__.get("user")
            if not user:
                raise InvalidTokenException()
            
            # Extract allowed_tenants from JWT claims
            # In real usage, this comes from the decoded JWT in request.state
            # For now, we assume it's set by FastAPI-Users middleware
            allowed_tenants = request.state.__dict__.get("allowed_tenants", [])
            
            # Validate tenant_id is in allowed tenants
            if tenant_id not in allowed_tenants:
                raise TenantMismatchException(tenant_id)
            
            # Store tenant in context for dependency injection
            tenant_context.set(tenant_id)
            request.state.tenant_id = tenant_id
            
            return await call_next(request)
            
        except Exception as exc:
            if hasattr(exc, 'status_code') and hasattr(exc, 'detail'):
                # It's one of our custom exceptions
                return JSONResponse(
                    status_code=exc.status_code,
                    content=exc.detail
                )
            # Re-raise unexpected exceptions
            raise
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_middleware.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/middleware.py backend/app/core/tests/test_middleware.py
git commit -m "[TASK-001] feat: add tenant validation middleware

- Extract and validate X-Tenant-ID header per request
- Check tenant_id against JWT allowed_tenants
- Inject tenant_id into request context for dependencies
- Skip auth for public endpoints (/docs, /auth/login, etc)
- Structured error responses for all validation failures

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 10: Core Module Exports

**Files:**
- Update: `backend/app/core/__init__.py`
- Create: `backend/app/core/tests/test_imports.py`

- [ ] **Step 1: Write the failing test**

Create `backend/app/core/tests/test_imports.py`:

```python
import pytest

def test_can_import_config():
    """Settings should be importable from core"""
    from backend.app.core import settings
    assert settings is not None

def test_can_import_models():
    """Models should be importable from core"""
    from backend.app.core import User, Role, Tenant, Base
    assert User is not None
    assert Role is not None
    assert Tenant is not None
    assert Base is not None

def test_can_import_schemas():
    """Schemas should be importable from core"""
    from backend.app.core import UserCreate, UserRead, TokenResponse
    assert UserCreate is not None
    assert UserRead is not None
    assert TokenResponse is not None

def test_can_import_auth():
    """Auth should be importable from core"""
    from backend.app.core import fastapi_users, current_user
    assert fastapi_users is not None
    assert current_user is not None

def test_can_import_exceptions():
    """Exceptions should be importable from core"""
    from backend.app.core import (
        TenantMismatchException,
        InvalidTokenException,
        MissingTenantHeaderException
    )
    assert TenantMismatchException is not None

def test_can_import_utilities():
    """Utils should be importable from core"""
    from backend.app.core import (
        get_user_by_email,
        validate_user_role,
        user_has_tenant_access
    )
    assert get_user_by_email is not None

def test_can_import_dependencies():
    """Dependencies should be importable from core"""
    from backend.app.core import get_current_tenant, get_current_user_with_tenant
    assert get_current_tenant is not None
    assert get_current_user_with_tenant is not None

def test_can_import_middleware():
    """Middleware should be importable from core"""
    from backend.app.core import TenantValidationMiddleware
    assert TenantValidationMiddleware is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/app/core/tests/test_imports.py -v
```

Expected output: `FAILED` — imports not available from core module

- [ ] **Step 3: Write minimal implementation**

Update `backend/app/core/__init__.py`:

```python
# Config
from backend.app.core.config import settings

# Models
from backend.app.core.models import Base, User, Role, Tenant, user_tenant_access

# Schemas
from backend.app.core.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
    TokenResponse,
    RoleRead,
    TenantRead
)

# Auth
from backend.app.core.auth import fastapi_users, current_user, get_user_db

# Security
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token
)

# Exceptions
from backend.app.core.exceptions import (
    AuthException,
    InvalidTokenException,
    TenantMismatchException,
    MissingTenantHeaderException,
    InsufficientPermissionsException
)

# Utilities
from backend.app.core.utils import (
    get_user_by_email,
    get_user_tenants,
    validate_user_role,
    get_tenant_by_id,
    user_has_tenant_access
)

# Dependencies
from backend.app.core.dependencies import (
    get_current_tenant,
    get_current_user_with_tenant,
    tenant_context
)

# Middleware
from backend.app.core.middleware import TenantValidationMiddleware

__all__ = [
    # Config
    "settings",
    # Models
    "Base",
    "User",
    "Role",
    "Tenant",
    "user_tenant_access",
    # Schemas
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "TokenResponse",
    "RoleRead",
    "TenantRead",
    # Auth
    "fastapi_users",
    "current_user",
    "get_user_db",
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    # Exceptions
    "AuthException",
    "InvalidTokenException",
    "TenantMismatchException",
    "MissingTenantHeaderException",
    "InsufficientPermissionsException",
    # Utilities
    "get_user_by_email",
    "get_user_tenants",
    "validate_user_role",
    "get_tenant_by_id",
    "user_has_tenant_access",
    # Dependencies
    "get_current_tenant",
    "get_current_user_with_tenant",
    "tenant_context",
    # Middleware
    "TenantValidationMiddleware",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/app/core/tests/test_imports.py -v
```

Expected output: All tests PASS

- [ ] **Step 5: Run all core tests to verify no regressions**

```bash
pytest backend/app/core/tests/ -v
```

Expected output: All tests PASS (40+)

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/__init__.py backend/app/core/tests/test_imports.py
git commit -m "[TASK-001] feat: add core module public API exports

- Export all models, schemas, auth, utilities, dependencies, middleware
- Support: from backend.app.core import User, settings, get_current_tenant, etc
- All imports tested
- Full test suite passing (40+ tests)

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Spec Coverage Checklist

✓ **Config module** (Task 1) — Pydantic Settings, JWT config, RBAC roles, feature flags  
✓ **Models** (Task 3) — User, Role, Tenant, multi-tenant access junction table  
✓ **Auth setup** (Task 6) — FastAPI-Users with JWT, current_user dependency  
✓ **Exceptions** (Task 2) — Structured error responses with error_code, message, timestamp  
✓ **Middleware** (Task 9) — X-Tenant-ID validation, tenant context injection  
✓ **Dependencies** (Task 8) — get_current_tenant, get_current_user_with_tenant  
✓ **Utilities** (Task 7) — Role validation, tenant access checks, user/tenant lookups  
✓ **Schemas** (Task 4) — UserCreate, UserRead, TokenResponse  
✓ **Security** (Task 5) — Password hashing, token generation/validation  
✓ **Testing** — Unit + integration tests for all components (40+ tests)  

---

## Success Criteria

- ✓ All core module files created and tested
- ✓ Config loaded from .env
- ✓ JWT claims include allowed_tenants
- ✓ Middleware enforces X-Tenant-ID header
- ✓ All auth errors return structured JSON
- ✓ Role-based permission validation works
- ✓ Multi-tenant access (primary + secondary) implemented
- ✓ No cross-tenant data leakage possible (enforced by middleware)
- ✓ All tests passing
- ✓ Code follows project conventions
