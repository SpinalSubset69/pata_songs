from asyncio import Event
from typing import List, Literal
from discord import Optional
from discord.ext.commands import Bot, Context
from mafic import Node, NodePool, Player, Playlist
from mafic.track import Track
from audio_backend import AudioBackend
from audio_track import AudioTrack
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

    async def __init__(self, node_settings: NodeSettings) -> None:
        super().__init__()
        self.is_ready = False
        self.node_pool = NodePool(self)  # type: ignore

        on_ready_event = Event()

        async def after_ready_async(self, node_settings: NodeSettings):
            if self.is_ready:
                return

            await self.node_pool.create_node(
                host=node_settings.host,
                port=node_settings.port,
                label=node_settings.label,
                password=node_settings.password,
            )

            self.is_ready = True

            on_ready_event.set()

        await after_ready_async(self, node_settings)

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

        guild_id: int = ctx.guild.id

        playlist.add_to_playlist(guild_id, audio_item)

        player: Player = self.current_node.get_player(
            guild_id
        ) or await self.current_node.add_player(guild_id)

        if ctx.author.voice and ctx.author.voice.channel:
            await player.connect(ctx.author.voice.channel.id)

        # If nothing is playing, start playing the next track
        if not player.is_playing():
            await self.play_next(ctx, bot, playlist)
        else:
            await ctx.send(f"Added to playlist: **{track.title}**")

    async def play_next(self, ctx: Context, bot: Bot, playlist: PlayList) -> None:
        return await super().play_next(ctx, bot, playlist)
