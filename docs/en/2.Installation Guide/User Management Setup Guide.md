This document explains how to switch from the legacy login system to the new user management/login system with password management.

## 1. Enable the new login mode
Set the following in `.env`:
```
VITE_ENABLE_NEW_AUTH=True
```
Meaning:
* `False`: legacy simple login (default).
* `True`: new user management/login system with registration, encrypted password storage, password reset, and session management.

Before enabling, make sure Redis and SMTP are configured (see below). Otherwise registration and password reset will not work.

## 2. Redis configuration (sessions, codes, lock)
The new user management/login system relies on Redis for temporary and security-related data.

Redis is required for:
- Temporary storage of verification codes (registration/reset)
- Login rate limiting and account lock status
- Short-lived session and security-related state

### Quick Redis via Docker
```bash
docker run -d --name jiuwen-redis -p 6379:6379 redis:latest
```
Note: Running Redis via Docker does not require manually downloading or installing any dependencies.

If you prefer not to use Docker, you can install Redis locally (steps vary by OS), which is not covered here.

### `.env` settings
```
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```
If you did not set a Redis password, keep `REDIS_PASSWORD` empty.

## 3. SMTP configuration (email codes)
SMTP is used to send registration and password reset codes.

### Get an SMTP authorization code
For common providers (QQ/163):
1. Log in to the webmail.
2. Go to Settings -> Account.
3. Enable POP3/IMAP/SMTP service.
4. Generate a 16-digit authorization code.

Important: `SMTP_PASSWORD` must be the authorization code, not the mailbox login password.
Warning: Using the mailbox login password instead of an SMTP authorization code will usually fail or be blocked by the provider.

### `.env` settings
```
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_16_digit_auth_code
SMTP_ALIAS=OpenJiuwen Support
```

## 4. Behavior notes (from the new login logic)
* Verification code is 6 digits and expires in 10 minutes.
* Code sending is rate-limited to 60 seconds.
* Login failures are limited to 5 attempts, then the account is locked for 30 minutes.
* Login success or password reset clears the lock/failure status.

## 5. Checklist before switching
* `.env` variable names match `.env.example`.
* Redis is running if `VITE_ENABLE_NEW_AUTH=True`.
* SMTP settings are valid and `SMTP_PASSWORD` is an authorization code.
* Firewall allows ports 6379 (Redis) and 465 (SMTP).

After enabling the new login system, legacy login behavior may change.
Ensure clients are prepared to handle token expiration and re-login flows.

## Warning
If you plan to deploy this service on a public or untrusted network, strongly recommend performing a security risk assessment and applying necessary protections and hardening before deployment.
