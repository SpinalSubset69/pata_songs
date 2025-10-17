from contextvars import Context
from typing import Any, Dict, Literal
from discord import (
    FFmpegPCMAudio,
    Member,
    Optional,
    PCMVolumeTransformer,
    StageChannel,
    VoiceChannel,
    VoiceClient,
    VoiceProtocol,
)
from audio_backend import AudioBackend
from audio_track import AudioTrack
from pata_logger import Logger
from playlist import PlayList
from discord.ext.commands import Bot, Context
from asyncio import Event
from yt_dlp import YoutubeDL

logger = Logger("youtube_dlp_backend")

HEADERS: dict[str, str] = {
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
    "http_headers": HEADERS,  # correct: Mapping[str, str]
    "sleep_interval_requests": 1,  # "sleep-requests" → renamed in TypedDict
    "sleep_interval": 60,  # "min-sleep-interval" maps to sleep_interval
    "max_sleep_interval": 90,
    "options": "-vn -loglevel error",
}


class YoutubeDlpBackend(AudioBackend):
    """Strategy that uses YouTube-DLP for playback."""

    async def search(self, query: str, results: int = 5) -> Optional[AudioTrack]:
        try:
            logger.debug(f"Searching for: {query}")

            result: Any = YoutubeDL(YOUTUBE_DLP_OPTIONS).extract_info(  # type: ignore due to youtube-dlp lacking full type stubs
                f'ytsearch{results}:"{query}"', download=False
            )

            logger.debug(f"Results obtained from query: {result}")

            if not result or "entries" not in result or not result["entries"]:
                logger.error(f"No search results found for query: {query}")
                return None

            entries: Any = result["entries"]
            if not isinstance(entries, list):
                return None

            for entry in entries:
                if entry and "/shorts/" not in entry["url"]:
                    logger.debug(f"Selected entry: {entry}")
                    return AudioTrack(
                        title=entry["title"],
                        url=AudioTrack.remove_list_query_param(entry["url"]),
                        duration=entry["duration"],
                        thumbnail=entry["thumbnails"][0]["url"],
                        author=entry["channel"],
                    )

            logger.warning("All top results were Shorts. No valid result found.")

            return None
        except Exception as exception:
            logger.error(f"Error trying to search: {exception}.")
            return None

    async def connect(self, ctx: Context) -> bool:
        """Contains Discord channel connection logic"""
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

    async def enqueue(
        self, ctx: Context, audio_item: AudioTrack, bot: Bot, playlist: PlayList
    ) -> None:
        if ctx.guild is None:
            logger.warning("Could not obtain Guild.")
            return

        guild_id: int = ctx.guild.id
        playlist.add_to_playlist(guild_id, audio_item)

        voice_client: VoiceProtocol | None = ctx.guild.voice_client
        if voice_client is None or not isinstance(voice_client, VoiceClient):
            logger.debug("Connecting to channel")
            await self.connect(ctx)

        if (
            voice_client is None
            or not isinstance(voice_client, VoiceClient)
            or not voice_client.is_playing()
        ):
            logger.debug("Nothing is currently playing, adding to queue.")
            await self.play_next(ctx, bot, playlist)
        else:
            logger.debug("Something is currently playing, adding to queue.")
            await ctx.send(f"Added to playlist: {audio_item.title}")

    async def play_next(self, ctx: Context, bot: Bot, playlist: PlayList) -> None:
        if ctx.guild is None:
            logger.error("Could not obtain guild")
            return

        guild_id: int = ctx.guild.id

        next_item: AudioTrack | None = playlist.get_next_song(guild_id)
        if not next_item:
            playlist.reset_play_list(guild_id)
            voice_client: VoiceClient | VoiceProtocol | None = ctx.guild.voice_client

            if voice_client is not None:
                logger.debug("Could not access voice_client, disconnecting.")
                await voice_client.disconnect(force=False)

            logger.debug("Playlist ended.")
            await ctx.send("Playlist ended.")
            return

        stream_url: str | None = self.get_youtube_stream_url(next_item.title)
        if stream_url is None:
            await ctx.send(f"Failed to get stream for {next_item.title}. Skipping.")
            await self.play_next(ctx, bot, playlist)
            return

        audio_source = self.create_audio_source_from_url(stream_url)
        if audio_source is None:
            await ctx.send(f"Could not create audio source for {next_item.title}.")
            await self.play_next(ctx, bot, playlist)
            return

        finished_event = Event()

        def after_playback(error):
            if error:
                logger.error(f"Playback error: {error}")

            finished_event.set()

        voice_client: VoiceClient | VoiceProtocol | None = ctx.guild.voice_client
        if voice_client is None:
            await self.connect(ctx)
            voice_client = ctx.guild.voice_client

        if voice_client is None:
            await ctx.send("Could not join voice channel to play.")
            return

        if not isinstance(voice_client, VoiceClient):
            logger.error("Could not obtain instance of VoiceClient")
            return

        voice_client.play(audio_source, after=after_playback)
        await ctx.send(f"Reproducing {next_item.title}")
        await finished_event.wait()

        await self.play_next(ctx, bot, playlist)

    def get_youtube_stream_url(self, video_url: str) -> Optional[str]:
        """Tries to obtain a stream url from a YouTube url"""
        logger.debug(f"Extracting streamable url from: {video_url}")

        with YoutubeDL(YOUTUBE_DLP_OPTIONS) as ydl:  # type: ignore due to youtube-dlp lacking full type stubs
            try:
                info_dict: Any = ydl.extract_info(video_url, download=False)

                if info_dict is None:
                    logger.error(f"Could not extract info from: {video_url}")
                    return None

                logger.debug(f"Info: {info_dict}")
                formats: list[dict[str, Any]] | None = info_dict.get("formats")
                logger.debug(f"formats: {formats}")

                if not isinstance(formats, list):
                    logger.error(f"Could not extract formats from: {video_url}")
                    return None

                logger.debug(
                    f"Evaluating formats for audio: found {len(formats)} formats"
                )

                audio_formats: list[dict[str, Any]] = [f for f in formats]

                if not audio_formats:
                    logger.error("No suitable audio-only format found.")
                    return None

                best_audio: dict[str, Any] = max(
                    audio_formats, key=lambda f: f.get("abr") or 0
                )
                logger.debug(
                    f"Selected best audio format: {best_audio.get('format_id')}"
                )
                logger.debug(f"Best audio URL: {best_audio['url']}")

                return best_audio["url"]

            except Exception as e:
                logger.error(f"Failed to get stream URL: {e}")
                return None

    def create_audio_source_from_url(
        self, stream_url: str
    ) -> Optional[PCMVolumeTransformer]:
        from platform import system

        is_windows: bool = system() == "Windows"

        ffmpeg_path: Literal["./ffmpeg/bin/ffmpeg.exe"] | Literal["ffmpeg"] = (
            "./ffmpeg/bin/ffmpeg.exe" if is_windows else "ffmpeg"
        )

        from os.path import exists

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
