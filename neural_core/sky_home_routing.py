"""Conservative, opt-in routing for the SKY Home Server.

This module selects a text provider; it never sends prompts, opens ports,
executes tools or changes the existing SKY provider defaults. The caller must
supply explicit per-request consent before any cloud provider is selected.
"""
from __future__ import annotations

from dataclasses import dataclass

CLOUD_ORDER = ("gemini", "openai", "anthropic", "mistral", "groq", "deepseek")
ALLOWED = ("auto", "ollama", *CLOUD_ORDER)


@dataclass(frozen=True)
class Route:
    provider: str | None
    remote: bool
    reason: str


def choose_home_route(
    *,
    requested: str = "auto",
    configured_cloud: tuple[str, ...] | list[str] = (),
    local_available: bool = False,
    cloud_consent: bool = False,
    private_data: bool = True,
    private_cloud_consent: bool = False,
    local_only: bool = False,
) -> Route:
    """Select a provider without contacting it or silently changing services.

    A cloud key alone is NOT consent. Private data is the safe default.
    This pure selector never retries. The API may use a disclosed LOCAL-only
    backup for an authorized AUTO cloud request; never another cloud service.
    """
    if requested not in ALLOWED:
        raise ValueError("Proveedor no permitido para SKY Home.")
    configured = set(configured_cloud).intersection(CLOUD_ORDER)
    can_cloud = cloud_consent and not local_only and (
        not private_data or private_cloud_consent
    )

    if requested == "ollama":
        return (Route("ollama", False, "Modelo local disponible") if local_available
                else Route(None, False, "Ollama local no está disponible"))

    if requested in CLOUD_ORDER:
        if local_only:
            return Route(None, False, "SKY_LOCAL_ONLY prohíbe enviar datos a la nube")
        if not cloud_consent:
            return Route(None, False, "Falta autorización de nube para esta solicitud")
        if private_data and not private_cloud_consent:
            return Route(None, False, "Falta autorización específica para datos privados")
        if requested not in configured:
            return Route(None, False, "Proveedor solicitado sin configuración")
        return Route(requested, True, "Proveedor remoto autorizado expresamente")

    # Auto: cloud-first on an 8 GB home server, but ONLY with consent.
    if can_cloud:
        for name in CLOUD_ORDER:
            if name in configured:
                return Route(name, True, "Nube autorizada; se evita cargar un modelo grande")
    if local_available:
        return Route("ollama", False, "Respaldo local; no se envían datos a la nube")
    if local_only:
        return Route(None, False, "Modo local activo sin modelo local disponible")
    if not cloud_consent:
        return Route(None, False, "Sin modelo local y sin autorización de nube")
    if private_data and not private_cloud_consent:
        return Route(None, False, "Sin modelo local; los datos privados no están autorizados para la nube")
    return Route(None, False, "No hay un proveedor configurado y disponible")
