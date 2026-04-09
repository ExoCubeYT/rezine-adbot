<div align="center">

<img src="https://i.pinimg.com/originals/2c/85/01/2c85015ad0b929bc0139f1e168533457.gif" width="160" />

# Rezine AdBot

```txt
> distributed telegram broadcast engine
> multi-account orchestration • rate-limit aware • resumable jobs
```

<p>
  <img src="https://img.shields.io/badge/python-3.13-0f172a?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/telethon-mtproto-111827?style=for-the-badge" />
  <img src="https://img.shields.io/badge/ptb-async%20v20+-020617?style=for-the-badge" />
</p>

</div>

---

## ░░ architecture

```txt
               ┌───────────────────────┐
               │     Telegram Bot      │
               │  (python-telegram)    │
               └──────────┬────────────┘
                          │ commands / ui
                          ▼
               ┌───────────────────────┐
               │   campaign manager    │
               │   (queue + state)     │
               └──────────┬────────────┘
                          │ jobs
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌───────────────┐                 ┌────────────────┐
│ account pool  │                 │   persistence   │
│ (telethon)    │                 │   sqlite + enc  │
└──────┬────────┘                 └────────────────┘
       │
       ▼
┌───────────────┐
│ telegram api  │
│ (rate limits) │
└───────────────┘
```

---

## ░░ why this exists

manually forwarding ads = slow + inconsistent + gets rate-limited fast

this project treats broadcasting like a **job system**:

* tasks
* queues
* workers (accounts)
* retry + backoff

---

## ░░ feature surface

```txt
[+] multi-account worker pool
[+] floodwait-aware scheduler
[+] resumable campaigns (crash safe)
[+] full media pipeline
[+] encrypted session storage
[+] inline bot control panel
```

---

## ░░ internals

### job model

```py
Campaign {
  id
  account_id
  payload (message/media)
  targets[]
  progress_index
  status
}
```

execution loop:

```txt
for group in targets:
    try send()
    except FloodWait:
        sleep(wait)
        retry
    persist_progress()
```

---

### rate limiting strategy

* detect `FloodWaitError`
* pause only affected worker
* continue others
* resume automatically

no dumb global sleep.

---

### session security

```txt
telethon session
   ↓
serialize
   ↓
fernet encrypt
   ↓
sqlite store
```

no plaintext sessions. ever.

---

## ░░ setup

```bash
git clone https://github.com/yourusername/rezine-adbot.git
cd rezine-adbot
pip install -r requirements.txt
cp .env.example .env
```

`.env`

```env
BOT_TOKEN=
API_ID=
API_HASH=
ADMIN_ID=
DB_PATH=data/bot.db
```

run:

```bash
python run.py
```

---

## ░░ usage flow

```txt
/start
  → add account
  → create campaign
  → attach payload
  → dispatch
```

control:

```txt
[▶ start] [⏸ pause] [✖ cancel]
```

---

## ░░ admin surface

```txt
/admin
  ├─ users
  ├─ stats
  └─ global broadcast
```

---

## ░░ design choices

* sqlite > overkill db
* queues > threads spam
* encryption > convenience
* resume > restart

---

## ░░ extending

ideas if you fork:

```txt
- proxy rotation per account
- ai caption variation
- smart group filtering
- web dashboard (fastapi)
- redis queue backend
```

---

## ░░ note

this is not a toy script.
this is a **system**.

---

<div align="center">

<img src="https://i.pinimg.com/originals/2c/85/01/2c85015ad0b929bc0139f1e168533457.gif" width="140" />

```txt
> automate quietly
> scale horizontally
```

---

## ⭐ star this project

if this helped you or you liked the system design,
consider dropping a star — it actually helps visibility.

</div>
