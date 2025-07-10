from math import log
import platform
from pydoc import plain
from typing import Any, List, Literal
from yt_dlp import YoutubeDL
from platform import system
from pata_logger import Logger
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


logger = Logger("bot_utils")


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
        logger.error(f"Could not obtain video information from: {video_url}")
        return ""

    with YoutubeDL(options) as ydl:
        ydl.download([video_info["webpage_url"]])

    logger.debug(f"Download complete... {filename}")

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
            logger.error("Could not obtain guild")
            return

        guild: Guild = ctx.guild
        guild_id: int = ctx.guild.id

        voice_client: VoiceClient | VoiceProtocol | None = get(
            bot.voice_clients, guild=guild
        )

        if not isinstance(voice_client, VoiceClient):
            logger.error("Could not obtain instance of VoiceClient")
            return

        audio_source: FFmpegPCMAudio | None = get_audio_source(audio_name)

        if audio_source is None:
            logger.error("Could not obtain audio source")
            return

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
                new_audio_source: FFmpegPCMAudio | None = get_audio_source(actual_audio_name)

                if new_audio_source is None:
                    logger.error("Could not obtain audio source")
                    return

                await reproduce_song(ctx, actual_audio_name, bot, play_list)
            else:
                play_list.reset_play_list(guild_id)
                await voice_client.disconnect()
        else:
            play_list.add_to_playlist(guild_id, audio_name)
            await ctx.send("Added to playlist:  " + audio_name)

    except Exception as e:
        logger.error(e)


def get_audio_source(audio_name: str) -> FFmpegPCMAudio | None:
    if not exists("./songs/" + audio_name):
        logger.error(f"Could not find {audio_name}")
        return None
    
    is_windows: bool = platform.system() == "Windows"
    ffmpeg: str = "./ffmpeg/bin/ffmpeg.exe" if is_windows else "ffmpeg"

    if is_windows and not exists("./ffmpeg/bin/"):
        logger.error(f"Could not find ffmpeg")
        return None

    return FFmpegPCMAudio(executable=ffmpeg, source="./songs/" + audio_name)

async def connect_to_voice_channel(ctx: Context, bot: Bot) -> bool:
    if ctx.guild is None:
        logger.error("Could not obtain guild")
        return False

    if not isinstance(ctx.author, Member):
        logger.error("Author is not a Member")
        return False

    author: Member = ctx.author

    if not isinstance(author.voice, VoiceState):
        logger.error("Could not obtain voice")
        return False
    
    connected: VoiceState | None = ctx.author.voice

    if not isinstance(connected, VoiceState):
        logger.error("Could not obtain a valid VoiceState")    
        return False

    if connected:
        if connected.channel is None:
            logger.error("Could not obtain channel")
            return False

        voice_client: VoiceClient = await connected.channel.connect()

        if not voice_client.is_connected:
            logger.error("Could not connectto channel")
            return False

        logger.debug(f"Connected to channel {voice_client.channel.id}")
        return True
    else:
        return False