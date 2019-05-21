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

@client.command()
async def map(ctx, map):
    map = map.upper()
    maptype = database.get_map_type(map)

    embed = discord.Embed(title="Records for " + map, colour=discord.Colour.blue())

    if maptype == "solo":
        rec = database.get_solo_map_record(map)
        l = database.get_map_records(map)

        embed.add_field(name="Record Time", value=jmutil.ticstime(rec['time']), inline=False)
        embed.add_field(name="Record Date", value=jmutil.format_date(rec['date']), inline=False)
        embed.add_field(name="Record Set By", value=jmutil.strip_colours(rec['author']), inline=False)

        for i in range(min(25, len(l))):    
            user, time = l[i]

            embed.add_field(name=str(i + 1) + ". " + user, value=jmutil.ticstime(time), inline=True)

    elif maptype == "team":
        recs = database.get_team_map_record(map)

        embed.add_field(name="Record Time", value=jmutil.ticstime(recs['time']), inline=False)
        embed.add_field(name="Record Date", value=jmutil.format_date(recs['date']), inline=False)

        for player, points in recs['helpers'].items():
            embed.add_field(name=jmutil.strip_colours(player), value=str(points) + " points", inline=True)

    else:
        await ctx.send("Error - No map named %s exists, or it has no set records." % (map,))
        
    await ctx.send(embed=embed)

@client.command()
async def exit(ctx):
    print(ctx.author.id)
    if ctx.author.id in config.ADMINS:
        await client.close()
        sys.exit()
    else:
        await ctx.send("No")

client.loop.create_task(wrcheck.poll_thread_target(client, database))
client.run(config.BOT_TOKEN)