import discord
import config
import sys
import db
import jmutil
import wrcheck
from discord.ext import commands

firstRun = True
client = commands.Bot(command_prefix='%')
database = db.Database(config.JM_DB_PATH)

class Jumpmaze(commands.Cog):
    """Jumpmaze Discord bot commands"""

    @commands.command(help="Returns the records for a specified map.", usage="<lump>")
    async def map(self, ctx, map):
        map = map.upper()
        maptype = database.get_map_type(map)

        url = "%s/maps/%s" % (config.SITE_URL, map)
        embed = discord.Embed(title="Records for " + map, colour=discord.Colour.blue(), url=url)
        embed.set_thumbnail(url="%s/img/maps/%s.png" % (config.SITE_URL, map))

        if maptype == "solo" or maptype == "jmrun":
            rec = database.get_solo_map_record(map) if maptype == "solo" else database.get_jmrun_map_record(map)
            l = database.get_map_records(map)

            embed.add_field(name="Record Time", value=jmutil.ticstime(rec['time']), inline=False)
            embed.add_field(name="Record Date", value=jmutil.format_date(rec['date']), inline=False)
            embed.add_field(name="Record Set By", value=jmutil.strip_colours(rec['author']), inline=False)

            for i in range(min(10, len(l))):    
                user, time = l[i]
                rank = database.get_entry_rank(map + '_pbs', user, False)

                embed.add_field(name=str(rank) + ". " + user, value=jmutil.ticstime(time), inline=True)

        elif maptype == "team":
            recs = database.get_team_map_record(map)

            embed.add_field(name="Record Time", value=jmutil.ticstime(recs['time']), inline=False)
            embed.add_field(name="Record Date", value=jmutil.format_date(recs['date']), inline=False)

            for player, points in recs['helpers'].items():
                plural = "s"
                if points == 1:
                    plural = ""

                embed.add_field(name=jmutil.strip_colours(player), value=str(points) + " point" + plural, inline=True)

        else:
            await ctx.send("Error - No map named %s exists, or it has no set records." % (map,))
            return
            
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