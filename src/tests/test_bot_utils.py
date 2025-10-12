from unittest.mock import patch

import pytest
from bot_utils import (
    create_audio_source_from_url,
    get_youtube_stream_url,
    search_youtube,
)
from pata_logger import Logger
from youtube_result import YoutubeResult

logger = Logger("bot_utils")


@patch("bot_utils.YoutubeDL")
def test_search_youtube_success(mock_ytdl):
    mock_ytdl.return_value.extract_info.return_value = {
        "entries": [{"title": "test song", "url": "https://youtu.be/test"}]
    }

    result: YoutubeResult | None = search_youtube("test song")

    logger.debug(f"Mock result: {result}")

    assert result is not None
    assert result["title"] == "test song"
    assert "youtu.be/test" in result["url_suffix"]


@patch("bot_utils.YoutubeDL")
def test_search_youtube_no_results(mock_ytdl):
    mock_ytdl.return_value.extract_info.return_value = {"entries": []}

    result: YoutubeResult | None = search_youtube("does not exist")

    assert result is None


@patch("bot_utils.YoutubeDL")
def test_get_youtube_stream_url_success(mock_ytdl):
    mock_ytdl.return_value.__enter__.return_value.extract_info.return_value = {
        "formats": [
            {
                "vcodec": "none",
                "acodec": "mp4a",
                "abr": 128,
                "url": "https://audio.test",
            }
        ]
    }

    url: str | None = get_youtube_stream_url("https://youtu.be/test")

    assert url == "https://audio.test"


@patch("bot_utils.YoutubeDL")
def test_get_youtube_stream_url_no_audio_formats(mock_ytdl):
    mock_ytdl.return_value.__enter__.return_value.extract_info.return_value = {
        "formats": [{"vcodec": "h264", "acodec": "none"}]
    }

    url: str | None = get_youtube_stream_url("https://youtu.be/test")

    assert url is None


@patch("bot_utils.exists", return_value=True)
@patch("bot_utils.platform.system", return_value="Linux")
def test_create_audio_source_from_url_success(mock_system, mock_exists):
    stream_url = "https://audio.test"
    result = create_audio_source_from_url(stream_url)
    assert result is not None


@patch("bot_utils.exists", return_value=False)
@patch("bot_utils.platform.system", return_value="Windows")
def test_create_audio_source_from_url_missing_ffmpeg(mock_system, mock_exists):
    result = create_audio_source_from_url("https://audio.test")
    assert result is None


def test_search_youtube_real():
    query = "Rooster (2022 Remaster)"
    result: YoutubeResult | None = search_youtube(query)

    assert result is not None
    assert "title" in result
    assert "url_suffix" in result


def test_get_youtube_stream_url_real():
    """we need to change the url if it's eventually removed"""
    video_url = "https://www.youtube.com/watch?v=ZUqBglpHTO0"  # Rooster (2022 Remaster)
    stream_url: str | None = get_youtube_stream_url(video_url)

    assert stream_url is not None
    assert stream_url.startswith("http")
