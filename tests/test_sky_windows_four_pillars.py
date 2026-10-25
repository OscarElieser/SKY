"""Four-pillar Windows acceptance reports limitations without false completion."""
from scripts import sky_windows_acceptance as acceptance


def test_windows_acceptance_is_readonly_and_measurable(monkeypatch):
    monkeypatch.setattr(acceptance.lab,"runtime_readiness",
                        lambda probe:{"ollama_probe_requested":probe})
    status=acceptance.build_report(False)
    assert status["component_probe"]["ollama_probe_requested"] is False
    assert set(status["four_pillars"])=={
        "voice_windows","real_artifacts","integrations","own_lora"}
    assert status["four_pillars"]["voice_windows"]["native_app_open_verified"] is False
    assert status["four_pillars"]["real_artifacts"]["providers"]["real_video_file_rendered"] is False
    assert status["four_pillars"]["integrations"]["external_actions_verified"] is False
    assert status["four_pillars"]["own_lora"]["trained_checkpoint_verified"] is False
    assert status["four_pillars"]["own_lora"]["preflight"]["model_trained"] is False
    assert status["overall_real_device_validation"]=="pending_manual_execution"
