import discord
from youtube_result import YoutubeResult 
from playlist import PlayList
from bot_utils import connect_to_voice_channel
from bot_utils import reproduce_song
from bot_utils import get_command_args_split
from bot_utils import download_youtube_song
from discord.ext import commands
from youtube_search import YoutubeSearch
from dotenv import load_dotenv
import os

load_dotenv()

# Initalize variables
BOT_TOKEN= os.getenv('BOT_TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
play_list = PlayList()

@bot.command()
async def reproduce_playlist(ctx):
    guild_id = ctx.guild.id
    if play_list.get_playlist_lenght(guild_id) == 0:
        ctx.send('No songs in playlist, please add at least one')
        return
            
    audio_name = play_list.get_next_song(guild_id)

    if audio_name == '':
        await ctx.send('Play list end')
        play_list.reset_play_list(guild_id);
        return
    
    connected_to_channel = await connect_to_voice_channel(ctx) 
    if connected_to_channel:
        # connect bot to channel                
        await ctx.send('Bot connected to channel!')
                
        # Reproduce Music
        await reproduce_song(ctx=ctx, audio_name=audio_name, bot=bot, play_list=play_list)                                            
    else:
        await ctx.send('User is not in a channel, failed to join...')

@bot.command()
async def add_playlist(ctx, args: str = commands.parameter(default='', description='Song to query')):
    youtube_query = get_command_args_split(args);                                     
    
    if youtube_query == '':
        await ctx.send('Please provided at least 1 argument')
        return
    
    results = YoutubeSearch(youtube_query, max_results=5).to_dict()

    if len(results) > 1: 
        guild_id = ctx.guild.id
        result = YoutubeResult(list(results)[0])         
        audio_name = download_youtube_song(result.url_suffix, result.title)        
        play_list.add_to_playlist(guild_id, audio_name)
        await ctx.send('Song ' + audio_name + ' added to playlist!!')

@bot.command()
async def play(ctx, args: str = commands.parameter(default='', description='Song to query')):
    try:                
        youtube_query = get_command_args_split(args);                                 
    
        if youtube_query == '':
            await ctx.send('Please provided at least 1 argument')
            return

        results = YoutubeSearch(youtube_query, max_results=5).to_dict()
        
        if len(results) > 1:            
            result = YoutubeResult(list(results)[0])            

            message  = 'Matched result for query: ' + result.title + ' downloading song...'
            await ctx.send(message)                                    
                        
            audio_name = download_youtube_song(result.url_suffix, result.title)            

            connected_to_channel = await connect_to_voice_channel(ctx, bot)    

            if connected_to_channel:                                
                # Reproduce Music
                await reproduce_song(ctx=ctx, audio_name=audio_name, bot=bot, play_list=play_list)                                            
            else:
                await ctx.send('User is not in a channel, failed to join...')
    except AttributeError:
        print('Error')    

bot.run(BOT_TOKEN)
