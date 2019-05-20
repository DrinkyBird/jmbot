# jmbot
## Install
1. Grab dependencies: `python3 -m pip install -U discord.py`
2. Create `config.py` and fill it:

```python
# Your Discord bot token
BOT_TOKEN=""
# Your Jumpmaze sqlite database path
JM_DB_PATH='C:/Users/Sean/Documents/jumpmaze.db'

# List of IDs of bot admins
ADMINS=[
    195246948847058954
]

# ID of channel to send notification to (for WRs etc)
NOTIFY_CHANNEL=563395640357421057

# How often to check for world records (in seconds)
WR_POLL_FREQ = 60
```

3. `python main.py`