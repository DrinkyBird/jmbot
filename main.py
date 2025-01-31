import asyncio
import discord
import config
import sys
import os
import db
import webdb
import jmutil
import wrcheck
import botstatus
import operator
import urllib.parse
import time
import math
from discord.ext import commands
from discord import app_commands

import requests
import logging
import http.client
import urllib3
import asyncio

firstRun = True
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents)
databases = [db.Database(x) for x in config.JM_DATABASES]
database = next(x for x in databases if x.is_primary)
webdb = webdb.Database(config.WEB_DB_PATH)

time_in_ms = lambda: time.time() * 1000

ALGO_SEAN = 0
ALGO_SNAIL = 1


async def map_lump_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    results = webdb.map_search(current, 25)
    return [
        app_commands.Choice(name=f"{result[0]} - {result[1]}", value=result[0]) for result in results
    ]


async def wad_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    results = webdb.wad_search(current, 24)
    out = [ app_commands.Choice(name="All WADs", value="all") ]
    for result in results:
        out.append(app_commands.Choice(name=result[1], value=result[0]))
    return out


async def player_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [ app_commands.Choice(name=player, value=player) for player in database.get_all_players() if current in player ][:25]


class Jumpmaze(commands.Cog):
    """Jumpmaze Discord bot commands"""

    async def populate_solo_embed(self, embed, map):
        maptype = database.get_map_type(map)
        rec = database.get_solo_map_record(map) if maptype == "solo" else database.get_jmrun_map_record(map)
        l = database.get_map_records(map)

        embed.add_field(name="Record Time", value=jmutil.ticstime(rec['time']), inline=False)
        embed.add_field(name="Record Date", value=jmutil.format_date(rec['date']), inline=False)
        embed.add_field(name="Record Set By", value=jmutil.strip_colours(rec['author']), inline=False)

        for i in range(min(10, len(l))):    
            user, time = l[i]
            rank = database.get_entry_rank(map + '_pbs', user, False)

            embed.add_field(name=str(rank) + ". " + user, value=jmutil.ticstime(time), inline=True)

    async def populate_team_embed(self, embed, map):
        recs = database.get_team_map_record(map)

        embed.add_field(name="Record Time", value=jmutil.ticstime(recs['time']), inline=False)
        embed.add_field(name="Record Date", value=jmutil.format_date(recs['date']), inline=False)

        for player, points in recs['helpers'].items():
            plural = "s"
            if points == 1:
                plural = ""

            embed.add_field(name=jmutil.strip_colours(player), value=str(points) + " point" + plural, inline=True)

    @app_commands.command(name="map", description="Returns the records for a specified map.")
    @app_commands.describe(map="Lump name", route="Map route")
    @app_commands.autocomplete(map=map_lump_autocomplete)
    async def map(self, interaction: discord.Interaction, map: str, route: int = -1):
        map = map.upper()
        if route >= 1:
            map += ' (Route %d)' % (route,)
        
        maptype = database.get_map_type(map)
        info = webdb.get_map_by_lump(map)

        url = config.SITE_URL + urllib.parse.quote("/maps/%s" % (map,))
        embed = discord.Embed(title="Records for %s (%s)" % (map, info['name']), colour=discord.Colour.blue(), url=url)
        embed.set_thumbnail(url=config.IMAGES_URL + urllib.parse.quote("%s.png" % (map,)))

        if maptype == "solo" or maptype == "jmrun":
            await self.populate_solo_embed(embed, map)

        elif maptype == "team":
            await self.populate_team_embed(embed, map)

        else:
            await interaction.response.send_message(f"Error - No map named `{map}` exists, or it has no set records.", ephemeral=True)
            return
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="wads", description="Returns list of known WADs")
    async def wads(self, interaction: discord.Interaction):
        wads = webdb.get_wads()
        embed = discord.Embed(title="WAD list", colour=discord.Colour.blue())

        for wad in wads:
            maps = webdb.get_wad_maps(wad['slug'])

            embed.add_field(name=wad['name'], value='ID: `%s`\n%d maps total' % (wad['slug'], len(maps)), inline=True)

        await interaction.response.send_message(embed=embed)

    async def do_top(self, interaction: discord.Interaction, wad: str, algo: int = ALGO_SEAN):
        wadinfo = webdb.get_wad_by_slug(wad)
        wadmaps = webdb.get_wad_maps(wad)
        players = database.get_all_players()
        solomaps = database.get_solo_map_names()
        scores = {}

        if wadmaps is None and wad != 'all':
            await interaction.response.send_message(f'No wad `{wad}` exists', ephemeral=True)
            return

        if wad != 'all':
            solomaps = []
            for map in wadmaps:
                maptype = database.get_map_type(map['lump'])
                if maptype == 'solo' or maptype == 'jmrun':
                    solomaps.append(map)
        else:
            wadinfo = {
                'name': 'all maps'
            }

        numsolomaps = len(solomaps)

        playerscounted = 0
        timescounted = 0
        start = time_in_ms()

        for player in players:
            wascounted = False
            scores[player] = 0

            maps = database.get_player_maps(player)

            for map in maps:
                inmaps = False

                if wad != 'all':
                    for m in solomaps:
                        if m['lump'] == map:
                            inmaps = True
                            break

                    if not inmaps:
                        continue

                numentries = len(database.get_map_records(map))

                if algo == ALGO_SEAN:
                    rank = database.get_entry_rank(map + '_pbs', player, True)
                    scores[player] += rank
                elif algo == ALGO_SNAIL:
                    rank = database.get_entry_rank(map + '_pbs', player, False)
                    scores[player] += math.sqrt(numentries) / math.sqrt(rank / 10)

                timescounted += 1
                wascounted = True

            if algo == ALGO_SEAN:
                scores[player] /= numsolomaps

            if wascounted:
                playerscounted += 1

        sortedscores = sorted(scores.items(), key=operator.itemgetter(1), reverse=True)

        end = time_in_ms()
        delta = end - start

        embed = discord.Embed(title="Top players for " + wadinfo['name'], colour=discord.Colour.blue())
        for i in range(min(15, len(sortedscores))):
            player, score = sortedscores[i]

            embed.add_field(name="%d. %s" % (i + 1, player), value="Score: %0.3f" % (score,), inline=True)

        print('Calculated from %s times set by %s players in %f ms.' % (f'{timescounted:,}', f'{playerscounted:,}', delta))
        await interaction.followup.send('Calculated from %s times set by %s players in %f ms.' % (f'{timescounted:,}', f'{playerscounted:,}', delta), embed=embed)
        
    @app_commands.command(name="top", description="Returns the top 10 players for a given WAD or overall (using Sean's points formula)")
    @app_commands.describe(wad="ID of the WAD, defaults to all")
    @app_commands.autocomplete(wad=wad_autocomplete)
    async def top(self, interaction: discord.Interaction, wad: str):
        await interaction.response.defer()
        await self.do_top(interaction, wad, ALGO_SEAN)
        
    @app_commands.command(name="top2", description="Returns the top 10 players for a given WAD or overall (using Snail's points formula)")
    @app_commands.describe(wad="ID of the WAD, defaults to all")
    @app_commands.autocomplete(wad=wad_autocomplete)
    async def top2(self, interaction: discord.Interaction, wad: str):
        await self.do_top(interaction, wad, ALGO_SNAIL)

    @app_commands.command(name="playertime", description="Returns the specified player's time on a specified map")
    @app_commands.describe(player="Player username")
    @app_commands.autocomplete(player=player_autocomplete)
    @app_commands.describe(map="Map lump name")
    @app_commands.autocomplete(map=map_lump_autocomplete)
    @app_commands.describe(route="Map route")
    async def playertime(self, interaction: discord.Interaction, player: str, map: str, route: int = -1):
        map = map.upper()
        mapinfo = webdb.get_map_by_lump(map)
        if route >= 1:
            map += ' (Route %d)' % (route,)
        ns = map + '_pbs'

        player = player.lower()

        if not database.entry_exists(ns, player):
            await interaction.response.send_message(f"Error - No player named {player} exists, or they have not set a time for {map}.", ephemeral=True)
            return

        time = int(database.get_entry(ns, player))
        rank = database.get_entry_rank(ns, player, False)

        url = config.SITE_URL + urllib.parse.quote("/players/%s" % (player,))
        embed = discord.Embed(title="%s's time for %s (%s)" % (player, map, mapinfo['name']), colour=discord.Colour.teal(), url=url)
        embed.set_thumbnail(url=config.IMAGES_URL + urllib.parse.quote("%s.png" % (map,)))

        embed.add_field(name="Time", value=jmutil.ticstime(time), inline=True)
        embed.add_field(name="Rank", value=str(rank), inline=True)
        embed.add_field(name="Date", value=jmutil.format_timestamp(database.get_timestamp(ns, player)), inline=True)

        await interaction.response.send_message(embed=embed)


