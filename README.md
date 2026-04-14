# neat-appspace-noshow
# Neat Pulse + Appspace No-Show Meeting Cleanup

Automatically **deletes** (cancels) scheduled meetings in Appspace if **no one enters the room** within **5 minutes** of the meeting start time — using real-time presence data from Neat Pulse sensors.

---

## Features

- Polls Neat Pulse presence sensors for your meeting rooms
- Checks Appspace for confirmed reservations that started in the last 5 minutes
- Cancels the reservation in Appspace if the room is empty
- All configuration (keys + room mapping) stored securely in a single `.env` file
- Logs clear status messages for easy monitoring
- Designed to run every 1–2 minutes via cron, GitHub Actions, or any scheduler
- Dry-run mode (logs only, no cancellations)
- Slack **and** Microsoft Teams notifications
- Full Docker / docker-compose support
- GitHub Actions scheduled workflow (every minute)
- All config in one `.env` file

## New Features Explained

### Dry-Run Mode
Set DRY_RUN=true in .env → script will only log what it would cancel and send notifications.

### Notifications

- SLACK_WEBHOOK_URL → Slack incoming webhook
- TEAMS_WEBHOOK_URL → Microsoft Teams incoming webhook
- Both optional — leave blank to disable.

---

## Prerequisites

- Python 3.9 or higher
- Neat Pulse tenant ID + API key
- Appspace Application credentials (`subject_id` and `refresh_token`)
- Access to both Neat Pulse and Appspace admin consoles to get Resource/Room IDs

## Full File List

- neat_appspace_no_show_cleanup.py	<--- Main script
- .env + .env.example 			<--- Environments variables, don't commit .env file to GitHub
- Dockerfile				<--- 
- docker-compose.yml			<--- 
- .github/workflows/no-show-cleanup.yml	<---
- README.md				<--- Readme file (this file)

---

## Quick Start
Edit the `.env.example`, which contains your private keys file and copy to the `.env` file. **DO NOT** commit the `.env` to Github
```
~Bash
cp .env.example .env
pip install requests pytz python-dotenv
python neat_appspace_no_show_cleanup.py
```

### Docker
```
~Bash
docker compose up --build -d

```
### GitHub Actions

Add all your secrets in Repository Settings → Secrets and variables → Actions
Push the .github/workflows/ folder
Workflow runs every minute automatically

_______________________________________________________________________________________________________________________________________

## Acknowledgements
---
This integration was written with the assiatnce of [Grok](https://grok.com)

A special note to Robert Winefield at Appspace :-)
