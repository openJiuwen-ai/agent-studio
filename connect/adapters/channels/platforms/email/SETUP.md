# Email Bot Setup Guide

The Email bot polls an **IMAP inbox** for unread messages and replies via **SMTP**.
It uses only the Python standard library — no extra dependencies are required.

The sender's email address is used as the persistent user ID, so each person
who emails the bot gets their own session and token.

---

## Quick Start — How Does This Work?

**Simple explanation:**

1. **You create a dedicated email account** (e.g., `mybot@gmail.com`)
2. **You start the email bot**, giving it the email credentials
3. **Anyone can email commands to `mybot@gmail.com`**
4. **The bot reads those emails, processes commands, and replies**

**Example flow:**
- User creates `aibot@gmail.com` and gets an App Password
- They start the bot: `python -m connect.adapters.channels.run email imap.gmail.com smtp.gmail.com aibot@gmail.com APP_PASSWORD`
- **You** send an email to `aibot@gmail.com` with the body: `help`
- The bot reads your email, processes the `help` command, and sends you a reply
- You reply to that email with another command (e.g., `agents`), and the bot responds again

**Key point:** You send emails **TO** the bot's email address (`aibot@gmail.com`), and the bot replies **FROM** that same address.

---

## Prerequisites

- Python 3.9+
- An email account with IMAP enabled (Gmail, Outlook, or any IMAP/SMTP provider)
- A running OpenJiuwen backend

---

## Step 1 — Install Dependencies

```bash
pip install -r channels/requirements.txt
```

*(No additional packages are needed for the email bot.)*

---

## Step 2 — Enable IMAP on Your Email Account

### Gmail

1. Open Gmail → **Settings (gear icon)** → **See all settings**.
2. Go to **Forwarding and POP/IMAP** tab.
3. Under **IMAP access**, select **Enable IMAP**.
4. Click **Save Changes**.

**Important — create an App Password (required if 2-Step Verification is on):**

