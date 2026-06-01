"""Single switch for stubbing outbound external calls (LLMs, ad platforms, media)."""
import os


def stub_enabled() -> bool:
    return os.getenv("NTM_STUB_EXTERNAL", "0").strip().lower() in {"1", "true", "yes"}


def ads_test_mode() -> bool:
    """Real API calls to Google/Meta but campaigns created PAUSED — safe for developer testing.

    When True: campaigns are created with PAUSED status and [TEST] name prefix.
    No real budget is spent. Platform IDs are real and can be inspected in the ad consoles.
    """
    return os.getenv("NTM_ADS_TEST_MODE", "0").strip().lower() in {"1", "true", "yes"}
