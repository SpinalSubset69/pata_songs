from tkinter import NO
from typing import Any, List, Literal
from youtube_result import YoutubeResult
from playlist import PlayList
from discord.ext import commands
from discord.ext.commands import Bot, Context
from youtube_search import YoutubeSearch
from dotenv import load_dotenv
from discord.utils import get
from discord import Guild, Intents, VoiceProtocol, VoiceClient
from os import getenv
from pata_logger import Logger
import bot_utils

load_dotenv()

BOT_TOKEN: str | None = getenv("BOT_TOKEN")

if BOT_TOKEN is None:
    raise RuntimeError("Could not obtain token from environment settings.")

intents: Intents = Intents.default()
intents.message_content = True
bot = Bot(command_prefix="$", intents=intents)
play_list = PlayList()
logger = Logger("pata_song_bot")


@bot.command()
async def reproduce_playlist(ctx: Context):
    if ctx.guild is None:
        logger.error("Could not obtain guild")
        return

    guild_id: int = ctx.guild.id

    if play_list.get_playlist_lenght(guild_id) == 0:
        await ctx.send("No songs in playlist, please add at least one")
        return

    audio_name: Any | Literal[""] = play_list.get_next_song(guild_id)

    if audio_name == "":
        await ctx.send("Play list end")
        play_list.reset_play_list(guild_id)
        return

    connected_to_channel: bool = await bot_utils.connect_to_voice_channel(ctx, bot)
    if connected_to_channel:
        # connect bot to channel
        await ctx.send("Bot connected to channel!")

        # Reproduce Music
        await bot_utils.reproduce_song(
            ctx=ctx, audio_name=audio_name, bot=bot, play_list=play_list
        )
    else:
        await ctx.send("User is not in a channel, failed to join...")


@bot.command()
async def add_playlist(
    ctx: Context,
    args: str = commands.parameter(default="", description="Song to query"),
):
    youtube_query: str = bot_utils.get_command_args_split(args)

    if youtube_query == "":
        await ctx.send("Please provided at least 1 argument")
        return

    youtube_search_results: List[Any] | str = YoutubeSearch(
        youtube_query, max_results=5
    ).to_dict()

    typed_results: List[YoutubeResult] = []

    if isinstance(youtube_search_results, str):
        await ctx.send(f"Search failed or returned error: {youtube_search_results}")
        return
    else:
        typed_results = [YoutubeResult(entry) for entry in youtube_search_results]

    if len(typed_results) > 1:
        youtube_result: YoutubeResult = typed_results[0]

        if ctx.guild is None:
            logger.error(f"Could not obtain guild")
            return

        guild_id: int = ctx.guild.id

        audio_name: str = bot_utils.download_youtube_song(
            youtube_result["url_suffix"], youtube_result["title"]
        )

        play_list.add_to_playlist(guild_id, audio_name)

        await ctx.send("Song " + audio_name + " added to playlist!")


@bot.command()
async def play(
    ctx: Context,
    args: str = commands.parameter(default="", description="Song to query"),
):
    try:
        youtube_query: str = bot_utils.get_command_args_split(args)

        if youtube_query == "":
            await ctx.send("Please provided at least 1 argument")
            return

        youtube_search_results: List[Any] | str = YoutubeSearch(
            youtube_query, max_results=5
        ).to_dict()

        typed_results: List[YoutubeResult] = []

        if isinstance(youtube_search_results, str):
            await ctx.send(f"Search failed or returned error: {youtube_search_results}")
            return
        else:
            typed_results = [YoutubeResult(entry) for entry in youtube_search_results]

        if len(typed_results) > 1:
            youtube_result: YoutubeResult = typed_results[0]

            message: str = (
                "Matched result for query: "
                + youtube_result["title"]
                + " downloading song..."
            )
            await ctx.send(message)
            
            if 'list' in youtube_result["url_suffix"]:
                youtube_result["url_suffix"] = youtube_result["url_suffix"].split('&')[0]

            audio_name: str = bot_utils.download_youtube_song(
                youtube_result["url_suffix"], youtube_result["title"]
            )

            connected_to_channel: bool = await bot_utils.connect_to_voice_channel(
                ctx, bot
            )

            if connected_to_channel:
                # Reproduce Music
                await bot_utils.reproduce_song(
                    ctx=ctx, audio_name=audio_name, bot=bot, play_list=play_list
                )
            else:
                await ctx.send("User is not in a channel, failed to join...")
    except AttributeError as e:
        logger.error(e)
        return


@bot.command()
async def next_song(ctx: Context):
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

    await bot_utils.reproduce_song(ctx, new_audio_name, bot, play_list)


@bot.command()
async def leave(ctx: Context):
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

    await voice_client.disconnect()

bot.run(BOT_TOKEN)
