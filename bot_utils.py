import os.path
import asyncio
import discord
import yt_dlp 
from discord.ext import commands
from youtube_search import YoutubeSearch

def download_youtube_song(videoUrl, song_title):        
    filename = f"{song_title}.mp3"  
    
    # Check if song is not already in folder
    if os.path.exists('./songs/' + filename):
        return filename

    video_url = 'https://www.youtube.com' + videoUrl
    video_info = yt_dlp.YoutubeDL().extract_info(url = video_url,download=False)    
          
    options={
        'noplaylist': True,
        'format':'bestaudio/best',
        'keepvideo':False,
        'outtmpl':'./songs/' + filename
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([video_info['webpage_url']])
    print("Download complete... {}".format(filename))
    return filename

def get_command_args_split(args):
    first_split = args.split(' ') # To avoide extra args
    split_args = first_split[0].split('|')
    song_name = split_args[0]
    song_author=''

    if len(split_args) > 0:
        song_author = split_args[1]        

    if song_name is None and song_author == '':
        return ''

    youtube_query = song_name;

    if song_author != '':
        youtube_query += ' ' + song_author  

    return youtube_query  + ' music video, no playlists'

async def reproduce_song(ctx, audio_name, bot, play_list):
    try:
        guild_id = ctx.guild.id
        voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients)
        audio_source = get_audio_source(audio_name)                   
        if not voice_client.is_playing():
            voice_client.play(audio_source, after=None)
            await ctx.send('Reproducing ' + audio_name)              

            while voice_client.is_playing():
                await asyncio.sleep(1)
                                
            if play_list.get_playlist_lenght(guild_id) > 0 and play_list.get_current_playlist_index(guild_id) <= play_list.get_playlist_lenght(guild_id):
                actual_audio_name = play_list.get_next_song(guild_id)                
                new_audio_source = get_audio_source(actual_audio_name)
                voice_client.play(new_audio_source, after=None)
            else:
                play_list.reset_play_list(guild_id)
                await voice_client.disconnect()
        else:
            play_list.add_to_playlist(guild_id, audio_name)

    except Exception as e:
        print(e)           

def get_audio_source(audio_name):
     return discord.FFmpegPCMAudio(executable='./ffmpeg/bin/ffmpeg.exe', source='./songs/' + audio_name) 
                
async def connect_to_voice_channel(ctx):
    connected = ctx.author.voice            
    if connected:
        # connect bot to channel
        await connected.channel.connect()
        return True                        
    else:
        return False
