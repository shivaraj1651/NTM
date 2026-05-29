"""Single switch for stubbing outbound external calls (LLMs, ad platforms, media)."""
import os


def stub_enabled() -> bool:
    return os.getenv("NTM_STUB_EXTERNAL", "0").strip().lower() in {"1", "true", "yes"}
