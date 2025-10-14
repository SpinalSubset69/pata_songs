from abc import ABC, abstractmethod
from typing import Optional
from discord.ext.commands import Context
from discord.ext.commands import Bot
from audio_track import AudioTrack
from playlist import PlayList


class AudioBackend(ABC):
    """
    Backend must manage connecting + play lifecycle, but the PlayList object
    is shared and the backend must call play_next when a track finishes.
    """

    @abstractmethod
    async def search(self, query: str, results: int = 5) -> Optional[AudioTrack]:
        """Return an audio item dict {'title':..., 'url':...} or None."""

    @abstractmethod
    async def connect(self, ctx: Context) -> bool:
        """Ensure bot is connected to the user's voice channel."""

    @abstractmethod
    async def enqueue(
        self, ctx: Context, audio_item: AudioTrack, bot: Bot, playlist: PlayList
    ) -> None:
        """
        Add item to queue and start playback if nothing is playing.
        Implementations should call play_next(ctx, bot, playlist) to start.
        """

    @abstractmethod
    async def play_next(self, ctx: Context, bot: Bot, playlist: PlayList) -> None:
        """Play next track from playlist for ctx.guild."""
