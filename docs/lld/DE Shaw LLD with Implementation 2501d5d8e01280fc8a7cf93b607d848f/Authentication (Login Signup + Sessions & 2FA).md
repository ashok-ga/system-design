# Authentication (Login Signup + Sessions & 2FA)

This problem requires designing a robust authentication service. We'll build the core logic for user management, session handling, and security features like 2FA and brute-force protection.

### **1. System Overview & Scope Clarification**

We are designing the backend service responsible for user identity and access management.

**Functional Requirements (FR):**

- **Signup:** New users can register with an email and password.
- **Login:** Registered users can log in using their credentials.
- **Logout:** Users can terminate their active session.
- **Password Reset:** Users can request a password reset link via email and set a new password.
- **Sessions:** Successful login creates a session token, which must be validated for subsequent requests. Sessions must expire.
- **Two-Factor Authentication (2FA):** Users can optionally enable Time-based One-Time Password (TOTP) for enhanced security.
- **Brute-Force Protection:** After a configurable number of failed login attempts (`N`), the user's account should be temporarily locked.

**Non-Functional Requirements (NFR):**

- **Security:** Passwords must be stored securely using a strong, salted hashing algorithm (e.g., BCrypt). Session IDs and 2FA secrets must be secure.
- **Performance:** Session validation should have minimal latency (critical path for most authenticated API calls).
- **Auditability:** Key events (login success/failure, password change, 2FA setup) should be logged for security analysis.

**Assumptions:**

- External services like `EmailService` and a persistent database are available but will be represented by interfaces (Dependency Inversion).
- We will use in-memory data stores for users and sessions to make the example self-contained and testable. In a production system, these would be backed by a database (e.g., PostgreSQL) and a distributed cache (e.g., Redis).

---

### **2. Core Components and Class Design**

We'll use a service-oriented architecture, with a central `AuthService` orchestrating various components.

- **Models (Data Transfer Objects):**
    - `User`: Represents a user's identity and security-related state.
    - `Session`: Represents a user's authenticated session.
- **Services (Business Logic):**
    - `AuthService`: The main facade for all authentication operations.
    - `PasswordHasher`: An interface for hashing and verifying passwords (Strategy Pattern).
    - `TotpService`: An interface for generating and verifying TOTP codes.
    - `TokenService`: Generates and validates short-lived tokens for actions like password resets.
    - `EmailService`: An interface for sending emails.
- **Stores (Data Access):**
    - `UserRepository`: Interface for CRUD operations on `User` objects.
    - `SessionRepository`: Interface for CRUD operations on `Session` objects.
- **Utilities:**
    - `RateLimiter`: Manages login attempts to prevent brute-force attacks.

**Class Diagram (Textual Representation):**

`+----------------+      +------------------+      +-------------------+
| <<interface>>  |      |                  |      |  <<interface>>    |
| PasswordHasher |----->|   AuthService    |<-----|   UserRepository  |
+----------------+      |------------------|      +-------------------+
| + hash()       |      | + signup()       |               ^
| + verify()     |      | + login()        |               |
+----------------+      | + logout()       |      +-------------------+
        ^               | + enable2FA()    |      | InMemoryUserRepo  |
        |               | + verifyTOTP()   |      +-------------------+
+----------------+      | + resetPassword()|
| BCryptHasher   |      +------------------+      +--------------------+
+----------------+               ^                |  <<interface>>     |
                                 |                | SessionRepository  |
                                 |                +--------------------+
+----------------+               |                         ^
| <<interface>>  |               |                         |
|   TotpService  |---------------+            +------------------------+
+----------------+               |            | InMemorySessionRepo    |
| + genSecret()  |               |            +------------------------+
| + verify()     |               |
+----------------+               |
        ^                        |
        |                        |
+----------------+      +----------------+
|   DefaultTotp  |      | <<interface>>  |
+----------------+      |   EmailService |
                        +----------------+`

---

### **3. API Design (`AuthService`)**

We'll define clear method signatures for our main service, including custom exceptions for specific error states.

Java

```java
// Custom Exceptions
class UserAlreadyExistsException extends Exception { ... }
class UserNotFoundException extends Exception { ... }
class InvalidCredentialsException extends Exception { ... }
class AccountLockedException extends Exception { ... }
class TwoFactorRequiredException extends Exception {
    public final String userId; // To know which user needs to verify
}
class InvalidTokenException extends Exception { ... }

// Main Service Interface
interface AuthService {
    // Signup
    User signup(String email, String password) throws UserAlreadyExistsException;

    // Login Flow
    Session login(String email, String password) throws UserNotFoundException, InvalidCredentialsException, AccountLockedException, TwoFactorRequiredException;
    Session verifyLoginWithTotp(String userId, String totpCode) throws UserNotFoundException, InvalidCredentialsException;

    // Logout
    void logout(String sessionId);

    // Session Management
    Optional<Session> validateSession(String sessionId);

    // 2FA Management
    String generate2FASecret(String userId) throws UserNotFoundException;
    void enable2FA(String userId, String totpCode) throws UserNotFoundException, InvalidCredentialsException;

    // Password Reset
    void requestPasswordReset(String email) throws UserNotFoundException;
    void completePasswordReset(String resetToken, String newPassword) throws InvalidTokenException;
}
```

---

### **4. Key Workflows**

