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

```
PasswordHasher (interface)         UserRepository (interface)         SessionRepository (interface)
        |                                   |                                 |
        v                                   v                                 v
   BCryptHasher                   InMemoryUserRepo                   InMemorySessionRepo

         |                                   |                                 |
         +-------------------+   +-----------+-----------+   +-----------------+
                             |   |                       |   |
                             v   v                       v   v
                         +------------------+        TotpService (interface)
                         |   AuthService    |                |
                         +------------------+                v
                         | +signup()        |           DefaultTotp
                         | +login()         |
                         | +logout()        |        EmailService (interface)
                         | +enable2FA()     |
                         | +verifyTOTP()    |
                         | +resetPassword() |
                         +------------------+
```

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

```java
import java.util.concurrent.atomic.AtomicInteger;

public class User {
    private final String id;
    private final String email;
    private String passwordHash;
    private boolean twoFactorEnabled;
    private String totpSecret;
    private long lockedUntil;
    private final AtomicInteger failedLoginAttempts = new AtomicInteger(0);
    // ...constructors, getters, setters...
}
```

**`Session.java` (Model)**

```java
import java.time.Instant;

public class Session {
    private final String sessionId;
    private final String userId;
    private final Instant expiresAt;
    // ...constructors, getters...
}
```

**`PasswordHasher.java` (Interface and Implementation)**

```java
public interface PasswordHasher {
    String hash(String password);
    boolean verify(String password, String hash);
}

public class BCryptPasswordHasher implements PasswordHasher {
    public String hash(String password) {
        return org.mindrot.jbcrypt.BCrypt.hashpw(password, org.mindrot.jbcrypt.BCrypt.gensalt());
    }
    public boolean verify(String password, String hash) {
        return org.mindrot.jbcrypt.BCrypt.checkpw(password, hash);
    }
}
```

**`TotpService.java` (Interface and Mock Implementation)**

```java
public interface TotpService {
    String generateSecret();
    boolean verify(String secret, String code);
}

public class MockTotpService implements TotpService {
    public String generateSecret() { return "SECRET"; }
    public boolean verify(String secret, String code) { return code.equals("123456"); }
}
```

**`UserRepository.java` (Interface and In-Memory Implementation)**

```java
import java.util.concurrent.ConcurrentHashMap;

public interface UserRepository {
    User findByEmail(String email);
    User findById(String id);
    void save(User user);
}

public class InMemoryUserRepository implements UserRepository {
    private final ConcurrentHashMap<String, User> byId = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, User> byEmail = new ConcurrentHashMap<>();
    public User findByEmail(String email) { return byEmail.get(email); }
    public User findById(String id) { return byId.get(id); }
    public void save(User user) {
        byId.put(user.getId(), user);
        byEmail.put(user.getEmail(), user);
    }
}
```

**`SessionRepository.java` (Interface and In-Memory Implementation)**

```java
import java.util.concurrent.ConcurrentHashMap;

public interface SessionRepository {
    void save(Session session);
    Session findById(String sessionId);
    void deleteByUserId(String userId);
}

public class InMemorySessionRepository implements SessionRepository {
    private final ConcurrentHashMap<String, Session> byId = new ConcurrentHashMap<>();
    public void save(Session session) { byId.put(session.getSessionId(), session); }
    public Session findById(String sessionId) { return byId.get(sessionId); }
    public void deleteByUserId(String userId) {
        byId.values().removeIf(s -> s.getUserId().equals(userId));
    }
}
```

**`AuthService.java` (Core Logic)**

