import threading
import discord
import jmutil
import config
import time
import db
import asyncio
import urllib.parse

import webdb

records = {}

def build_records(database):
    ret = {}
    maps = database.get_map_names()

    for map in maps:
        maptype = database.get_map_type(map)

        if maptype == "solo":
            ret[map] = database.get_solo_map_record(map)
        elif maptype == "team":
            ret[map] = database.get_team_map_record(map)
        elif maptype == "jmrun":
            ret[map] = database.get_jmrun_map_record(map)
        else:
            continue

        ret[map]['type'] = maptype

    return ret

async def perform_poll(client: discord.Client, database: db.Database, webdb: webdb.Database):
    global records

    newrecs = build_records(database)
    oldrecs = records[database]

    for map, data in newrecs.items():
        maptype = data['type']

        isWR = False
        if map in oldrecs:
            if data['time'] < oldrecs[map]['time']:
                isWR = True
        else:
            isWR = True

        if isWR:
            mapinfo = webdb.get_map_by_lump(map)

            url = config.SITE_URL + urllib.parse.quote("/maps/%s" % (map,))
            dbnamestr = "" if database.is_primary else f" on {database.display_name}"
            embed = discord.Embed(title="A new record for %s (%s) has been set%s!" % (map, mapinfo['name'], dbnamestr), colour=database.wr_colour, url=url)
            embed.set_thumbnail(url=config.IMAGES_URL + urllib.parse.quote("%s.png" % (map,)))
            embed.set_footer(text=f"Database: {database.display_name}")

            if maptype == "solo" or maptype == "jmrun":
                rec = database.get_solo_map_record(map) if maptype == "solo" else database.get_jmrun_map_record(map)
                l = database.get_map_records(map)

                embed.add_field(name="Record Time", value=jmutil.ticstime(rec['time']), inline=False)
                embed.add_field(name="Record Date", value=jmutil.format_date(rec['date']), inline=False)
                embed.add_field(name="Record Set By", value=jmutil.strip_colours(rec['author']), inline=False)
                
                if l is not None:
                    for i in range(min(3, len(l))):    
                        user, time = l[i]
                        rank = database.get_entry_rank(map + '_pbs', user, False)

                        embed.add_field(name=str(rank) + ". " + user, value=jmutil.ticstime(time), inline=True)
            elif maptype == "team":
                recs = data

                embed.add_field(name="Record Time", value=jmutil.ticstime(recs['time']), inline=False)
                embed.add_field(name="Record Date", value=jmutil.format_date(recs['date']), inline=False)

                for player, points in recs['helpers'].items():
                    plural = "s"
                    if points == 1:
                        plural = ""

                    embed.add_field(name=jmutil.strip_colours(player), value=str(points) + " point" + plural, inline=True)

                if map in oldrecs:
                    oldrec = oldrecs[map]

                    embed.add_field(name="Previous Record Time", value=jmutil.ticstime(oldrec['time']), inline=False)
                    embed.add_field(name="Previous Record Date", value=jmutil.format_date(oldrec['date']), inline=False)

                    helpers = ''
                    i = 0

                    for player, points in oldrec['helpers'].items():
                        helpers += "%s (%d)" % (jmutil.strip_colours(player), points)
                        if i < len(oldrec['helpers']) - 1:
                            helpers += ", "
                        i += 1

                    embed.add_field(name="Previous Record Helpers", value=helpers, inline=False)

            channel = client.get_channel(config.NOTIFY_CHANNEL)
            await channel.send(embed=embed)

    records[database] = newrecs

async def poll_thread_target(client: discord.Client, databases: list[db.Database], webdb: webdb.Database):
    global records

    await client.wait_until_ready()
    for database in databases:
        records[database] = build_records(database)

    while not client.is_closed():
        channel = client.get_channel(config.NOTIFY_CHANNEL)
        for database in databases:
            await perform_poll(client, database, webdb)
        await asyncio.sleep(config.WR_POLL_FREQ)