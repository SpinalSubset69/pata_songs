from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
from pata_logger import Logger

logger = Logger("proxy")


class ProxySource(Enum):
    NO_PROXY = "NoProxy"
    FRESH_PROXY = "FreshProxy"

    @staticmethod
    def from_string(source: str | None):
        if source in ["NoProxy"] or source is None:
            return ProxySource.NO_PROXY

        return ProxySource.FRESH_PROXY


class ProxyFormat(Enum):
    NO_FORMAT = "NoFormat"
    JSON = "Json"

    @staticmethod
    def from_string(format: str | None):
        if format in ["NoFormat"] or format is None:
            return ProxyFormat.NO_FORMAT

        return ProxyFormat.JSON


@dataclass(frozen=True)
class ProxyKey:
    source: ProxySource
    format: ProxyFormat


PROXYLISTS: dict[ProxyKey, str] = {
    ProxyKey(
        source=ProxySource.FRESH_PROXY, format=ProxyFormat.JSON
    ): "https://vakhov.github.io/fresh-proxy-list/proxylist.json",
}


@dataclass
class PataProxy:
    ip: str
    cid: Optional[str]
    host: Optional[str]
    port: Optional[str]
    lastseen: Optional[str]
    delay: Optional[str]
    country_code: Optional[str]
    country_name: Optional[str]
    city: Optional[str]
    checks_up: Optional[str]
    checks_down: Optional[str]
    anon: Optional[str]
    http: Optional[str]
    ssl: Optional[str]
    socks4: Optional[str]
    socks5: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        dict_ip: str | None = data.get("ip")

        if dict_ip is None:
            logger.error("value: %s does not contain ip.", data)
            return None

        return cls(
            ip=dict_ip,
            cid=data.get("cid"),
            host=data.get("host"),
            port=data.get("port"),
            lastseen=data.get("lastseen"),
            delay=data.get("delay"),
            country_code=data.get("country_code"),
            country_name=data.get("country_name"),
            city=data.get("city"),
            checks_up=data.get("checks_up"),
            checks_down=data.get("checks_down"),
            anon=data.get("anon"),
            http=data.get("http"),
            ssl=data.get("ssl"),
            socks4=data.get("socks4"),
            socks5=data.get("socks5"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "cid": self.cid,
            "host": self.host,
            "port": self.port,
            "lastseen": self.lastseen,
            "delay": self.delay,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "city": self.city,
            "checks_up": self.checks_up,
            "checks_down": self.checks_down,
            "anon": self.anon,
            "http": self.http,
            "ssl": self.ssl,
            "socks4": self.socks4,
            "socks5": self.socks5,
        }
