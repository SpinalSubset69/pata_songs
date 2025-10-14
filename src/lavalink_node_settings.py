from dataclasses import dataclass


@dataclass
class NodeSettings:
    """Contains the settings used to configure a Lavalink Node"""

    host: str
    port: int
    label: str
    password: str
