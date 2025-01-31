# jmbot
## Install
1. Grab dependencies: `python3 -m pip install -U discord.py`
2. Create `config.py` and fill it:

```python
# Your Discord bot token
BOT_TOKEN=""

# Your Jumpmaze sqlite database path
JM_DATABASES = [
    {
        "path": "/mnt/games/Doom/Zandronum/jm",
        "primary": True,
        "name": "Primary",
    },
    {
        "path": "/home/sean/Dev/jmbot/jumpmaze.db",
        "primary": False,
        "name": "test",
        "wr_colour": 0xFF00FF,
    }
]

WEB_DB_PATH='/home/sean/Dev/jmbot/website.db'

# List of IDs of bot admins
ADMINS=[
    195246948847058954
]

# ID of channel to send notification to (for WRs etc)
NOTIFY_CHANNEL=563395640357421057

# How often to check for world records (in seconds)
WR_POLL_FREQ = 60

# Location of your JM site
SITE_URL = "https://firestick.games/jumpmaze"
IMAGES_URL = "https://firestick.games/assets/jmmaps/"

COMMAND_PREFIX = '%'

# Enable debugging spam
DEBUG = False
```

3. `python main.py`