1. Go to [Google Account](https://myaccount.google.com/) → **Security**.
2. Under "How you sign in to Google", click **2-Step Verification**.
3. Scroll to the bottom → **App passwords**.
4. Select **Mail** and your device → click **Generate**.
5. Copy the 16-character password — use this as `<PASSWORD>` below.

### Outlook / Microsoft 365

1. Sign in to [outlook.com](https://outlook.com) → **Settings** → **Mail** → **Sync email**.
2. Enable **IMAP** access.
3. IMAP host: `outlook.office365.com`, SMTP host: `smtp-mail.outlook.com`

### Other providers

Consult your provider's documentation for IMAP/SMTP hostnames and ports.

---

## Step 3 — Start the Bot

### Gmail

```bash
python -m connect.adapters.channels.run email \
  imap.gmail.com smtp.gmail.com \
  bot@gmail.com APP_PASSWORD
```

### Outlook

```bash
python -m connect.adapters.channels.run email \
  outlook.office365.com smtp-mail.outlook.com \
  bot@outlook.com YOUR_PASSWORD \
  --smtp-port 587
```

### With custom backend URL

```bash
python -m connect.adapters.channels.run email \
  imap.gmail.com smtp.gmail.com \
  bot@gmail.com APP_PASSWORD \
  --backend-url http://my-server:8000
```

### With slower polling (reduces IMAP load)

```bash
python -m connect.adapters.channels.run email \
  imap.gmail.com smtp.gmail.com \
  bot@gmail.com APP_PASSWORD \
  --poll-interval 30
```

### Using environment variables

```bash
export BACKEND_URL=http://my-server:8000
export EMAIL_POLL_INTERVAL=30
python -m connect.adapters.channels.run email imap.gmail.com smtp.gmail.com bot@gmail.com APP_PASSWORD
```

---

## All Options

| Argument / Option | Required | Description |
|---|---|---|
| `IMAP_HOST` | Yes | IMAP server hostname |
| `SMTP_HOST` | Yes | SMTP server hostname |
| `EMAIL_ADDRESS` | Yes | Email address the bot monitors and replies from |
| `PASSWORD` | Yes | Email account password or app-specific password |
| `--imap-port PORT` | No | IMAP SSL port. Default: `993`. Env: `IMAP_PORT` |
| `--smtp-port PORT` | No | SMTP STARTTLS port. Default: `587`. Env: `SMTP_PORT` |
| `--backend-url URL` | No | OpenJiuwen backend URL. Default: `http://localhost:8000`. Env: `BACKEND_URL` |
| `--access-token TOKEN` | No | Static backend token (skips per-user login). Env: `ACCESS_TOKEN` |
| `--poll-interval N` | No | Seconds between inbox polls. Default: `10`. Env: `EMAIL_POLL_INTERVAL` |

---

## How It Works

**Email Flow:**
1. **Users send emails TO the bot's address** (e.g., `aibot@gmail.com`)
2. **The bot polls its IMAP inbox** every `--poll-interval` seconds for `UNSEEN` messages
3. **The bot extracts the command** from the first non-quoted, non-empty line of the email body
4. **The bot processes the command** (login, workflow, agent chat, etc.)
5. **The bot replies FROM the same address** using SMTP, maintaining the email thread

**Technical Details:**
- The first non-quoted, non-empty line of each email body is treated as the command
- Quoted reply text (lines starting with `>` or reply separators) is ignored — so you can reply to a bot email with your next command
- The bot replies in the same thread using SMTP with `In-Reply-To` and `References` headers
- Each sender's email address becomes their unique user ID for persistent sessions

---

## Available Commands

Send these as the first line of an email body to the bot's address:

| Command | Description |
|---|---|
| `login` | Log in to the OpenJiuwen backend |
| `logout` | Log out |
| `status` | Check login status |
| `cancel` | Cancel any active operation |
| `health` | Check backend connectivity |
| `help` | Show all available commands |
| `workflows` | List all workflows |
| `workflows search <query>` | Search workflows by keyword |
| `workflow execute <id>` | Run a workflow (bot replies with parameter prompts) |
| `workflow skip` | Skip an optional parameter |
| `workflow cancel` | Cancel parameter collection |
| `agents` | List all agents |
| `agents search <query>` | Search agents by keyword |
| `agent execute <id> <message>` | Send a single message to an agent |
| `agent chat <id>` | Start an interactive chat session |

**Multi-turn flows** (login, workflow parameter collection, agent chat) work by replying to the bot's email. Each reply you send is read as the next input.

---

## Token Storage

User session tokens are stored in:

```
channels/platforms/email/.email_tokens.json
```

Each token is keyed by the sender's email address (lowercase).

This file is listed in `.gitignore` and will not be committed.

---

## Production Deployment

Example systemd service:

```ini
[Unit]
Description=OpenJiuwen Email Bot
After=network.target

[Service]
WorkingDirectory=/opt/openjiuwen
ExecStart=python -m connect.adapters.channels.run email \
          imap.gmail.com smtp.gmail.com \
          bot@gmail.com APP_PASSWORD \
          --backend-url http://localhost:8000 \
          --poll-interval 15
Restart=always
EnvironmentFile=/opt/openjiuwen/.env

[Install]
WantedBy=multi-user.target
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `IMAP login failed` | Check email/password. For Gmail use an App Password, not your account password |
| `SMTP authentication failed` | Same — use App Password for Gmail |
| Bot doesn't see new emails | Confirm IMAP is enabled in account settings |
| Bot replies to wrong thread | Check that the email client sends `In-Reply-To` header correctly |
| Bot reads old emails on startup | IMAP `UNSEEN` flag is used — only emails received after SEEN mark |
| Commands not recognised | Make sure the command is the very first non-blank line of the email body, not after a quoted reply |
| Gmail blocks login | Enable IMAP and use an App Password; "Less secure app access" is not required |
