from backend.app.external.stubs import stub_enabled


def test_stub_enabled_reads_env(monkeypatch):
    monkeypatch.setenv("NTM_STUB_EXTERNAL", "1")
    assert stub_enabled() is True
    monkeypatch.setenv("NTM_STUB_EXTERNAL", "0")
    assert stub_enabled() is False
    monkeypatch.delenv("NTM_STUB_EXTERNAL", raising=False)
    assert stub_enabled() is False