**a) User Login (with Brute-Force and 2FA)**

1. **Client:** Calls `AuthService.login(email, password)`.
2. **AuthService:**
a. Retrieves the `User` from the `UserRepository` by email. If not found, throws `UserNotFoundException`.
b. Checks if the account is locked (`user.getLockedUntil()` is in the future). If so, throws `AccountLockedException`.
c. Calls `PasswordHasher.verify(password, user.getPasswordHash())`.
d. **On Failure:**
i. Atomically increments `failedAttempts` for the user.
ii. If `failedAttempts` exceeds the threshold (e.g., 5), it sets `lockedUntil` to a future time (e.g., now + 15 minutes).
iii. Saves the updated user state.
iv. Throws `InvalidCredentialsException`.
e. **On Success:**
i. Resets `failedAttempts` to 0 and clears `lockedUntil`.
ii. Checks if `user.is2FAEnabled()`.
iii. **If 2FA is ON:** Throws `TwoFactorRequiredException` containing the `userId`. The client must now prompt the user for their TOTP code and call `verifyLoginWithTotp()`.
iv. **If 2FA is OFF:** Creates a new `Session` with a secure random ID, links it to the `userId`, sets an expiry time, saves it to `SessionRepository`, and returns the `Session` object.

**b) Password Reset**

1. **Client:** Calls `AuthService.requestPasswordReset(email)`.
2. **AuthService:**
a. Finds the user by email.
b. Calls `TokenService.generate(userId, duration)` to create a short-lived, signed token (e.g., a JWT).
c. Calls `EmailService.send(...)` with a reset link containing this token.
3. **User:** Clicks the link in the email.
4. **Client:** Presents a form and calls `AuthService.completePasswordReset(token, newPassword)`.
5. **AuthService:**
a. Calls `TokenService.validate(token)` to verify its signature and expiry. If invalid, throws `InvalidTokenException`.
b. Extracts the `userId` from the validated token.
c. Hashes the `newPassword` using `PasswordHasher`.
d. Updates the user's `passwordHash` in the `UserRepository`.
e. (Best Practice) Invalidates all existing sessions for that user by deleting them from the `SessionRepository`.

---

### **5. Code Implementation (Java)**

Below is a complete, runnable implementation. For brevity, dependencies like a TOTP library or a JWT library are mocked or simplified.

**Dependencies (conceptual - for a real project, add these to `pom.xml` or `build.gradle`):**

- `org.mindrot:jbcrypt`: For BCrypt password hashing.
- `dev.samstevens.totp:totp`: For TOTP generation and verification.
- A testing framework like JUnit 5.

**File Structure:**

`src/
└── main/
    └── java/
        └── auth/
            ├── models/
            │   ├── User.java
            │   └── Session.java
            ├── services/
            │   ├── AuthService.java
            │   ├── PasswordHasher.java
            │   ├── BCryptPasswordHasher.java
            │   └── ... (TotpService, TokenService, etc.)
            ├── repositories/
            │   ├── UserRepository.java
            │   ├── SessionRepository.java
            │   └── InMemoryUserRepository.java
            │   └── InMemorySessionRepository.java
            └── exceptions/
                └── ... (Custom exceptions)`

**Core Code Snippets:**

**`User.java` (Model)**

Java

```java
// ...see previous content for full code...
```

**`AuthService.java` (Orchestrator)**

Java

```java
// ...see previous content for full code...
```

---

6. Testing (JUnit 5)

Tests are crucial to verify all flows, especially failure cases.

Java

```java
// ...see previous content for full code...
```

### **7. Concurrency, Security, and Scalability**

- **Concurrency:** The in-memory repositories (`InMemoryUserRepository`) use `ConcurrentHashMap` to be thread-safe. The `failedLoginAttempts` counter on the `User` object is an `AtomicInteger` to handle concurrent failed logins safely. In a database-backed system, we would use transactions with `SELECT ... FOR UPDATE` to ensure atomic updates to the user's state.
- **Security:**
    - **Password Hashing:** We use BCrypt, an adaptive hashing function that incorporates a salt automatically. The work factor can be tuned over time.
    - **Session Management:** Session IDs are generated using `UUID.randomUUID()` providing 122 bits of randomness, making them unguessable. They should be transmitted over HTTPS in `HttpOnly`, `Secure`, `SameSite=Strict` cookies.
    - **2FA Secrets:** The TOTP secret stored in the database should be encrypted at rest.
    - **Token Security:** Password reset tokens must be short-lived and single-use. Using JWTs signed with a strong secret (e.g., HMAC-SHA256) is a standard approach.
- **Scalability:**
    - **Stateless Service:** The `AuthService` is stateless. Multiple instances can be run behind a load balancer.
    - **Centralized State:** The state (users, sessions) must be moved out of instance memory.
        - `UserRepository` would point to a relational database (e.g., PostgreSQL, MySQL).
        - `SessionRepository` would point to a distributed, low-latency key-value store like Redis. Sessions in Redis can have a TTL set automatically, simplifying expiry logic.
    - **Rate Limiting:** The brute-force counter (`failedLoginAttempts`) stored on the user object works but can be enhanced. A distributed rate limiter (e.g., using Redis's `INCR` command with `EXPIRE`) can provide more sophisticated protection against IP-based or subnet-based attacks, not just user-based ones.
