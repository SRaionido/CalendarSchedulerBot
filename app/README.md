# Discord Scheduler Bot

A Discord bot for coordinating schedules with friends. Members can post their availability by day and time, create shared events, and view everyone's schedule as a generated calendar image. All data is stored in JSON files and automatically cleaned up each day.

---

## Features

- Add and remove personal availability windows (up to 3 time ranges per day)
- View your own availability, filtered by month if needed
- Render a full monthly calendar image showing every member's available hours as colour-coded blocks
- Create titled events with a date and time duration
- Delete events by ID
- View all upcoming events as rich Discord embeds, each with a one-click Google Calendar link (no account access required)
- Automatic daily cleanup — any availability or event data from before today is purged every 24 hours
- Modular storage layer: swap from JSON to SQLite or PostgreSQL without touching command code
- Separate production and development environments — one image, isolated data directories

---

## Project Structure

```
CalendarSchedulerBot/
│
├── app/                              # Bot source code and Dockerfile
│   ├── bot.py                        # Entry point — starts the bot, registers all cogs
│   ├── config.py                     # All settings, read from environment variables
│   ├── requirements.txt
│   ├── .env.example                  # Template — copy into production/ or development/
│   ├── Dockerfile                    # Image definition — referenced by both compose files
│   ├── commands/
│   │   ├── availability.py           # /add_availability /remove_availability
│   │   │                             # /my_availability /clear_month
│   │   ├── calendar_view.py          # /view_month
│   │   └── events.py                 # /create_event /delete_event /upcoming
│   ├── storage/
│   │   ├── base.py                   # Abstract interface — implement to add a new backend
│   │   ├── __init__.py               # Factory: returns the configured backend instance
│   │   └── json_storage.py           # Thread-safe JSON implementation (default)
│   ├── tasks/
│   │   └── cleanup.py                # Background task: purges past data every 24 hours
│   └── utils/
│       ├── time_parser.py            # Parses dates, times, and time ranges from user input
│       └── calendar_render.py        # Generates monthly calendar PNG via matplotlib
│
├── production/
│   ├── docker-compose.yml            # Runs the pre-built image — never builds from source
│   ├── .env                          # Production secrets (never committed to git)
│   └── data/                         # Production JSON data files (never committed to git)
│
└── development/
    ├── docker-compose.yml            # Builds from source on demand
    ├── .env                          # Dev secrets (never committed to git)
    └── data/                         # Dev JSON data files (never committed to git)
```

---

## Setup

### 1. Create a Discord bot

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** and give it a name
3. Go to **Bot** → **Add Bot**
4. Copy the **Token** — you will need it for your `.env` file
5. Go to **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, select `Send Messages` and `Attach Files` permissions, and use the generated URL to invite the bot to your server

For development it is recommended to create a second separate bot application so test output never appears in your production server.

### 2. Configure environment files

Copy the example env file into each environment folder and fill in the token:

```bash
cp app/.env.example production/.env
cp app/.env.example development/.env
```

`production/.env`:
```env
DISCORD_TOKEN=your_production_bot_token_here
DATA_DIR=/app/data
STORAGE_BACKEND=json
```

`development/.env`:
```env
DISCORD_TOKEN=your_dev_bot_token_here
DATA_DIR=/app/data
STORAGE_BACKEND=json
```

### 3. Development workflow

Build from source and run against the isolated dev data directory:

```bash
cd development
docker compose up -d --build    # build image from ../app and start
docker compose logs -f          # follow logs
docker compose down             # stop
```

Every time you change source code, run `docker compose up -d --build` again to rebuild and restart.

### 4. Promoting to production

Build the image once and tag it, then start production:

```bash
# Build and tag the image from source
cd app
docker build -t scheduler-bot:latest .

# Start production (no build step — just runs the tagged image)
cd ../production
docker compose up -d
docker compose logs -f
```

### 5. Updating production after a code change

```bash
# Rebuild the image with new code
cd app
docker build -t scheduler-bot:latest .

# Restart production — it picks up the new image automatically
cd ../production
docker compose up -d
```

Production never builds from source directly. It only ever runs images you have deliberately built and tagged, so a half-finished change in `app/` can never accidentally reach production.

### 6. Run locally without Docker

```bash
cd app
pip install -r requirements.txt
python bot.py
```

---

## Commands

### Availability

| Command | Description |
|---|---|
| `/add_availability date start1 end1 [start2 end2] [start3 end3]` | Save your available hours for a date. Up to 3 time windows. Times accept `HH:MM` (24-hour) or `9am` / `2:30pm` style. |
| `/remove_availability date` | Remove all your availability for a specific date. |
| `/my_availability [month]` | View your saved availability. Optionally filter to a month with `YYYY-MM`. |
| `/clear_month month` | Wipe all your availability entries for an entire month. |

