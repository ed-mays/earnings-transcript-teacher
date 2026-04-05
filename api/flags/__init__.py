"""Feature flag system — provider protocol and singleton factory."""

from flags.provider import FeatureFlagProvider
from flags.supabase_provider import SupabaseFlagProvider

__all__ = ["FeatureFlagProvider", "SupabaseFlagProvider", "get_flag_provider"]

_provider: SupabaseFlagProvider | None = None


def get_flag_provider() -> FeatureFlagProvider:
    """Return the module-level SupabaseFlagProvider, creating it on first call."""
    global _provider
    if _provider is None:
        _provider = SupabaseFlagProvider()
    return _provider
