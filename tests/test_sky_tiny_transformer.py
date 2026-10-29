"""CPU safety and functionality tests for the optional SKY Transformer trainer."""
import json
from pathlib import Path
import pytest
from neural_core.sky_tiny_transformer import TinyTransformerError, approved_text, preflight

def dataset(tmp_path):
    path = tmp_path / "original_authorized.jsonl"
    rows = [{"instruction": f"¿Qué significa ejemplo {i} para SKY?",
             "response": f"Es un caso original creado para probar el aprendizaje {i}.",
             "approved_for_training": True} for i in range(25)]
    path.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows),
                    encoding="utf-8")
    return path

def test_preflight_does_not_train(tmp_path):
    sample = dataset(tmp_path)
    report = preflight(str(sample), "cpu")
    assert report["approved_examples"] == 25
    assert not report["training_performed"]
    assert report["device_available"]
    assert report["training_bytes"] > report["validation_bytes"]
    assert not (tmp_path / "checkpoint").exists()

def test_model_requires_owner_authorization(tmp_path):
    torch = pytest.importorskip("torch")
    from neural_core.sky_tiny_transformer import train
    with pytest.raises(TinyTransformerError, match="confirm-rights"):
        train(dataset=str(dataset(tmp_path)), output=str(tmp_path/"checkpoint"), steps=1)
    assert not (tmp_path / "checkpoint").exists()

def test_transformer_has_true_causal_attention_and_trainable_weights():
    torch = pytest.importorskip("torch")
    from neural_core.sky_tiny_transformer import build_model
    model = build_model(context=24,width=32,layers=1,heads=4).eval()
    x = torch.tensor([[1,2,3,4,5,6]], dtype=torch.long)
    with torch.no_grad():
        before = model(x)
        changed = model(torch.tensor([[1,2,3,4,5,200]],dtype=torch.long))
    assert before.shape == (1,6,257)
    assert torch.allclose(before[:,:5,:], changed[:,:5,:], atol=1e-5)

def test_cpu_training_saves_inactive_checkpoint(tmp_path):
    pytest.importorskip("torch")
    from neural_core.sky_tiny_transformer import train
    source = dataset(tmp_path)
    output = tmp_path/"checkpoint"
    manifest = train(dataset=str(source),output=str(output),device="cpu",
                     steps=1,context=24,confirm_rights=True)
    assert (output/"sky_tiny_transformer.pt").is_file()
    assert (output/"manifest.json").is_file()
    assert manifest["training_hardware"] == "CPU"
    assert manifest["training_method"] == "from_scratch"
    assert not manifest["active_in_android"]
    assert not manifest["owner_activated"]
    with pytest.raises(TinyTransformerError, match="ya existe"):
        train(dataset=str(source),output=str(output),steps=1,context=24,confirm_rights=True)

def test_tpu_mode_never_fakes_hardware(monkeypatch):
    pytest.importorskip("torch")
    from neural_core.sky_tiny_transformer import resolve_device
    monkeypatch.delenv("PJRT_DEVICE",raising=False)
    with pytest.raises(TinyTransformerError,match="PJRT_DEVICE"):
        resolve_device("tpu")
