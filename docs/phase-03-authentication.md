# Harbor — Phase 3: Authentication & JWT

## Objective

Implement secure user authentication and authorization for Harbor.

Phase 3 provides:

- User registration
- Password hashing
- User login
- JWT access tokens
- Token expiration
- Token verification
- Current-user resolution
- Protected API endpoints
- Foundation for user-scoped Harbor data

## Technologies

- FastAPI
- Pydantic
- PostgreSQL
- Supabase
- bcrypt
- PyJWT
- OAuth2PasswordBearer

## Registration Flow

Client
  |
  v
POST /api/v1/auth/register
  |
  v
Validate request
  |
  v
Check duplicate email
  |
  v
Hash password using bcrypt
  |
  v
Store user in PostgreSQL

Plain-text passwords are never stored.

## Login Flow

Client
  |
  v
POST /api/v1/auth/login
  |
  v
Lookup user
  |
  v
Verify bcrypt password
  |
  v
Check active status
  |
  v
Generate JWT
  |
  v
Return access token

## JWT Claims

The access token contains minimal identity information:

- sub: user UUID
- email: user email
- iat: issued-at timestamp
- exp: expiration timestamp

Sensitive data such as passwords and API keys must never be stored in
JWT payloads.

## Protected Requests

Protected API requests use:

Authorization: Bearer <access-token>

FastAPI extracts and verifies the JWT before the protected route is
executed.

## Current User Dependency

The get_current_user dependency:

1. Reads bearer token
2. Verifies JWT signature
3. Validates token expiration
4. Reads the user UUID from sub
5. Loads the user from PostgreSQL
6. Confirms the user is active
7. Returns authenticated user information

## Endpoints

### POST /api/v1/auth/register

Creates a Harbor account.

### POST /api/v1/auth/login

Authenticates the user and returns a JWT access token.

### GET /api/v1/auth/me

Protected endpoint that returns the currently authenticated user.

## Security Decisions

- Passwords are hashed using bcrypt.
- Password hashes are never returned through the API.
- JWTs expire.
- JWT signing secret is stored in backend environment configuration.
- Login errors do not reveal whether a specific email exists.
- Inactive users cannot log in or use protected routes.
- Supabase service credentials remain backend-only.
- Future conversations will be filtered by authenticated user ID.

## Environment Variables

JWT_SECRET_KEY
JWT_ALGORITHM
JWT_ACCESS_TOKEN_EXPIRE_MINUTES

The actual JWT secret must never be committed to Git.

## Phase 3 Completion Criteria

- Registration succeeds
- Duplicate registration is rejected
- Password is stored only as a bcrypt hash
- Correct login returns JWT
- Incorrect login returns 401
- Expired/invalid JWT is rejected
- /auth/me requires authentication
- /auth/me identifies the correct user
- JWT secret is excluded from Git

## Next Phase

Phase 4 will introduce Harbor's knowledge-base ingestion system.

It will prepare documents for RAG by supporting:

- document loading
- text extraction
- document metadata
- cleaning
- source tracking
- section/page tracking
- ingestion pipeline structure