@client.command(hidden=True)
async def exit(ctx):
    if ctx.author.id in config.ADMINS:
        await ctx.message.reply('wtf', mention_author=False)
        await client.close()
        sys.exit()

@client.command(hidden=True)
async def say(ctx, target, msg):
    if ctx.author.id in config.ADMINS:
        try:
            channel = client.get_channel(int(target))
            await channel.send(msg)
        except Exception as e:
            await ctx.send('An error occured (`' + str(e) + '`) - channel doesn\'t exist, is in invalid format, or isn\'t accessible by the bot')

@client.command(hidden=True)
async def ver(ctx):
    s = ''
    s += 'Python: %s\n' % (sys.version)
    s += 'discord.py: %s\n' % (discord.__version__)

    if hasattr(os, 'uname'):
        s += 'uname: %s\n' % (str(os.uname()))

    await ctx.reply(s, mention_author=False)

@client.event
async def on_ready():
    for guild in client.guilds:
        client.tree.copy_global_to(guild=guild)
        await client.tree.sync(guild=guild)
    client.loop.create_task(wrcheck.poll_thread_target(client, databases, webdb))
    client.loop.create_task(botstatus.change_target(client))
    game = discord.Game("Jumpmaze")
    await client.change_presence(status=discord.Status.online, activity=game)

async def main():
    if config.DEBUG:
        http.client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    async with client:
        await client.add_cog(Jumpmaze())
        await client.start(config.BOT_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
