"""SKY Internal Roles — centro único, cinco ejecutores internos.

Los roles son capacidades registradas, NO procesos en ejecución permanente.
Mientras la API esté operativa, pueden seleccionarse sin crear nuevos
subagentes de usuario. Los workflows conservan su aprobación explícita.
"""
from __future__ import annotations

from typing import Any
from .sky_workflows import ROLE_ACTION, _valid_step

ROLE_LABELS = {
    'planificador': 'Planificación e investigación estructurada',
    'documentalista': 'Documentos y entregables de oficina',
    'diseñador': 'Diseño visual y experiencias',
    'creador_3d': 'Escenas y proyectos tridimensionales',
    'memoria': 'Notas y memoria autorizada de proyectos',
}

ROUTED_KINDS = {
    'correo': 'sky',
    'casa': 'sky',
    'respuesta': 'sky',
    'accion': 'sky',
}

_ACTION_ROLES = {
    'document': 'documentalista',
    'plan': 'planificador',
    'experience': 'diseñador',
    'world': 'creador_3d',
    'memory': 'memoria',
}


def catalogue() -> dict[str, Any]:
    """La API activa es SKY. Los cinco ejecutores NO hablan independientemente."""
    return {
        'front_agent': 'SKY',
        'single_public_interface': True,
        'internals_are_private': True,
        'internal_roles': [
            {'id': 'sky', 'label': 'SKY CORE', 'kind': 'coordinator',
             'ready_while_service_running': True, 'autonomous_execution': False},
            *[
                {'id': role, 'label': ROLE_LABELS[role], 'kind': 'workflow_executor',
                 'action': action, 'ready_while_service_running': True,
                 'autonomous_execution': False}
                for role, action in ROLE_ACTION.items()
            ],
        ],
        'total_core_roles': 1 + len(ROLE_ACTION),
        'always_listening': False,
        'requires_owner_approval_for_workflows': True,
        'note': ('Los roles están disponibles mientras SKY está ejecutándose; '
                 'no son seis servicios independientes ni capacidades nuevas.'),
    }


def route_result(result: dict[str, Any]) -> str:
    """Clasifica SIN convertir texto externo o sugerencias LLM en permisos."""
    if not isinstance(result, dict):
        return 'sky'
    if result.get('tipo') != 'workflow':
        # Voz, correo, control de Windows y consultas permanecen en SKY CORE.
        return 'sky'
    proposal = result.get('propuesta')
    if not isinstance(proposal, dict):
        return 'sky'
    return _ACTION_ROLES.get(proposal.get('action'), 'sky')


def plan_internal_steps(name: str, steps: list[dict], project_id: str | None = None) -> dict:
    """Previsualización de un plan seguro de hasta 8 pasos, sin ejecutarlo."""
    if not isinstance(name, str) or not 3 <= len(name.strip()) <= 120:
        raise ValueError('El nombre necesita entre 3 y 120 caracteres.')
    if not isinstance(steps, list) or not 1 <= len(steps) <= 8:
        raise ValueError('El plan admite entre 1 y 8 pasos.')
    checked = []
    for step in steps:
        checked.append(_valid_step(step))
    from . import sky_workflows as wf
    wf._validate_tokens(checked, project_id)
    return {
        'central_agent': 'SKY',
        'name': name.strip(),
        'steps': [
            {'role': step['agent'], 'action': step['action'],
             'description': step['task'], 'writes_data': step['action'] != 'plan'}
            for step in checked
        ],
        'requires_owner_approval': True,
        'will_execute_now': False,
        'ready_to_create_workflow': True,
        'message': 'SKY preparó el trabajo interno. No se ejecutará antes de tu aprobación.',
    }
