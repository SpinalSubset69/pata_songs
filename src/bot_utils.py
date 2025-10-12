from asyncio import Event
import platform
from typing import Any, Dict, Literal, Optional
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


logger = Logger("bot_utils")

custom_headers: dict[str, str] = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

YOUTUBE_DLP_OPTIONS: Dict[str, Any] = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "extract_flat": "in_playlist",  # TypedDict allows this literal
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "nocheckcertificate": True,
    "ignoreerrors": True,  # correct: bool | "only_download"
    "logtostderr": True,
    "no_warnings": True,
    "break_on_existing": None,  # must be str | None → use None instead of True
    "skip_download": None,  # must be str | None → None means “True”
    "quiet": True,
    "getcomments": False,
    "keepvideo": None,  # must be str | None → None means False
    "http_headers": custom_headers,  # correct: Mapping[str, str]
    "sleep_interval_requests": 1,  # "sleep-requests" → renamed in TypedDict
    "sleep_interval": 60,  # "min-sleep-interval" maps to sleep_interval
    "max_sleep_interval": 90,
}


def search_youtube(search_query: str, results: int = 5) -> Optional[YoutubeResult]:
    """obtains list of results from YouTube with best settings"""
    try:
        logger.debug(f"Searching for: {search_query}")

        result: Any = YoutubeDL(YOUTUBE_DLP_OPTIONS).extract_info(  # type: ignore due to youtube-dlp lacking full type stubs
            f'ytsearch{results}:"{search_query}"', download=False
        )

        logger.debug(f"Results obtained from query: {result}")

        if not result or "entries" not in result or not result["entries"]:
            logger.error(f"No search results found for query: {search_query}")
            return None

        entries: Any = result["entries"]
        if not isinstance(entries, list):
            return None

        for entry in entries:
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

    with YoutubeDL(YOUTUBE_DLP_OPTIONS) as ydl:  # type: ignore due to youtube-dlp lacking full type stubs
        try:
            info_dict: Any = ydl.extract_info(video_url, download=False)

            if info_dict is None:
                logger.error(f"Could not extract info from: {video_url}")
                return None

            formats: list[dict[str, Any]] | None = info_dict.get("formats")
            logger.debug(f"formats: {formats}")

            if not isinstance(formats, list):
                logger.error(f"Could not extract formats from: {video_url}")
                return None

            logger.debug(f"Evaluating formats for audio: found {len(formats)} formats")

            audio_formats: list[dict[str, Any]] = [f for f in formats]

            if not audio_formats:
                logger.error("No suitable audio-only format found.")
                return None

            best_audio: dict[str, Any] = max(
                audio_formats, key=lambda f: f.get("abr") or 0
            )
            logger.debug(f"Selected best audio format: {best_audio.get('format_id')}")
            logger.debug(f"Best audio URL: {best_audio['url']}")

            return best_audio["url"]

        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            return None


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


def create_audio_source_from_url(stream_url: str) -> Optional[PCMVolumeTransformer]:
    is_windows: bool = platform.system() == "Windows"
    ffmpeg_path: Literal["./ffmpeg/bin/ffmpeg.exe"] | Literal["ffmpeg"] = (
        "./ffmpeg/bin/ffmpeg.exe" if is_windows else "ffmpeg"
    )

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
