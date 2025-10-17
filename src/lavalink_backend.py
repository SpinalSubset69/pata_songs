from typing import List, Literal, Self
from discord import (
    Member,
    Optional,
    StageChannel,
    VoiceChannel,
    VoiceClient,
    VoiceState,
)
from discord.ext.commands import Bot, Context
from mafic import Node, NodePool, Player, Playlist
from mafic.track import Track
from audio_backend import AudioBackend
from audio_track import AudioTrack
from lavalink_node_settings import NodeSettings
from pata_logger import Logger
from playlist import PlayList


LavalinkSearchPlatform = Literal[
    "ytsearch",
    "ytmsearch",
    "scsearch",
    "spsearch",
    "sprec",
    "amsearch",
    "dzsearch",
    "dzisrc",
    "ymsearch",
    "speak",
    "tts",
    "ftts",
]


logger = Logger("lavalink_backend")


class LavalinkBackend(AudioBackend):
    """Strategy that uses Lavalink for playback."""

    node_pool: NodePool
    is_ready: bool = False

    def __init__(self, bot: Bot, node_settings: NodeSettings) -> None:
        super().__init__()
        self.is_ready = False
        self.bot: Bot = bot
        self.node_settings: NodeSettings = node_settings
        self.node_pool = NodePool(bot)

    @classmethod
    async def create(cls, bot: Bot, node_settings: NodeSettings) -> "LavalinkBackend":
        """Async factory for LavalinkBackend (replaces async __init__)."""
        self: Self = cls(bot, node_settings)

        await self.node_pool.create_node(
            host=node_settings.host,
            port=node_settings.port,
            label=node_settings.label,
            password=node_settings.password,
        )

        self.is_ready = True
        logger.info("Lavalink node is ready.")
        return self

    @property
    def current_node(self) -> Node:
        """Gets a random node from the pool"""
        # Currently we're only supporting one node, but if more are
        # added then this method should be updated
        return self.node_pool.get_random_node()

    async def search(
        self,
        query: str,
        results: int = 5,
        search_type: LavalinkSearchPlatform = "ytsearch",
    ) -> Optional[AudioTrack]:
        search_res: List[Track] | Playlist | None = (
            await self.current_node.fetch_tracks(query, search_type=search_type)
        )

        if not search_res:
            logger.warning(
                "No response obtained after searching %s in platform %s.",
                query,
                search_type,
            )

            return None

        tracks: List[Track] = []
        if isinstance(search_res, Playlist):
            logger.debug("Obtained a list of tracks from Playlist %s.", search_res.name)
            tracks = search_res.tracks
        else:
            tracks = search_res

        if len(tracks) == 0:
            logger.warning(
                "Obtained a response but no results came up after searching %s in platform %s.",
                query,
                search_type,
            )

            return None

        logger.debug(
            "Obtained a list of %s tracks, using the first instance.", len(tracks)
        )

        track: Track = tracks[0]

        logger.debug("Selected track %s.", track.title)

        return AudioTrack(
            title=track.title,
            url=AudioTrack.remove_list_query_param(track.uri or "Unknown"),
            duration=track.length / 1000.0 or 0,
            thumbnail=track.artwork_url or "Unknown",
            author=track.author or "Unknown",
        )

    async def connect(self, ctx: Context) -> bool:
        # For Lavalink, the “connect” is done by the Player, so this may be a no-op,
        # assuming ctx.author is in a voice channel.
        return True

    async def enqueue(
        self, ctx: Context, audio_item: AudioTrack, bot: Bot, playlist: PlayList
    ) -> None:
        if ctx.guild is None:
            logger.error("Could not obtain guild")
            return

        if not isinstance(ctx.author, Member):
            raise RuntimeError("Author is not a guild member.")

        voice_state: VoiceState | None = ctx.author.voice
        if voice_state is None or voice_state.channel is None:
            raise RuntimeError("You must be connected to a voice channel first.")

        guild_id: int = ctx.guild.id
        playlist.add_to_playlist(guild_id, audio_item)

        player: Player | None = self.current_node.get_player(guild_id)

        if not player:
            voice: VoiceChannel | StageChannel = voice_state.channel
            player = await voice.connect(cls=Player)

        if (
            player is None
            or not isinstance(player, VoiceClient)
            or not player.is_playing()
        ):
            logger.debug("Nothing is currently playing, adding to queue.")
            await self.play_next(ctx, bot, playlist)
        else:
            logger.debug("Something is currently playing, adding to queue.")
            await ctx.send(f"Added to playlist: {audio_item.title}.")

    async def play_next(self, ctx: Context, bot: Bot, playlist: PlayList) -> None:
        if ctx.guild is None:
            logger.error("Could not obtain guild")
            return

        if not isinstance(ctx.author, Member):
            raise RuntimeError("Author is not a guild member.")

        voice_state: VoiceState | None = ctx.author.voice
        if voice_state is None or voice_state.channel is None:
            raise RuntimeError("You must be connected to a voice channel first.")

        guild_id: int = ctx.guild.id

        player: Player | None = self.current_node.get_player(guild_id)

        if not player:
            voice: VoiceChannel | StageChannel = voice_state.channel
            player = await voice.connect(cls=Player)

        if player is None or not isinstance(player, VoiceClient):
            raise RuntimeError("Player is not of voice client instance.")

        next_track: AudioTrack | None = playlist.get_next_song(guild_id)
        if next_track is None:
            playlist.reset_play_list(guild_id)
            player = self.current_node.get_player(guild_id)

            if player:
                await player.disconnect()

            await ctx.send("Playlist ended.")
            return

        await player.play(next_track.url)
        await ctx.send(f"Reproducing {next_track.title}.")
