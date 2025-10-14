from dataclasses import dataclass


@dataclass
class AudioTrack:
    """Represents a single playable audio track (YouTube, Lavalink, etc.)."""

    title: str
    url: str
    duration: float | None = None
    thumbnail: str | None = None
    author: str | None = None

    @property
    def url_without_list(self):
        """Removes the `list` query parameter from the url"""
        return AudioTrack.remove_list_query_param(self.url)

    @staticmethod
    def remove_list_query_param(url: str) -> str:
        if "http" not in url or "https" not in url:
            return url

        if "list" not in url:
            return url

        return url.split("&")[0]

    def __str__(self) -> str:
        return f"{self.title} ({self.url})"
