from typing import List, Optional
from pata_logger import Logger
from pata_proxy import PataProxy

logger = Logger("proxy_selector")


class ProxySelector:
    proxies: List[PataProxy] = []

    def __init__(self, proxies: List[PataProxy]):
        self.proxies = proxies

    def has_proxies(self) -> bool:
        return len(self.proxies) > 0

    def random_proxy_ip(self) -> Optional[str]:
        # TODO: try ping proxy before returning and remove if no response
        # TODO: if the previous takes too long, consider running a background task on startup to eliminate non-working proxies

        from random import choice

        if not self.proxies:
            logger.error("No proxies found but configured to use a proxy.")
            return None

        random_ip = choice(self.proxies).ip

        logger.debug("Selected proxy %s.", random_ip)

        return random_ip