### Calendar

| Command | Description |
|---|---|
| `/view_month [month]` | Post a calendar image showing everyone's availability for a month. Defaults to the current month. |

### Events

| Command | Description |
|---|---|
| `/create_event title date start_time end_time` | Create a titled event. Rejects dates in the past. |
| `/delete_event event_id` | Delete an event by its 8-character ID. |
| `/upcoming` | List all upcoming events as Discord embeds, each with a Google Calendar link that pre-fills the event details. No account access required. |

---

## Time Format Reference

All time inputs accept either 24-hour or 12-hour format:

| Input | Interpreted as |
|---|---|
| `09:00` | 9:00 AM |
| `14:30` | 2:30 PM |
| `9am` | 9:00 AM |
| `2pm` | 2:00 PM |
| `11:30am` | 11:30 AM |

All date inputs use `YYYY-MM-DD` (e.g. `2025-07-04`).
All month inputs use `YYYY-MM` (e.g. `2025-07`).

---

## Data Storage

Two JSON files are created automatically inside the environment's `data/` directory:

**`availability.json`** — stores each user's available time ranges per date:
```json
{
  "guild_id": {
    "users": { "user_id": "Display Name" },
    "availability": {
      "user_id": {
        "2025-07-04": [["09:00", "12:00"], ["14:00", "17:00"]]
      }
    }
  }
}
```

**`events.json`** — stores created events per guild:
```json
{
  "guild_id": {
    "a1b2c3d4": {
      "id": "a1b2c3d4",
      "title": "Game Night",
      "date": "2025-07-04",
      "start_time": "19:00",
      "end_time": "22:00",
      "created_by": "user_id",
      "created_by_name": "Display Name"
    }
  }
}
```

Production and development each have their own `data/` folder inside their respective environment directories. They never share data.

### Automatic cleanup

A background task runs every 24 hours (and immediately on startup) that deletes all availability entries and events whose date is before today. The purge is logged each time it runs:

```
Daily purge complete — removed 3 availability entry/entries and 1 past event(s) (cutoff: 2025-07-05).
```

---

## Switching to a Real Database

The entire storage layer sits behind an abstract interface in `storage/base.py`. To add a new backend:

1. Create `app/storage/postgres_storage.py` (or sqlite, etc.) implementing every method in `BaseStorage`
2. Add a branch to the factory in `app/storage/__init__.py`
3. Set `STORAGE_BACKEND=postgres` in your `.env` and add any connection config to `app/config.py`

Nothing in `commands/`, `tasks/`, or `bot.py` needs to change.

---

## Docker Notes

### Why the two compose files work differently

The **development** compose file includes a `build:` block pointing at `../app`. Running `docker compose up -d --build` rebuilds the image from your current source code every time. This is what you want during active development.

The **production** compose file has no `build:` block at all. It references `image: scheduler-bot:latest`, which must already exist on the machine. Docker will refuse to start if the image has not been built yet. This separation means production can never accidentally run code you have not deliberately promoted.

### Clock sync

Both compose files mount `/etc/localtime:/etc/localtime:ro`. This is required. Discord slash command interactions expire after 3 seconds, and if the container clock drifts from the host clock even slightly, the bot will fail every command with an `Unknown interaction` error.

### Running both environments simultaneously

Production and development can run at the same time on the same machine. They are independent containers with separate data volumes and (ideally) separate bot tokens, so they do not interfere with each other.

### Slash command propagation

On first run, global slash commands can take up to an hour to appear in Discord. For instant propagation during development, edit `app/bot.py` and pass your guild ID to the sync call:

```python
synced = await bot.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))
```

Remove the guild argument before promoting to production so commands appear in all servers.

---

## .gitignore

Keep secrets and data files out of version control:

```
production/.env
production/data/

development/.env
development/data/
```

The compose files, Dockerfile, and source code are all safe to commit.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "The application did not respond" | Container clock out of sync | Confirm `/etc/localtime:/etc/localtime:ro` is in the compose volumes |
| Production fails to start with "image not found" | Image was never built | Run `cd app && docker build -t scheduler-bot:latest .` first |
| Slash commands don't appear | Global sync delay | Wait up to 1 hour, or use guild-specific sync during dev |
| `LoginFailure` in logs | Wrong or missing token | Check the `.env` file in the environment folder you are running from |
| Permission errors on `data/` | Folder owned by root | `sudo chown -R 1000:1000 production/data` or `development/data` |
| `Synced 0 slash command(s)` | Bot crashed before `on_ready` | Check logs for errors above that line |