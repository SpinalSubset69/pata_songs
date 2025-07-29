from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from pata_logger import Logger
from pata_proxy import PataProxy, ProxyFormat, ProxySource


logger = Logger("proxy_saver")


class ProxyFormatParser(ABC):
    source: ProxySource = ProxySource.NO_PROXY
    format: ProxyFormat = ProxyFormat.NO_FORMAT
    proxies: List[PataProxy] = []

    def __init__(
        self, source: ProxySource, format: ProxyFormat, proxies: List[PataProxy]
    ):
        self.source = source
        self.format = format
        self.proxies = proxies

    @property
    def filename(self) -> Path:
        return Path(
            f"proxylist/parsed_proxies_{self.source.value.lower()}.{self.format.value.lower()}"
        )

    @abstractmethod
    def save(self) -> None:
        pass

    @abstractmethod
    def read(self) -> "ProxyFormatParser":
        pass

    def add(self, proxy: PataProxy) -> None:
        logger.info("Adding proxy %s.", str(proxy))
        self.proxies.append(proxy)

    def add_range(self, proxies: List[PataProxy]) -> None:
        logger.info("Adding %s proxies.", len(proxies))
        self.proxies.extend(proxies)

    def exists(self) -> bool:
        return self.filename.exists()


class JsonFormatParser(ProxyFormatParser):
    def save(self) -> None:
        from json import dump

        try:
            with self.filename.open("w", encoding="utf-8") as f:
                dump(
                    [p.to_dict() for p in self.proxies], f, indent=2, ensure_ascii=False
                )
            logger.info("Saved proxies to JSON file: %s", self.filename)
        except Exception as e:
            logger.error("Failed to save proxies to JSON: %s", e)

    def read(self) -> ProxyFormatParser:
        from json import load

        try:
            if not self.exists():
                logger.warning("File %s does not exist. Cannot read.", self.filename)
                return self

            with self.filename.open("r", encoding="utf-8") as f:
                data = load(f)

            self.proxies = [
                proxy
                for proxy in (PataProxy.from_dict(item) for item in data)
                if proxy is not None
            ]

            logger.info(
                "Loaded %s proxies from JSON file: %s", len(self.proxies), self.filename
            )
        except Exception as e:
            logger.error("Failed to read proxies from JSON: %s", e)

        return self


class CsvFormatParser(ProxyFormatParser):
    def save(self) -> None:
        from csv import DictWriter

        try:
            with self.filename.open("w", newline="", encoding="utf-8") as f:
                writer: DictWriter[str] = DictWriter(
                    f, fieldnames=self.proxies[0].to_dict().keys()
                )
                writer.writeheader()
                for p in self.proxies:
                    writer.writerow(p.to_dict())
            logger.info("Saved proxies to CSV file: %s", self.filename)
        except Exception as e:
            logger.error("Failed to save proxies to CSV: %s", e)

    def read(self) -> ProxyFormatParser:
        from csv import DictReader

        try:
            if not self.exists():
                logger.warning("File %s does not exist. Cannot read.", self.filename)
                return self

            with self.filename.open("r", newline="", encoding="utf-8") as f:
                reader: DictReader[str] = DictReader(f)
                self.proxies = [
                    proxy
                    for proxy in (PataProxy.from_dict(row) for row in reader)
                    if proxy is not None
                ]
            logger.info(
                "Loaded %s proxies from CSV file: %s", len(self.proxies), self.filename
            )
        except Exception as e:
            logger.error("Failed to read proxies from CSV: %s", e)

        return self


class NoFormatSaver(ProxyFormatParser):
    def save(self) -> None:
        logger.info("No saving performed due to no source nor format configured.")

    def read(self) -> ProxyFormatParser:
        logger.info("No saving performed due to no source nor format configured.")
        return self


def get_format_parser(
    source: ProxySource, format: ProxyFormat, proxies: List[PataProxy]
) -> ProxyFormatParser:
    logger.debug("Getting proxy parser for format %s", format)

    if format == ProxyFormat.NO_FORMAT:
        return NoFormatSaver(ProxySource.NO_PROXY, ProxyFormat.NO_FORMAT, [])

    if format == ProxyFormat.JSON:
        return JsonFormatParser(source, format, proxies)
