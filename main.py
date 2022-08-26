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
import jimgit
from discord.ext import commands

firstRun = True
intents = discord.Intents.default()
client = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents)
database = db.Database(config.JM_DB_PATH)
webdb = webdb.Database(config.WEB_DB_PATH)

time_in_ms = lambda: time.time() * 1000

ALGO_SEAN = 0
ALGO_SNAIL = 1

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

    @commands.command(help="Returns the records for a specified map.", usage="<lump> [route]")
    async def map(self, ctx, map, route=-1):
        map = map.upper()
        if route >= 1:
            map += ' (Route %d)' % (route,)
        
        maptype = database.get_map_type(map)
        info = webdb.get_map_by_lump(map)

        url = config.SITE_URL + urllib.parse.quote("/maps/%s" % (map,))
        embed = discord.Embed(title="Records for %s (%s)" % (map, info['name']), colour=discord.Colour.blue(), url=url)
        embed.set_thumbnail(url=config.SITE_URL + urllib.parse.quote("/img/maps/%s.png" % (map,)))

        if maptype == "solo" or maptype == "jmrun":
            await self.populate_solo_embed(embed, map)

        elif maptype == "team":
            await self.populate_team_embed(embed, map)

        else:
            await ctx.send("Error - No map named %s exists, or it has no set records." % (map,))
            return
            
        await ctx.send(embed=embed)

    @commands.command(help="Returns list of known WADs")
    async def wads(self, ctx):
        wads = webdb.get_wads()
        embed = discord.Embed(title="WAD list", colour=discord.Colour.blue())

        for wad in wads:
            maps = webdb.get_wad_maps(wad['slug'])

            embed.add_field(name=wad['name'], value='ID: `%s`\n%d maps total' % (wad['slug'], len(maps)), inline=True)

        await ctx.send(embed=embed)

    async def do_top(self, ctx, wad, algo=ALGO_SEAN):
        await ctx.trigger_typing()

        wadinfo = webdb.get_wad_by_slug(wad)
        wadmaps = webdb.get_wad_maps(wad)
        players = database.get_all_players()
        solomaps = database.get_solo_map_names()
        scores = {}

        if wadmaps is None and wad != 'all':
            await ctx.send('No wad %s exists' % (wad,))
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

        await ctx.send('Calculated from %s times set by %s players in %f ms.' % (f'{timescounted:,}', f'{playerscounted:,}', delta), embed=embed)
        
    @commands.command(help="Returns the top 10 players for a given WAD or overall (using Sean's points formula)", usage='[wad]')
    async def top(self, ctx, wad='all'):
        await self.do_top(ctx, wad, ALGO_SEAN)
        
    @commands.command(help="Returns the top 10 players for a given WAD or overall (using Snail's points formula)", usage='[wad]')
    async def top2(self, ctx, wad='all'):
        await self.do_top(ctx, wad, ALGO_SNAIL)

    @commands.command(help="Returns the specified player's time on a specified map", usage="<player> <lump> [route]")
    async def playertime(self, ctx, player, map, route=-1):
        map = map.upper()
        mapinfo = webdb.get_map_by_lump(map)
        if route >= 1:
            map += ' (Route %d)' % (route,)
        ns = map + '_pbs'

        player = player.lower()

        if not database.entry_exists(ns, player):
            await ctx.send("Error - No player named %s exists, or they have not set a time for %s." % (player, map))
            return

        time = int(database.get_entry(ns, player))
        rank = database.get_entry_rank(ns, player, False)

        url = config.SITE_URL + urllib.parse.quote("/players/%s" % (player,))
        embed = discord.Embed(title="%s's time for %s (%s)" % (player, map, mapinfo['name']), colour=discord.Colour.teal(), url=url)
        embed.set_thumbnail(url=config.SITE_URL + urllib.parse.quote("/img/maps/%s.png" % (map,)))

        embed.add_field(name="Time", value=jmutil.ticstime(time), inline=True)
        embed.add_field(name="Rank", value=str(rank), inline=True)
        embed.add_field(name="Date", value=jmutil.format_timestamp(database.get_timestamp(ns, player)), inline=True)

        await ctx.reply(embed=embed)


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
    game = discord.Game("Jumpmaze")
    await client.change_presence(status=discord.Status.online, activity=game)

client.loop.create_task(wrcheck.poll_thread_target(client, database, webdb))
client.loop.create_task(botstatus.change_target(client))
client.add_cog(Jumpmaze())
client.add_cog(jimgit.JimGit())
client.run(config.BOT_TOKEN)