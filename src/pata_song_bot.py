from typing import Any, Dict, Literal
from audio_backend import AudioBackend
from audio_track import AudioTrack
from lavalink_backend import LavalinkBackend
from lavalink_node_settings import NodeSettings
from youtube_dlp_backend import YoutubeDlpBackend
from playlist import PlayList
from discord.ext import commands
from discord.ext.commands import Bot, Context
from dotenv import load_dotenv
from discord.utils import get
from discord import Color, Embed, Guild, Intents, VoiceProtocol, VoiceClient
from os import getenv
from pata_logger import Logger
from embed_builder import EmbedBuilder

load_dotenv()

AUDIO_BACKEND_SOURCE: str = getenv("AUDIO_BACKEND_SOURCE", "Raw")

BOT_TOKEN: str | None = getenv("BOT_TOKEN")

if BOT_TOKEN is None:
    raise RuntimeError("Could not obtain token from environment settings.")

intents: Intents = Intents.all()

BOT_COMMAND_PREFIX: str | None = getenv("BOT_COMMAND_PREFIX")

if BOT_COMMAND_PREFIX is None:
    raise RuntimeError("Could not obtain bot command prefix from environment settings")

bot = Bot(command_prefix=BOT_COMMAND_PREFIX, intents=intents)
play_list = PlayList()
logger = Logger("pata_song_bot")

backend: AudioBackend

if AUDIO_BACKEND_SOURCE == "youtube-dlp":
    backend = YoutubeDlpBackend()
elif AUDIO_BACKEND_SOURCE == "lavalink":
    node_settings = NodeSettings(
        getenv("LAVALINK_NODE_HOST", "localhost"),
        int(getenv("LAVALINK_NODE_PORT", "2333")),
        getenv("LAVALINK_NODE_LABEL", "Default"),
        getenv("LAVALINK_NODE_PASSWORD", "password"),
    )

    backend = LavalinkBackend(node_settings)
else:
    raise ValueError(f"Unsupported audio backend source: {AUDIO_BACKEND_SOURCE}.")


@bot.command()
async def reproduce_playlist(ctx: Context):
    if ctx.guild is None:
        logger.error("Could not obtain guild")
        return

    guild_id: int = ctx.guild.id

    if play_list.get_playlist_length(guild_id) == 0:
        await ctx.send("No songs in playlist, please add at least one")
        return

    audio_name: Any | Literal[""] = play_list.get_next_song(guild_id)

    if audio_name == "":
        await ctx.send("Play list end")
        play_list.reset_play_list(guild_id)
        return

    connected_to_channel: bool = await backend.connect(ctx)
    if connected_to_channel:
        await ctx.send("Bot connected to channel!")
        await backend.play_next(ctx, bot, play_list)
    else:
        await ctx.send("User is not in a channel, failed to join...")


@bot.command()
async def add_playlist(
    ctx: Context,
    *,
    args: str = commands.parameter(default="", description="Song to query"),
):
    """
    Adds a song to the server's playlist by searching YouTube using the provided query.

    Parameters
    ----------
    ctx : Context
        The context in which the command was invoked, including metadata such as the channel and guild.
    args : str, keyword-only
        The search query for the song to add. Declared after a `*` to make it keyword-only.
        This allows the entire remaining message (including spaces) to be captured as a single string.

    Behavior
    --------
    - Validates that a query was provided.
    - Searches YouTube using the query.
    - If a result is found, extracts the video URL suffix.
    - Adds the song to the playlist associated with the current server (`guild.id`).
    - Sends a confirmation message to the Discord text channel.

    Notes
    -----
    The use of `*` in the function signature is used to support multi-word queries.
    Without it, Discord.py would split the message by spaces and treat each word as a separate argument.

    Example
    -------
    User input: !add_playlist never going to give you up

    The full string "never going to give you up" will be passed as the `args` parameter and used to
    search YouTube. The resulting video will be added to the server's playlist.
    """
    youtube_query: str = args

    if youtube_query == "":
        await ctx.send("Please provided at least 1 argument")
        return

    youtube_search_result: AudioTrack | None = await backend.search(youtube_query)

    if youtube_search_result is None:
        logger.error(f"No video result obtained, returning.")
        await ctx.send(f"Could not find anything related to: {youtube_query}")
        return

    if ctx.guild is None:
        logger.error(f"Could not obtain guild")
        return

    guild_id: int = ctx.guild.id

    play_list.add_to_playlist(guild_id, youtube_search_result)

    await ctx.send("Song " + youtube_search_result.title + " added to playlist!")


