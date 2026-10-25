"""NetPlan: offline IPv4 planning API."""
from contextlib import asynccontextmanager
from ipaddress import IPv4Address, IPv4Network
import logging
import os
from time import perf_counter

from fastapi import FastAPI, HTTPException, Query, Request

VERSION = "1.0.0"
logger = logging.getLogger("netplan")


def parse_network(cidr: str) -> IPv4Network:
    """Require explicit prefix; normalize host bits, e.g. .42/24 -> .0/24."""
    try:
        if "/" not in cidr:
            raise ValueError
        return IPv4Network(cidr, strict=False)
    except ValueError:
        raise HTTPException(422, "Укажите IPv4-сеть с маской, например 192.168.1.0/24") from None


def describe(network: IPv4Network) -> dict:
    # /31 is a point-to-point link; /32 describes a single address.
    usable = network.num_addresses if network.prefixlen >= 31 else network.num_addresses - 2
    first = network.network_address if network.prefixlen >= 31 else network.network_address + 1
    last = network.broadcast_address if network.prefixlen >= 31 else network.broadcast_address - 1
    return {"network": str(network), "netmask": str(network.netmask),
            "broadcast": str(network.broadcast_address), "total_addresses": network.num_addresses,
            "usable_hosts": usable, "first_host": str(first), "last_host": str(last)}


def create_app() -> FastAPI:
    name = os.getenv("APP_NAME", "NetPlan").strip() or "NetPlan"
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
    try:
        max_subnets = int(os.getenv("MAX_SUBNETS", "256"))
        if not 1 <= max_subnets <= 4096:
            raise ValueError
    except ValueError:
        raise ValueError("MAX_SUBNETS must be an integer between 1 and 4096") from None
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger.setLevel(level)

    @asynccontextmanager
    async def lifespan(application):
        logger.info("service_started version=%s max_subnets=%s", VERSION, max_subnets)
        yield
        logger.info("service_stopped")

    api = FastAPI(title=name, version=VERSION, lifespan=lifespan,
                  description="Расчёт IPv4-подсетей без сетевого сканирования и внешних API.")

    @api.middleware("http")
    async def log_request(request: Request, call_next):
        start = perf_counter()
        response = await call_next(request)
        # Do not log query strings, headers or request bodies.
        logger.info("request method=%s path=%s status=%s duration_ms=%.2f",
                    request.method, request.url.path, response.status_code,
                    (perf_counter() - start) * 1000)
        return response

    @api.get("/", tags=["Service"])
    def root():
        return {"service": name, "docs": "/docs", "description": "Планирование IPv4-сетей"}

    @api.get("/health", tags=["Service"])
    def health():
        return {"status": "ok", "service": name}

    @api.get("/version", tags=["Service"])
    def version():
        return {"version": VERSION}

    @api.get("/networks/info", tags=["IPv4"], summary="Параметры подсети")
    def network_info(cidr: str = Query(..., max_length=64, examples=["192.168.1.42/24"])):
        return describe(parse_network(cidr))

    return api


app = create_app()
