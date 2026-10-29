"""SKY experimental *from-scratch* byte-level causal Transformer.

Opt-in/offline single-device training on CPU, CUDA or an attached TPU via
PyTorch/XLA. Never reads chat archives, keys or private files automatically.
This is a small educational model; it is NOT Gemini and is NOT wired to SKY chat.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
from datetime import datetime, timezone
from pathlib import Path

VOCAB = 257  # UTF-8 bytes plus example separator
MAX_DATA_BYTES = 4_000_000


class TinyTransformerError(ValueError):
    pass


def approved_text(dataset: str):
    from neural_core.sky_train_model import split_dataset, validate_dataset

    pairs = validate_dataset(dataset)
    train, valid = split_dataset(pairs)
    def encode(rows):
        text = "\n".join("Usuario: " + q + "\nSKY: " + a for q, a in rows)
        raw = text.encode("utf-8")
        if len(raw) > MAX_DATA_BYTES:
            raise TinyTransformerError("Dataset experimental supera 4 MB de texto aprobado.")
        return list(raw) + [256]
    return pairs, encode(train), encode(valid)


def build_model(*, context=64, width=64, layers=2, heads=4):
    import torch
    from torch import nn
    if width % heads:
        raise TinyTransformerError("El tamaño de las capas debe dividirse entre cabezas.")
    class SkyTinyTransformer(nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = nn.Embedding(VOCAB, width)
            self.position = nn.Embedding(context, width)
            layer = nn.TransformerEncoderLayer(
                d_model=width, nhead=heads, dim_feedforward=width * 4,
                dropout=0.0, batch_first=True, activation="gelu")
            self.layers = nn.TransformerEncoder(layer, num_layers=layers,
                                                enable_nested_tensor=False)
            self.norm = nn.LayerNorm(width)
            self.head = nn.Linear(width, VOCAB, bias=False)

        def forward(self, x):
            n = x.size(1)
            if n > context:
                raise TinyTransformerError("La consulta excede el contexto entrenado.")
            positions = torch.arange(n, device=x.device)
            encoded = self.embedding(x) + self.position(positions)[None, :, :]
            causal = torch.triu(torch.ones(n, n, device=x.device, dtype=torch.bool), diagonal=1)
            out = self.layers(encoded, mask=causal)
            return self.head(self.norm(out))
    return SkyTinyTransformer()


def resolve_device(choice):
    import torch
    if choice not in {"cpu", "cuda", "tpu", "auto"}:
        raise TinyTransformerError("Dispositivo debe ser cpu, cuda, tpu o auto.")
    if choice == "auto":
        choice = "cuda" if torch.cuda.is_available() else "cpu"
    if choice == "cuda":
        if not torch.cuda.is_available():
            raise TinyTransformerError("No hay GPU CUDA disponible.")
        return torch.device("cuda"), False, "CUDA"
    if choice == "tpu":
        # Explicitly reject the XLA CPU emulator; do not claim a real TPU without one.
        if os.getenv("PJRT_DEVICE", "").upper() != "TPU":
            raise TinyTransformerError("Configurá PJRT_DEVICE=TPU en el host TPU.")
        try:
            import torch_xla
            from torch_xla.core import xla_model as xm
            device = torch_xla.device()
            if xm.xla_device_hw(device).upper() != "TPU":
                raise TinyTransformerError("El dispositivo XLA no es una TPU física.")
        except ImportError as exc:
            raise TinyTransformerError("La TPU requiere PyTorch/XLA instalado en el host.") from exc
        return device, True, "TPU-XLA"
    return torch.device("cpu"), False, "CPU"


def batch(tokens, *, context, count, device, rng):
    import torch
    if len(tokens) < context + 2:
        raise TinyTransformerError("Dataset demasiado pequeño para esa ventana.")
    starts = [rng.randrange(0, len(tokens) - context - 1) for _ in range(count)]
    x = torch.tensor([tokens[i:i+context] for i in starts],
                     dtype=torch.long, device=device)
    y = torch.tensor([tokens[i+1:i+context+1] for i in starts],
                     dtype=torch.long, device=device)
    return x, y


def evaluate(model, tokens, *, context, device):
    import torch
    import torch.nn.functional as F
    model.eval()
    rng = random.Random(912)
    with torch.no_grad():
        losses = []
        for _ in range(4):
            x, y = batch(tokens, context=context, count=1, device=device, rng=rng)
            result = model(x)
            losses.append(float(F.cross_entropy(result.reshape(-1, VOCAB),
                                                 y.reshape(-1)).detach().cpu()))
    return sum(losses) / len(losses)


def train(*, dataset, output, device="cpu", steps=20, context=64,
          confirm_rights=False, seed=42):
    if not confirm_rights:
        raise TinyTransformerError("Se requiere --confirm-rights: datos con permiso explícito.")
    if not 1 <= steps <= 2000 or not 24 <= context <= 256:
        raise TinyTransformerError("Usá 1-2000 pasos y contexto de 24-256 bytes.")
    dest = Path(output).expanduser().resolve()
    project = Path(__file__).resolve().parents[1]
    if dest == project or project in dest.parents:
        raise TinyTransformerError("Guardá los checkpoints FUERA del repositorio GitHub.")
    if dest.exists():
        raise TinyTransformerError("El destino ya existe. Nunca sobrescribir checkpoints.")
    examples, training, heldout = approved_text(dataset)
    if len(training) <= context + 2 or len(heldout) <= context + 2:
        raise TinyTransformerError("La partición de entrenamiento o evaluación es insuficiente.")
    import torch
    import torch.nn.functional as F
    torch.manual_seed(seed)
    runtime, xla, hardware = resolve_device(device)
    model = build_model(context=context).to(runtime)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0005)
    rng = random.Random(seed)
    before = evaluate(model, heldout, context=context, device=runtime)
    training_loss = before
    for _ in range(steps):
        model.train()
        x, y = batch(training, context=context, count=4, device=runtime, rng=rng)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, VOCAB), y.reshape(-1))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        if xla:
            from torch_xla.core import xla_model as xm
            xm.optimizer_step(optimizer, barrier=True)
        else:
            optimizer.step()
        training_loss = float(loss.detach().cpu())
    after = evaluate(model, heldout, context=context, device=runtime)
    if not all(math.isfinite(v) for v in [before, after, training_loss]):
        raise TinyTransformerError("Evaluación no finita. No se guarda checkpoint.")
    manifest = {
        "name": "SKY Tiny Transformer experimental",
        "model_type": "byte_level_transformer_encoder_causal",
        "training_method": "from_scratch",
        "not_gemini": True,
        "not_production_ready": True,
        "active_in_android": False,
        "active_in_windows": False,
        "training_hardware": hardware,
        "steps": steps,
        "context_bytes": context,
        "training_examples": len(examples) - max(1, len(examples)//10),
        "heldout_examples": max(1,len(examples)//10),
        "train_loss_last": round(training_loss, 5),
        "heldout_loss_before": round(before, 5),
        "heldout_loss_after": round(after, 5),
        "heldout_improved": after < before,
        "dataset_sha256": hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),
        "seed": seed,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner_activated": False,
    }
    dest.mkdir(parents=True, exist_ok=False)
    torch.save({"state_dict": {k:v.detach().cpu() for k,v in model.state_dict().items()},
                "context": context, "width": 64, "layers": 2, "heads": 4},
               dest / "sky_tiny_transformer.pt")
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def preflight(dataset, device="cpu"):
    pairs, training, heldout = approved_text(dataset)
    if device == "tpu":
        try:
            runtime, _, hardware = resolve_device(device)
            available = True
        except (TinyTransformerError, RuntimeError) as exc:
            available = False
            hardware = "TPU no disponible: " + str(exc)
    else:
        _, _, hardware = resolve_device(device)
        available = True
    return {"mode": "preflight", "training_performed": False,
            "approved_examples": len(pairs), "training_bytes": len(training),
            "validation_bytes": len(heldout), "requested_device": device,
            "device_available": available, "hardware": hardware}


def main(argv=None):
    p = argparse.ArgumentParser(description="Entrenamiento experimental propio de SKY, sin red")
    p.add_argument("--dataset", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--device", choices=["cpu","cuda","tpu","auto"], default="cpu")
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--context", type=int, default=64)
    p.add_argument("--preflight", action="store_true")
    p.add_argument("--confirm-rights", action="store_true")
    args = p.parse_args(argv)
    report = preflight(args.dataset,args.device) if args.preflight else train(
        dataset=args.dataset, output=args.output, device=args.device,
        steps=args.steps, context=args.context, confirm_rights=args.confirm_rights)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