```java
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

public class AuthServiceImpl implements AuthService {
    private final UserRepository userRepo;
    private final SessionRepository sessionRepo;
    private final PasswordHasher hasher;
    private final TotpService totpService;
    // ...TokenService, EmailService omitted for brevity...

    public AuthServiceImpl(UserRepository userRepo, SessionRepository sessionRepo, PasswordHasher hasher, TotpService totpService) {
        this.userRepo = userRepo;
        this.sessionRepo = sessionRepo;
        this.hasher = hasher;
        this.totpService = totpService;
    }

    public User signup(String email, String password) throws UserAlreadyExistsException {
        if (userRepo.findByEmail(email) != null) throw new UserAlreadyExistsException();
        User user = new User(UUID.randomUUID().toString(), email, hasher.hash(password));
        userRepo.save(user);
        return user;
    }

    public Session login(String email, String password) throws UserNotFoundException, InvalidCredentialsException, AccountLockedException, TwoFactorRequiredException {
        User user = userRepo.findByEmail(email);
        if (user == null) throw new UserNotFoundException();
        if (user.getLockedUntil() > System.currentTimeMillis()) throw new AccountLockedException();
        if (!hasher.verify(password, user.getPasswordHash())) {
            int attempts = user.getFailedLoginAttempts().incrementAndGet();
            if (attempts > 5) {
                user.setLockedUntil(System.currentTimeMillis() + 15 * 60 * 1000);
            }
            userRepo.save(user);
            throw new InvalidCredentialsException();
        }
        user.getFailedLoginAttempts().set(0);
        user.setLockedUntil(0);
        userRepo.save(user);
        if (user.isTwoFactorEnabled()) throw new TwoFactorRequiredException(user.getId());
        Session session = new Session(UUID.randomUUID().toString(), user.getId(), Instant.now().plusSeconds(3600));
        sessionRepo.save(session);
        return session;
    }

    public Session verifyLoginWithTotp(String userId, String totpCode) throws UserNotFoundException, InvalidCredentialsException {
        User user = userRepo.findById(userId);
        if (user == null) throw new UserNotFoundException();
        if (!totpService.verify(user.getTotpSecret(), totpCode)) throw new InvalidCredentialsException();
        Session session = new Session(UUID.randomUUID().toString(), user.getId(), Instant.now().plusSeconds(3600));
        sessionRepo.save(session);
        return session;
    }

    public void logout(String sessionId) {
        // Remove session (not shown)
    }

    public Optional<Session> validateSession(String sessionId) {
        Session s = sessionRepo.findById(sessionId);
        if (s == null || s.getExpiresAt().isBefore(Instant.now())) return Optional.empty();
        return Optional.of(s);
    }

    public String generate2FASecret(String userId) throws UserNotFoundException {
        User user = userRepo.findById(userId);
        if (user == null) throw new UserNotFoundException();
        String secret = totpService.generateSecret();
        user.setTotpSecret(secret);
        userRepo.save(user);
        return secret;
    }

    public void enable2FA(String userId, String totpCode) throws UserNotFoundException, InvalidCredentialsException {
        User user = userRepo.findById(userId);
        if (user == null) throw new UserNotFoundException();
        if (!totpService.verify(user.getTotpSecret(), totpCode)) throw new InvalidCredentialsException();
        user.setTwoFactorEnabled(true);
        userRepo.save(user);
    }

    public void requestPasswordReset(String email) throws UserNotFoundException {
        // Omitted for brevity
    }
    public void completePasswordReset(String resetToken, String newPassword) throws InvalidTokenException {
        // Omitted for brevity
    }
}
```

**Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class AuthServiceTest {
    private AuthServiceImpl authService;
    @BeforeEach
    void setup() {
        authService = new AuthServiceImpl(new InMemoryUserRepository(), new InMemorySessionRepository(), new BCryptPasswordHasher(), new MockTotpService());
    }
    @Test
    void testSignupAndLogin() throws Exception {
        User user = authService.signup("test@example.com", "password");
        assertNotNull(user);
        Session session = authService.login("test@example.com", "password");
        assertNotNull(session);
    }
    @Test
    void testBruteForceLockout() throws Exception {
        authService.signup("a@b.com", "pw");
        for (int i = 0; i < 6; i++) {
            try { authService.login("a@b.com", "wrong"); } catch (InvalidCredentialsException | AccountLockedException ignored) {}
        }
        assertThrows(AccountLockedException.class, () -> authService.login("a@b.com", "pw"));
    }
    // ...more tests for 2FA, password reset, etc...
}
```
