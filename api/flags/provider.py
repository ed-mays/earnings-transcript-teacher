"""FeatureFlagProvider protocol — the interface all providers must implement."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class FeatureFlagProvider(Protocol):
    """Protocol for checking feature flag state."""

    def is_enabled(self, key: str, *, default: bool = False) -> bool:
        """Return the flag's enabled state, or default if the key is not found."""
        ...

    def get_all(self) -> dict[str, bool]:
        """Return all flags as a {key: enabled} dict."""
        ...

    def invalidate_cache(self) -> None:
        """Invalidate the in-memory cache so the next call reloads from storage."""
        ...
