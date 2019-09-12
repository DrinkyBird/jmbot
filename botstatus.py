import random
import asyncio
import discord
import sys

GAME_LIST = [
    'Jumpmaze',
    'H-Doom',
    'complex doom, probably',
    'megaman, probably',
    'banning Snail',
    'with itself',
    'thrashing the database file',
    'IRC is better tbh',
    'WEYO',
    'ZDaemon',
    'Odamex',
    'Skulltag',
    'csDoom',
    'Wrack',
    'Python ' + sys.version
]

lastGame = 0

async def perform_change(client):
    global lastGame

    newGame = 0

    while True:
        newGame = random.randint(0, len(GAME_LIST) - 1)
        if newGame != lastGame:
            break

    lastGame = newGame

    game = discord.Game(GAME_LIST[newGame])
    await client.change_presence(status=discord.Status.online, activity=game)

async def change_target(client):
    await client.wait_until_ready()

    while not client.is_closed():
        await perform_change(client)
        await asyncio.sleep(random.randint(1, 60) * 60)