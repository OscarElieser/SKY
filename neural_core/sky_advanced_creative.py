"""SKY v9.8: selección asistida de primer plano con OpenCV GrabCut.

Devuelve una máscara PNG privada reutilizable; no es segmentación semántica.
"""
from __future__ import annotations
import io
from PIL import Image
from . import sky_creative as cr


def cutout_mask(asset_id: str, rect: list[int], iterations: int = 4):
    if not isinstance(rect, list) or len(rect) != 4 or any(type(v) is not int for v in rect):
        raise ValueError('Rectángulo: [x, y, ancho, alto] con enteros')
    if type(iterations) is not int or not 1 <= iterations <= 7:
        raise ValueError('Iteraciones admitidas: 1 a 7')
    asset = cr.get_asset(asset_id)
    if not asset or asset['kind'] != 'image':
        raise ValueError('Seleccioná una imagen válida')
    path, _ = cr.asset_path(asset_id)
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError('Instalá opencv-python-headless y numpy') from exc
    with Image.open(path) as original:
        image = original.convert('RGB')
        w, h = image.size
        if w * h > 8_000_000:
            raise ValueError('El recorte asistido admite hasta 8 MP')
        x, y, rw, rh = rect
        if x < 0 or y < 0 or rw < 3 or rh < 3 or x + rw >= w or y + rh >= h:
            raise ValueError('El rectángulo debe estar dentro de la imagen')
        pixel = np.asarray(image)[:, :, ::-1].copy()
    matte = np.zeros((h, w), np.uint8)
    fg = np.zeros((1, 65), np.float64)
    bg = np.zeros((1, 65), np.float64)
    cv2.grabCut(pixel, matte, (x, y, rw, rh), bg, fg, iterations, cv2.GC_INIT_WITH_RECT)
    mask = np.where((matte == cv2.GC_FGD) | (matte == cv2.GC_PR_FGD), 255, 0).astype('uint8')
    buffer = io.BytesIO()
    Image.fromarray(mask, 'L').save(buffer, format='PNG')
    result = cr.ingest(buffer.getvalue(), 'SKY_mascara_' + asset_id + '.png')
    return {'mask_asset': result, 'rectangle': rect, 'method': 'grabcut', 'editable': True}
