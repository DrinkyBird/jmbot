import discord
import config
import sys
import db
import jmutil
import wrcheck
import operator
import urllib.parse
from discord.ext import commands

firstRun = True
client = commands.Bot(command_prefix=config.COMMAND_PREFIX)
database = db.Database(config.JM_DB_PATH)

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

        url = config.SITE_URL + urllib.parse.quote("/maps/%s" % (map,))
        embed = discord.Embed(title="Records for " + map, colour=discord.Colour.blue(), url=url)
        embed.set_thumbnail(url=config.SITE_URL + urllib.parse.quote("/img/maps/%s.png" % (map,)))

        if maptype == "solo" or maptype == "jmrun":
            await self.populate_solo_embed(embed, map)

        elif maptype == "team":
            await self.populate_team_embed(embed, map)

        else:
            await ctx.send("Error - No map named %s exists, or it has no set records." % (map,))
            return
            
        await ctx.send(embed=embed)

    @commands.command(help="Returns the top 10 players")
    async def top(self, ctx):
        players = database.get_all_players()
        solomaps = database.get_solo_map_names()
        scores = {}

        numsolomaps = len(solomaps)

        for player in players:
            scores[player] = 0

            maps = database.get_player_maps(player)

            for map in maps:
                rank = database.get_entry_rank(map + '_pbs', player, True)
                scores[player] += rank

            scores[player] /= numsolomaps

        sortedscores = sorted(scores.items(), key=operator.itemgetter(1), reverse=True)

        embed = discord.Embed(title="Top Players", colour=discord.Colour.blue())
        for i in range(min(15, len(sortedscores))):
            player, score = sortedscores[i]

            embed.add_field(name="%d. %s" % (i + 1, player), value="Score: %0.3f" % (score,), inline=True)

        await ctx.send(embed=embed)

    @commands.command(help="Returns the specified player's time on a specified map", usage="<player> <lump> [route]")
    async def playertime(self, ctx, player, map, route=-1):
        map = map.upper()
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
        embed = discord.Embed(title="%s's time for %s" % (player, map), colour=discord.Colour.teal(), url=url)
        embed.set_thumbnail(url=config.SITE_URL + urllib.parse.quote("/img/maps/%s.png" % (map,)))

        embed.add_field(name="Time", value=jmutil.ticstime(time), inline=True)
        embed.add_field(name="Rank", value=str(rank), inline=True)

        await ctx.send(embed=embed)


@client.command()
async def exit(ctx):
    print(ctx.author.id)
    if ctx.author.id in config.ADMINS:
        await client.close()
        sys.exit()
    else:
        await ctx.send("No")

@client.event
async def on_ready():
    game = discord.Game("Jumpmaze")
    await client.change_presence(status=discord.Status.online, activity=game)

client.loop.create_task(wrcheck.poll_thread_target(client, database))
client.add_cog(Jumpmaze())
client.run(config.BOT_TOKEN)