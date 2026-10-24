"""Deterministic self-contained glTF 2.0 binary avatar with idle/walk animations.

No network or unlicensed third-party model is required. The model uses node
animation channels, NOT a skinned skeleton or photorealistic rig.
"""
from __future__ import annotations

from functools import lru_cache
import json
import math
import struct


def _quat_x(angle: float) -> list[float]:
    return [math.sin(angle / 2), 0.0, 0.0, math.cos(angle / 2)]


@lru_cache(maxsize=1)
def build_avatar_glb() -> bytes:
    data = bytearray()
    views: list[dict] = []
    accessors: list[dict] = []

    def accessor(values, *, components: int, component_type: int, target=None,
                 minimum=None, maximum=None):
        while len(data) % 4:
            data.append(0)
        offset = len(data)
        fmt = "f" if component_type == 5126 else "H"
        data.extend(struct.pack("<" + fmt * len(values), *values))
        view = {"buffer": 0, "byteOffset": offset,
                "byteLength": len(data) - offset}
        if target is not None:
            view["target"] = target
        views.append(view)
        acc = {"bufferView": len(views) - 1, "byteOffset": 0,
               "componentType": component_type, "count": len(values) // components,
               "type": {1: "SCALAR", 3: "VEC3", 4: "VEC4"}[components]}
        if minimum is not None:
            acc["min"] = minimum
        if maximum is not None:
            acc["max"] = maximum
        accessors.append(acc)
        return len(accessors) - 1

    # 24 vertices: each face has a stable outward normal.
    face_positions = (
        ((.5,-.5,-.5),(.5,.5,-.5),(.5,.5,.5),(.5,-.5,.5)),
        ((-.5,-.5,.5),(-.5,.5,.5),(-.5,.5,-.5),(-.5,-.5,-.5)),
        ((-.5,.5,-.5),(-.5,.5,.5),(.5,.5,.5),(.5,.5,-.5)),
        ((-.5,-.5,.5),(-.5,-.5,-.5),(.5,-.5,-.5),(.5,-.5,.5)),
        ((-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)),
        ((.5,-.5,-.5),(-.5,-.5,-.5),(-.5,.5,-.5),(.5,.5,-.5)),
    )
    face_normals = ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))
    positions, normals, indices = [], [], []
    for face, (corners, normal) in enumerate(zip(face_positions, face_normals)):
        for p in corners:
            positions.extend(p)
            normals.extend(normal)
        base = face * 4
        indices.extend([base,base+1,base+2,base,base+2,base+3])

    pa = accessor(positions, components=3, component_type=5126, target=34962,
                  minimum=[-.5,-.5,-.5],maximum=[.5,.5,.5])
    na = accessor(normals, components=3, component_type=5126, target=34962)
    ia = accessor(indices, components=1, component_type=5123, target=34963)
    nodes = [{"name":"Avatar raíz","children":[1,2,3,5,7,9]}]
    nodes.extend([
        {"name":"Torso","mesh":0,"translation":[0,1.02,0],"scale":[.53,.8,.31],
         "extras":{"part":"outfit"}},
        {"name":"Cabeza","mesh":0,"translation":[0,1.64,0],"scale":[.43,.45,.42],
         "extras":{"part":"skin"}},
        {"name":"Hombro izquierdo","translation":[-.34,1.32,0],"children":[4]},
        {"name":"Brazo izquierdo","mesh":0,"translation":[0,-.31,0],"scale":[.19,.63,.21],
         "extras":{"part":"outfit"}},
        {"name":"Hombro derecho","translation":[.34,1.32,0],"children":[6]},
        {"name":"Brazo derecho","mesh":0,"translation":[0,-.31,0],"scale":[.19,.63,.21],
         "extras":{"part":"outfit"}},
        {"name":"Cadera izquierda","translation":[-.15,.61,0],"children":[8]},
        {"name":"Pierna izquierda","mesh":0,"translation":[0,-.30,0],"scale":[.20,.60,.24],
         "extras":{"part":"pants"}},
        {"name":"Cadera derecha","translation":[.15,.61,0],"children":[10]},
        {"name":"Pierna derecha","mesh":0,"translation":[0,-.30,0],"scale":[.20,.60,.24],
         "extras":{"part":"pants"}},
    ])
    times = [0.0, .25, .5, .75, 1.0]
    input_acc = accessor(times, components=1, component_type=5126,
                         minimum=[0.0],maximum=[1.0])
    samplers, channels = [], []
    for node, sign in ((3,1),(5,-1),(7,-1),(9,1)):
        angles = [0, sign*.52, 0, -sign*.52, 0]
        rotations = [v for angle in angles for v in _quat_x(angle)]
        output = accessor(rotations, components=4, component_type=5126)
        samplers.append({"input":input_acc,"output":output,"interpolation":"LINEAR"})
        channels.append({"sampler":len(samplers)-1,
                         "target":{"node":node,"path":"rotation"}})
    gltf = {
        "asset":{"version":"2.0","generator":"SKY Metaverso avatar original"},
        "scene":0,"scenes":[{"nodes":[0]}],
        "nodes":nodes,
        "meshes":[{"name":"Malla corporal original","primitives":[{
            "attributes":{"POSITION":pa,"NORMAL":na},"indices":ia,"mode":4}]}],
        "accessors":accessors,
        "bufferViews":views,
        "animations":[{"name":"walk","samplers":samplers,"channels":channels}],
        "buffers":[{"byteLength":len(data)}],
    }
    # glTF 2.0 GLB header + aligned JSON/BIN chunks.
    json_bytes = json.dumps(gltf,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    json_bytes += b' ' * ((-len(json_bytes)) % 4)
    data += b'\x00' * ((-len(data)) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(data)
    return (struct.pack('<4sII',b'glTF',2,total)
            + struct.pack('<I4s',len(json_bytes),b'JSON') + json_bytes
            + struct.pack('<I4s',len(data),b'BIN\x00') + bytes(data))
