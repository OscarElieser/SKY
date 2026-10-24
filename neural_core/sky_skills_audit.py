"""Unified SKY skill audit: distinct catalogues, no invented 78 live skills.

Names are grouped by source. A module, SKILL.md, or configured token is not
proof that the feature worked with hardware or an external service.
"""
from __future__ import annotations
from pathlib import Path

TARGET = 78

def audit() -> dict:
    from . import sky_pro_skills, sky_habilidades, sky_skills, sky_skillpack
    external=sky_skillpack.catalogue()
    professional=sky_pro_skills.catalog()
    native=sky_habilidades.catalogo()
    workflows=sky_skills.listar()
    files=sorted(str(p.parent.relative_to(Path(__file__).resolve().parents[1]))
                 for p in (Path(__file__).resolve().parents[1]/".agents"/"skills").glob("*/SKILL.md"))
    builders=native.get("builder",[])
    native_items=native.get("nativas",[])
    groups={
        "external_adapters":external["skills"],
        "professional_guides":professional,
        "native_skills":[{"id":p["id"],"status":"registered_not_runtime_verified",
                          "configured":p.get("integraciones_listas",False)}
                         for p in native_items],
        "step_workflows":[{"id":p.get("id"),"status":"registered_not_runtime_verified"}
                          for p in workflows],
        "skill_builder":[{"id":p.get("id"),"status":p.get("estado","unknown")}
                         for p in builders],
    }
    counts={key:len(items) for key,items in groups.items()}
    total=sum(counts.values())
    missing=[p["id"] for p in external["skills"] if not p["configured"]]
    return {
      "target":TARGET,
      "count_by_independent_catalogue":counts,
      "total_entries_not_deduplicated":total,
      "difference_from_target":TARGET-total,
      "manifest_of_78_distinct_ids_present":False,
      "verified_external_live":0,
      "external_adapter_count":external["adapter_count"],
      "external_config_missing":missing,
      "skill_md_paths":files,
      "groups":groups,
      "interpretation":"78 habilitadas y probadas no certificadas: los catálogos se superponen y no existe manifiesto único de 78 IDs.",
    }
