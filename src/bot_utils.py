import platform
from typing import Any, List, Literal, Optional
from warnings import deprecated
from yt_dlp import YoutubeDL
from pata_logger import Logger
from playlist import PlayList
from os.path import exists
from discord.utils import get
from discord import (
    Guild,
    Member,
    PCMVolumeTransformer,
    VoiceClient,
    FFmpegPCMAudio,
    VoiceProtocol,
    VoiceState,
)
from discord.ext.commands import Bot, Context
from youtube_result import YoutubeResult


logger = Logger("bot_utils")


def search_youtube(search_query: str, results: int = 1) -> Optional[YoutubeResult]:
    """obtains list of results from YouTube with best settings"""
    try:
        options = {
            "quiet": True,
            "format": "bestaudio/best",
            "skip_download": True,
            "extract_flat": "in_playlist",
            "nocheckcertificate": True,
            "getcomments": False,
            "keepvideo": False,
            "break_on_existing": True,
        }

        logger.debug(f"Searching for: {search_query}")

        result = YoutubeDL(options).extract_info(
            f'ytsearch{results}:"{search_query}"', download=False
        )

        logger.debug(f"Results obtained from query: {result}")

        if result is None or "entries" not in result or not result["entries"]:
            logger.error(f"No search results found for query: {search_query}")
            return None

        # TODO: depending on the results count, update this logic
        entry = result["entries"][0]

        if entry is None:
            logger.error(f"Found video, but couldn't parse any results.")
            return None

        logger.debug(f"Obtained the following entry: {entry}")

        # TODO: add validation for these properties
        return YoutubeResult(title=entry["title"], url_suffix=entry["url"])
    except Exception as exception:
        logger.error(f"Error trying to search: {exception}.")
        return None


def get_youtube_stream_url(video_url: str) -> Optional[str]:
    """Tries to obtain a stream url from a YouTube url"""
    options = {
        "quiet": True,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
    }

    logger.debug(f"Extracting streamable url from: {video_url}")

    with YoutubeDL(options) as ydl:
        try:
            info_dict = ydl.extract_info(video_url, download=False)

            if info_dict is None:
                logger.error(f"Could not extract streamable url from: {video_url}")
                return

            logger.debug(f"Obtained the following response: {info_dict}")

            return info_dict["url"]

        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            return None


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
            stream_url = get_youtube_stream_url(video_url)

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

            voice_client.play(audio_source, after=None)
            await ctx.send("Reproducing " + video_url)

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
        FFmpegPCMAudio(stream_url, executable=ffmpeg_path, options="-vn"), volume=1.0
    )


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
            logger.error("Could not connect to channel")
            return False

        logger.debug(f"Connected to channel {voice_client.channel.id}")
        return True
    else:
        return False