@bot.command()
async def play(
    ctx: Context,
    *,
    args: str = commands.parameter(default="", description="Song to query"),
):
    """
    Adds a song to the server's playlist by searching YouTube using the provided query.

    Parameters
    ----------
    ctx : Context
        The context in which the command was invoked, including metadata such as the channel and guild.
    args : str, keyword-only
        The search query for the song to add. Declared after a `*` to make it keyword-only.
        This allows the entire remaining message (including spaces) to be captured as a single string.

    Behavior
    --------
    - Validates that a query was provided.
    - Searches YouTube using the query.
    - If a result is found, extracts the video URL suffix.
    - Adds the song to the playlist associated with the current server (`guild.id`).
    - Sends a confirmation message to the Discord text channel.

    Notes
    -----
    The use of `*` in the function signature is used to support multi-word queries.
    Without it, Discord.py would split the message by spaces and treat each word as a separate argument.

    Example
    -------
    User input: !add_playlist never going to give you up

    The full string "never going to give you up" will be passed as the `args` parameter and used to
    search YouTube. The resulting video will be added to the server's playlist.
    """
    try:
        youtube_query: str = args

        if youtube_query == "":
            await ctx.send("Please provided at least 1 argument")
            return

        logger.debug("Received arguments: %s.", args)

        youtube_search_result: AudioTrack | None = await backend.search(youtube_query)

        if youtube_search_result is None:
            logger.error(f"No video result obtained, returning.")
            await ctx.send(f"Could not find anything related to: {youtube_query}")
            return

        message: str = (
            "Matched result for query: "
            + youtube_search_result.title
            + " downloading song..."
        )
        await ctx.send(message)

        connected_to_channel: bool = await backend.connect(ctx)

        if connected_to_channel:
            logger.debug("Adding to %s to queue.", youtube_search_result.title)
            await backend.enqueue(ctx, youtube_search_result, bot, play_list)
        else:
            await ctx.send("User is not in a channel, failed to join...")
    except AttributeError as e:
        logger.error(e)
        return


@bot.command()
async def next_song(ctx: Context):
    try:
        if ctx.guild is None:
            logger.error(f"Could not obtain guild")
            return

        guild: Guild = ctx.guild
        guild_id: int = ctx.guild.id
        voice_client: VoiceClient | VoiceProtocol | None = get(
            bot.voice_clients, guild=guild
        )

        if not isinstance(voice_client, VoiceClient):
            logger.error(f"Could not obtain instance of VoiceClient")
            return

        new_audio_name: Any | Literal[""] = play_list.get_next_song(guild_id)

        if new_audio_name == "":
            await ctx.send("No more songs in playlist, going to clear playlist!")
            play_list.reset_play_list(guild_id)
            return

        if voice_client.is_playing():
            voice_client.stop()

        await backend.enqueue(ctx, new_audio_name, bot, play_list)
    except AttributeError as e:
        logger.error(e)
        return


@bot.command()
async def leave(ctx: Context):
    try:
        if ctx.guild is None:
            logger.error(f"Could not obtain guild")
            return

        guild: Guild = ctx.guild
        voice_client: VoiceClient | VoiceProtocol | None = get(
            bot.voice_clients, guild=guild
        )

        if not isinstance(voice_client, VoiceClient):
            logger.error(f"Could not obtain instance of VoiceClient")
            return

        if voice_client.is_playing():
            logger.debug("Client is playing songs, stopping")
            voice_client.stop()

        await voice_client.disconnect()
    except AttributeError as e:
        logger.error(e)
        return


@bot.command()
async def pause(ctx: Context):
    try:
        if ctx.guild is None:
            raise RuntimeError("Could not obtain guild")
        guild: Guild = ctx.guild

        voice_client: VoiceClient | VoiceProtocol | None = get(
            bot.voice_clients, guild=guild
        )

        if not isinstance(voice_client, VoiceClient):
            embed: Embed = (
                EmbedBuilder()
                .set_title("Pause Song")
                .set_description("Bot is not connected in a voice channel")
                .set_color(Color.red())
                .build()
            )
            await ctx.send(embed=embed)
            return

        if voice_client.is_paused():
            return

        if not voice_client.is_playing():
            embed: Embed = (
                EmbedBuilder()
                .set_title("Pause Song")
                .set_description("Bot is not reproducing, can't pause")
                .set_color(Color.red())
                .build()
            )
            await ctx.send(embed=embed)
            return

        voice_client.pause()
    except AttributeError as e:
        logger.error(e)
        return


@bot.command()
async def resume(ctx: Context):
    try:
        if ctx.guild is None:
            raise RuntimeError("Could not obtain guild")
        guild: Guild = ctx.guild

        voice_client: VoiceClient | VoiceProtocol | None = get(
            bot.voice_clients, guild=guild
        )

        if not isinstance(voice_client, VoiceClient):
            embed: Embed = (
                EmbedBuilder()
                .set_title("Resume Song")
                .set_description("Bot is not in a channel, can't resume")
                .set_color(Color.red())
                .build()
            )
            await ctx.send(embed=embed)
            return

        if voice_client.is_playing():
            embed: Embed = (
                EmbedBuilder()
                .set_title("Resume Song")
                .set_description("Bot is already reproducing a song")
                .set_color(Color.red())
                .build()
            )
            await ctx.send(embed=embed)
            return

        voice_client.resume()
    except AttributeError as e:
        logger.error(e)
        return


bot.run(BOT_TOKEN)
