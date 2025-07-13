from asyncio import Event
import platform
from typing import Any, Optional
from warnings import deprecated
from pytubefix.streams import Stream
from yt_dlp import YoutubeDL
from pata_logger import Logger
from playlist import PlayList
from os.path import exists
from discord.utils import get
from discord import (
    Guild,
    Member,
    PCMVolumeTransformer,
    StageChannel,
    VoiceChannel,
    VoiceClient,
    FFmpegPCMAudio,
    VoiceProtocol,
)
from discord.ext.commands import Bot, Context
from youtube_result import YoutubeResult
from pytubefix import YouTube
from pytubefix.cli import on_progress


logger = Logger("bot_utils")

custom_headers: dict[str, str] = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"
}

YOUTUBE_DLP_OPTIONS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "extract_flat": "in_playlist",  # We need this for speed
    "match_filter": "original_url !*= /shorts/",  # This is for removing shorts, but it seems to be broken
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",  # Bind the client request to random IP
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "logtostderr": True,
    "no_warnings": True,
    "break_on_existing": True,
    "skip_download": True,
    "quiet": True,
    "getcomments": False,
    "keepvideo": False,
    "http_headers": custom_headers,
}


def search_youtube(search_query: str, results: int = 5) -> Optional[YoutubeResult]:
    """obtains list of results from YouTube with best settings"""
    try:
        logger.debug(f"Searching for: {search_query}")

        result = YoutubeDL(YOUTUBE_DLP_OPTIONS).extract_info(
            f'ytsearch{results}:"{search_query}"', download=False
        )

        logger.debug(f"Results obtained from query: {result}")

        if not result or "entries" not in result or not result["entries"]:
            logger.error(f"No search results found for query: {search_query}")
            return None

        for entry in result["entries"]:
            if entry and "/shorts/" not in entry["url"]:
                logger.debug(f"Selected entry: {entry}")
                return YoutubeResult(title=entry["title"], url_suffix=entry["url"])

        logger.warning("All top results were Shorts. No valid result found.")
        return None
    except Exception as exception:
        logger.error(f"Error trying to search: {exception}.")
        return None


def get_youtube_stream_url(video_url: str) -> Optional[str]:
    """Tries to obtain a stream url from a YouTube url"""
    logger.debug(f"Extracting streamable url from: {video_url}")

    yt = YouTube(video_url, on_progress_callback=on_progress, client='WEB')

    yt_st: Stream | None = yt.streams.get_audio_only()

    if not isinstance(yt_st, Stream):                
        raise AttributeError("Unable to get video url stream")

    return yt_st.url     


@deprecated(f"Please use get_youtube_stream_url to convert to audio_source")
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


async def reproduce_song(
    ctx: Context, video_url: str, bot: Bot, play_list: PlayList
) -> None:
    try:
        if video_url is None:
            logger.error("Could not obtain audio source")
            await ctx.send(f"Could not obtain audio source.")
            return

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

        if not voice_client.is_playing():

            stream_url: str | None = get_youtube_stream_url(video_url)

            if stream_url is None:
                logger.error("Failed to retrieve stream URL.")
                await ctx.send("Failed to retrieve stream URL.")
                return

            logger.debug(f"Converting url {stream_url} to audio source")

            audio_source = create_audio_source_from_url(stream_url)

            if audio_source is None:
                logger.error("Could not obtain audio source")
                await ctx.send("Could not obtain audio source")
                return

            finished_event: Event = Event()

            def after_playback(error: Exception | None):
                if error:
                    logger.error(f"Playback error: {error}")

                finished_event.set()

            voice_client.play(audio_source, after=after_playback)
            await ctx.send("Reproducing " + video_url)
            await finished_event.wait()

            if play_list.get_playlist_lenght(
                guild_id
            ) > 0 and play_list.get_current_playlist_index(
                guild_id
            ) <= play_list.get_playlist_lenght(
                guild_id
            ):
                actual_audio_name: Any = play_list.get_next_song(guild_id)

                if actual_audio_name is None:
                    logger.error("Could not obtain audio source")
                    return

                await reproduce_song(ctx, actual_audio_name, bot, play_list)
            else:
                play_list.reset_play_list(guild_id)
                await voice_client.disconnect()
        else:
            play_list.add_to_playlist(guild_id, video_url)
            await ctx.send("Added to playlist:  " + video_url)

    except Exception as e:
        logger.error(e)


@deprecated("Please use create_audio_source_from_url instead")
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


def create_audio_source_from_url(stream_url: str) -> Optional[PCMVolumeTransformer]:
    is_windows: bool = platform.system() == "Windows"
    ffmpeg_path = "./ffmpeg/bin/ffmpeg.exe" if is_windows else "ffmpeg"

    if is_windows and not exists("./ffmpeg/bin/"):
        logger.error(f"Could not find ffmpeg")
        return

    return PCMVolumeTransformer(
        FFmpegPCMAudio(
            stream_url,
            executable=ffmpeg_path,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn",
        ),
        volume=1.0,
    )


async def connect_to_voice_channel(ctx: Context) -> bool:
    if ctx.guild is None:
        logger.error("Could not obtain guild")
        return False

    if not isinstance(ctx.author, Member):
        logger.error("Author is not a Member")
        return False

    author: Member = ctx.author

    if author.voice is None or author.voice.channel is None:
        logger.error("Author is not in a voice channel")
        return False

    voice_channel: VoiceChannel | StageChannel = author.voice.channel

    voice_client: VoiceClient | VoiceProtocol | None = ctx.guild.voice_client

    if (
        voice_client is not None
        and isinstance(voice_client, VoiceClient)
        and voice_client.is_connected()
    ):
        logger.debug(f"Bot already connected to channel {voice_client.channel.id}")

        if voice_client.channel != voice_channel:
            logger.info("Bot is connected to a different channel. Moving...")
            await voice_client.move_to(voice_channel)

        return True

    try:
        voice_client = await voice_channel.connect()
        logger.debug(f"Connected to channel {voice_client.channel.id}")

        return True
    except Exception as e:
        logger.error(f"Failed to connect to voice channel: {e}")        
        return False
