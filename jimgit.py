import discord
import config
from discord.ext import commands
from github import Github

TRIM_LENGTH = 64

ghinst = None

def get_github():
    global ghinst
    
    if ghinst is None:
        ghinst = Github(config.GITHUB_ACCESS_KEY)
        
    return ghinst

class JimGit(commands.Cog):
    @commands.command(help="Posts a GitHub issue", usage="<text>")
    async def postissue(self, ctx, text):
        if len(text.split()) < 2:
            await ctx.send('It appears you are trying to post a single word (or nothing at all). Either you need to be more detailed, or need quotes.')
            
            return
            
        gh = get_github()
        
        repo = gh.get_repo(config.GITHUB_REPO)
        
        author = ctx.message.author
        username = '%s#%s' % (author.name, author.discriminator)
        
        title = 'Discord report by %s: %s' % (username, text[:TRIM_LENGTH])
        
        body = ''
        body += '[__%s posted in %s #%s:__](%s)\n\n' % (username, ctx.guild.name, ctx.channel.name, ctx.message.jump_url)
        
        lines = text.split('\n')
        for line in lines:
            body += '> ' + line + '\n'
        
        repo.create_issue(title=title, body=body)