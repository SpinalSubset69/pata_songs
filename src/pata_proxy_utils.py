from typing import Any, List, Optional
from aiohttp import ClientError, ServerTimeoutError, ClientSession
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from pata_proxy import PROXYLISTS, PataProxy, ProxyFormat, ProxyKey, ProxySource
from proxy_format_parser import ProxyFormatParser, get_format_parser
from pata_logger import Logger


logger = Logger("proxy_utils")


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ClientError, ServerTimeoutError)),
    reraise=True,
)
async def load_proxies_async(source: str | None, format: str | None) -> List[PataProxy]:
    parsed_source: ProxySource = ProxySource.from_string(source)
    parsed_format: ProxyFormat = ProxyFormat.from_string(format)

    if parsed_source is ProxySource.NO_PROXY:
        logger.info("No proxies selected")
        return []

    proxy_key = ProxyKey(source=parsed_source, format=parsed_format)
    proxy_url: str | None = PROXYLISTS.get(proxy_key)

    if proxy_url is None:
        logger.error(
            "No URL found for source=%s, format=%s", parsed_source, parsed_format
        )

        return []

    logger.info(
        "Obtained URL %s for source=%s, format=%s",
        proxy_url,
        proxy_key.source,
        proxy_key.format,
    )

    parsed_proxies: List[PataProxy] | None = []
    proxy_parser: ProxyFormatParser = get_format_parser(
        parsed_source, parsed_format, parsed_proxies
    )

    if proxy_parser.exists():
        logger.info("Found an existing configuration file, reading.")
        proxy_parser = proxy_parser.read()

        if parsed_proxies is None:
            logger.error("Could not parse proxies from file.")
            return []

        return parsed_proxies

    async with ClientSession() as session:
        async with session.get(proxy_url) as response:
            response.raise_for_status()
            data: Optional[Any] = await response.json()
            logger.debug("Obtained %s raw data", data)

            if data is None:
                logger.error("Could not obtain any data from source %s", proxy_url)
                return []

            logger.info("Obtained data, attempting to parse.")

            for item in data:
                parsed_proxy: PataProxy | None = PataProxy.from_dict(item)

                if parsed_proxy is None:
                    logger.error("Could not parse an item.")
                    continue

                logger.debug("Parsed item.")

                parsed_proxies.append(parsed_proxy)

            logger.info("Parsed %s proxies", len(parsed_proxies))

            proxy_parser.add_range(parsed_proxies)
            proxy_parser.save()

            return parsed_proxies
