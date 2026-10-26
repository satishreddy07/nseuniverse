"""Optional Kotak Neo SDK adapter for live, analysis-only market data."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterable

from nse_universe.validation.market_data import require_aware_datetime, require_finite_number


@dataclass(frozen=True, slots=True)
class KotakNeoConfig:
    """Credentials/configuration loaded from environment variables."""

    consumer_key: str
    mobile_number: str
    ucc: str
    mpin: str
    environment: str = "prod"

    @classmethod
    def from_env(cls) -> "KotakNeoConfig":
        values = {
            "consumer_key": os.getenv("KOTAK_NEO_CONSUMER_KEY", "").strip(),
            "mobile_number": os.getenv("KOTAK_NEO_MOBILE_NUMBER", "").strip(),
            "ucc": os.getenv("KOTAK_NEO_UCC", "").strip(),
            "mpin": os.getenv("KOTAK_NEO_MPIN", "").strip(),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            env_names = {
                "consumer_key": "KOTAK_NEO_CONSUMER_KEY",
                "mobile_number": "KOTAK_NEO_MOBILE_NUMBER",
                "ucc": "KOTAK_NEO_UCC",
                "mpin": "KOTAK_NEO_MPIN",
            }
            raise ValueError(
                "Missing required environment variables: "
                + ", ".join(env_names[name] for name in missing)
            )
        environment = os.getenv("KOTAK_NEO_ENVIRONMENT", "prod").strip() or "prod"
        return cls(**values, environment=environment)


@dataclass(frozen=True, slots=True)
class NormalizedTick:
    """Provider-independent tick; raw SDK objects are not retained."""

    instrument_token: str
    exchange_segment: str
    last_traded_price: float
    received_at: datetime
    trading_symbol: str | None = None
    exchange_timestamp: datetime | None = None
    last_traded_quantity: float | None = None
    volume: float | None = None
    open_interest: float | None = None
    total_buy_quantity: float | None = None
    total_sell_quantity: float | None = None
    best_bid_price: float | None = None
    best_bid_quantity: float | None = None
    best_ask_price: float | None = None
    best_ask_quantity: float | None = None
    source: str = "kotak_neo"

    def __post_init__(self) -> None:
        if not self.instrument_token.strip():
            raise ValueError("instrument_token must not be empty")
        if not self.exchange_segment.strip():
            raise ValueError("exchange_segment must not be empty")
        object.__setattr__(
            self,
            "last_traded_price",
            require_finite_number(self.last_traded_price, field_name="last_traded_price"),
        )
        for name in (
            "last_traded_quantity", "volume", "open_interest", "total_buy_quantity",
            "total_sell_quantity", "best_bid_quantity", "best_ask_quantity",
        ):
            value = getattr(self, name)
            if value is not None:
                number = require_finite_number(value, field_name=name)
                if number < 0:
                    raise ValueError(f"{name} must be non-negative")
                object.__setattr__(self, name, number)
        for name in ("best_bid_price", "best_ask_price"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, require_finite_number(value, field_name=name))
        require_aware_datetime(self.received_at, field_name="received_at")
        if self.exchange_timestamp is not None:
            require_aware_datetime(self.exchange_timestamp, field_name="exchange_timestamp")


class KotakNeoAdapter:
    """Thin wrapper around the official kotakneoapi async SFeed client.

    Pass the current TOTP to authenticate() at runtime; it is never persisted.
    This adapter intentionally exposes no order-placement methods.
    """

    def __init__(self, config: KotakNeoConfig, *, client: Any | None = None) -> None:
        self.config = config
        self._client = client
        self._authenticated = False

    def authenticate(self, *, totp: str) -> None:
        """Perform official SDK TOTP login and MPIN validation."""
        if not totp or not totp.strip():
            raise ValueError("A current TOTP code must be supplied at login time")
        if self._client is None:
            try:
                from neo_api_client import NeoAPI
            except ImportError as exc:
                raise RuntimeError(
                    "Kotak Neo support is optional. Install it with: "
                    "python -m pip install -e '.[kotak-neo]'"
                ) from exc
            self._client = NeoAPI(
                consumer_key=self.config.consumer_key,
                environment=self.config.environment,
            )
        self._client.totp_login(
            mobile_number=self.config.mobile_number,
            ucc=self.config.ucc,
            totp=totp.strip(),
        )
        self._client.totp_validate(mpin=self.config.mpin)
        self._authenticated = True

    @staticmethod
    def normalize_message(
        message: Any, *, received_at: datetime | None = None
    ) -> NormalizedTick:
        """Normalize an SDK SFeed message/dict without guessing missing prices."""
        get = (
            message.get
            if isinstance(message, dict)
            else lambda key, default=None: getattr(message, key, default)
        )
        token = get("instrument_token") or get("exchange_token")
        segment = get("exchange_segment") or get("exchange")
        price = get("last_traded_price")
        if price is None:
            price = get("ltp")
        if token is None or segment is None:
            raise ValueError("Kotak Neo tick is missing instrument token or exchange segment")
        if price is None:
            raise ValueError("Kotak Neo tick is missing last traded price")

        exchange_timestamp = (
            get("exchange_timestamp")
            or get("last_update_time")
            or get("last_trade_time")
            or get("timestamp")
        )
        if isinstance(exchange_timestamp, str):
            try:
                exchange_timestamp = datetime.fromisoformat(
                    exchange_timestamp.replace("Z", "+00:00")
                )
            except ValueError:
                exchange_timestamp = None
        if isinstance(exchange_timestamp, (int, float)) and not isinstance(
            exchange_timestamp, bool
        ):
            try:
                exchange_timestamp = (
                    datetime.fromtimestamp(exchange_timestamp, tz=timezone.utc)
                    if exchange_timestamp > 0
                    else None
                )
            except (OverflowError, OSError, ValueError):
                exchange_timestamp = None
        if exchange_timestamp is not None and (
            not isinstance(exchange_timestamp, datetime)
            or exchange_timestamp.tzinfo is None
            or exchange_timestamp.utcoffset() is None
        ):
            exchange_timestamp = None

        received = received_at or datetime.now(timezone.utc)

        def optional_number(*keys: str) -> float | None:
            for key in keys:
                value = get(key)
                if value is not None:
                    return require_finite_number(value, field_name=key)
            return None

        return NormalizedTick(
            instrument_token=str(token),
            exchange_segment=str(segment),
            trading_symbol=get("trading_symbol") or get("display_symbol"),
            last_traded_price=require_finite_number(price, field_name="last_traded_price"),
            received_at=received,
            exchange_timestamp=exchange_timestamp,
            last_traded_quantity=optional_number(
                "last_traded_quantity", "last_traded_qty", "last_trade_qty"
            ),
            volume=optional_number("volume", "last_volume", "volume_traded_today"),
            open_interest=optional_number("open_interest", "oi"),
            total_buy_quantity=optional_number("total_buy_quantity"),
            total_sell_quantity=optional_number("total_sell_quantity"),
            best_bid_price=_best_level(message, "buy", "price"),
            best_bid_quantity=_best_level(message, "buy", "quantity"),
            best_ask_price=_best_level(message, "sell", "price"),
            best_ask_quantity=_best_level(message, "sell", "quantity"),
        )

    async def stream(
        self, tokens: Iterable[tuple[str, str]], *, feed_type: str = "touchline"
    ) -> AsyncIterator[NormalizedTick]:
        """Subscribe to token pairs and yield normalized ticks.

        feed_type may be touchline, depth, or full_depth. The official SDK manages
        its documented feed reconnection and re-subscription behavior.
        """
        if not self._authenticated or self._client is None:
            raise RuntimeError("Call authenticate(totp=...) before streaming")
        try:
            from neo_api_client.websocket.feed import WsToken
        except ImportError as exc:
            raise RuntimeError(
                "Installed Kotak Neo SDK lacks the modern SFeed API; upgrade kotakneoapi."
            ) from exc

        subscriptions = [(str(segment), str(token)) for segment, token in tokens]
        if not subscriptions:
            raise ValueError("At least one instrument subscription is required")
        if len(subscriptions) > 3000:
            raise ValueError("Kotak Neo SFeed supports at most 3000 subscribed tokens")
        methods = {
            "touchline": "subscribe_scrips",
            "depth": "subscribe_depth",
            "full_depth": "subscribe_full_depth",
        }
        if feed_type not in methods:
            raise ValueError("feed_type must be touchline, depth, or full_depth")
        ws_tokens = [WsToken(segment, token) for segment, token in subscriptions]
        async with self._client.create_websocket() as websocket:
            await getattr(websocket, methods[feed_type])(ws_tokens)
            async for message in websocket:
                try:
                    yield self.normalize_message(message)
                except (TypeError, ValueError):
                    # Non-price events and incomplete packets are not market ticks.
                    continue


def _best_level(message: Any, side: str, field: str) -> float | None:
    """Read best bid/ask from SDK depth rows when present."""
    rows = (
        message.get(side, [])
        if isinstance(message, dict)
        else getattr(message, side, [])
    )
    if not rows:
        return None
    level = rows[0]
    value = level.get(field) if isinstance(level, dict) else getattr(level, field, None)
    if value is None:
        return None
    return require_finite_number(value, field_name=f"{side}.{field}")
