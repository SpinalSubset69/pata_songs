from typing import Any, List, Literal
from yt_dlp import YoutubeDL
from playlist import PlayList
from os.path import exists
from discord.utils import get
from discord import (
    Guild,
    Member,
    VoiceClient,
    FFmpegPCMAudio,
    VoiceProtocol,
    VoiceState,
)
from asyncio import sleep
from discord.ext.commands import Bot, Context


def download_youtube_song(videoUrl: str, song_title: str) -> str:
    filename: str = f"{song_title}.mp3"

    # Check if song is not already in folder
    if exists("./songs/" + filename):
        return filename

    video_url: str = "https://www.youtube.com" + videoUrl
    video_info = YoutubeDL().extract_info(url=video_url, download=False)

    options = {
        "noplaylist": True,
        "format": "bestaudio/best",
        "keepvideo": False,
        "outtmpl": "./songs/" + filename,
    }

    if video_info is None:
        raise RuntimeError(f"Could not obtain video information from: {video_url}")

    with YoutubeDL(options) as ydl:
        ydl.download([video_info["webpage_url"]])

    print("Download complete... {}".format(filename))

    return filename


def get_command_args_split(args) -> str:
    first_split: Any = args.split(" ")  # To avoide extra args

    split_args: List[Any] = []
    song_name: Literal[""] = ""

    if "|" in first_split[0]:
        split_args = first_split[0].split("|")
        song_name = split_args[0]
    else:
        song_name = first_split[0]

    song_author: Literal[""] = ""

    if len(split_args) > 0:
        song_author = split_args[1]

    if song_name is None and song_author == "":
        return ""

    youtube_query: Any | Literal[""] = song_name

    if song_author != "":
        youtube_query += " " + song_author

    return youtube_query + " music video, no playlists"


async def reproduce_song(
    ctx: Context, audio_name: str, bot: Bot, play_list: PlayList
) -> None:
    try:
        if ctx.guild is None:
            raise RuntimeError("Could not obtain guild")

        guild: Guild = ctx.guild
        guild_id: int = ctx.guild.id

        voice_client: VoiceClient | VoiceProtocol | None = get(
            bot.voice_clients, guild=guild
        )

        if not isinstance(voice_client, VoiceClient):
            raise RuntimeError("Could not obtain instance of VoiceClient")

        audio_source: FFmpegPCMAudio = get_audio_source(audio_name)

        if not voice_client.is_playing():
            voice_client.play(audio_source, after=None)
            await ctx.send("Reproducing " + audio_name)

            # TODO: Why are we checking if it's playing after already checking that it's not?
            while voice_client.is_playing():
                await sleep(1)

            if play_list.get_playlist_lenght(
                guild_id
            ) > 0 and play_list.get_current_playlist_index(
                guild_id
            ) <= play_list.get_playlist_lenght(
                guild_id
            ):
                # TODO: Check why we pass new_audio_source but the method reproduce_song accepts only name so it's not needed
                actual_audio_name: Any = play_list.get_next_song(guild_id)
                new_audio_source: FFmpegPCMAudio = get_audio_source(actual_audio_name)

                await reproduce_song(ctx, actual_audio_name, bot, play_list)
            else:
                play_list.reset_play_list(guild_id)
                await voice_client.disconnect()
        else:
            play_list.add_to_playlist(guild_id, audio_name)
            await ctx.send("Added to playlist:  " + audio_name)

    except Exception as e:
        print(e)


def get_audio_source(audio_name: str) -> FFmpegPCMAudio:
    if exists("./songs/" + audio_name) == False:
        raise FileNotFoundError(f"Could not find {audio_name}")

    if exists("./ffmpeg/bin/") == False:
        raise FileNotFoundError(f"Could not find ffmpeg")

    return FFmpegPCMAudio(
        executable="./ffmpeg/bin/ffmpeg.exe", source="./songs/" + audio_name
    )


async def connect_to_voice_channel(ctx: Context, bot: Bot) -> bool:
    if ctx.guild is None:
        raise RuntimeError("Could not obtain guild")

    if not isinstance(ctx.author, Member):
        raise RuntimeError("Author is not a Member")

    author: Member = ctx.author

    if not isinstance(author.voice, VoiceState):
        raise RuntimeError("Could not obtain voice")
    
    connected: VoiceState | None = ctx.author.voice

    if not isinstance(connected, VoiceState):
        raise RuntimeError("Could not obtain a valid VoiceState")    

    if connected:
        if connected.channel is None:
            raise RuntimeError("Could not obtain channel")            
        await connected.channel.connect()
        return True
    else:
        return False

def get_guild_from_context(ctx: Context) -> Guild:
    if ctx.guild is None:
        raise RuntimeError("Could not obtain guild")
    return ctx.guild