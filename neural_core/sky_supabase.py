"""SKY Supabase Cloud Integration: Base de datos Postgres y Autenticación en la nube.

Permite autenticar usuarios con Supabase Auth (email/password) y sincronizar
proyectos, perfiles y documentos en PostgreSQL en la nube de Supabase.
"""
from __future__ import annotations
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')


def get_config() -> tuple[str, str]:
    url = os.getenv('SUPABASE_URL', '').strip()
    key = (os.getenv('SUPABASE_ANON_KEY') or os.getenv('BAQUEANO_SUPABASE_PUBLISHABLE_KEY', '')).strip()
    return url, key


def is_configured() -> bool:
    url, key = get_config()
    return bool(url and key and url.startswith('https://'))


def get_client():
    url, key = get_config()
    if not url or not key:
        return None
    try:
        from supabase import create_client, Client
        return create_client(url, key)
    except Exception as exc:
        raise RuntimeError(f"Error inicializando cliente de Supabase: {exc}")


SUPER_ADMIN_EMAILS = {
    'oscarelieser.informatica.inatec@gmail.com',
    os.getenv('SUPER_ADMIN_EMAIL', '').strip().lower()
} - {''}


def is_super_admin(email: str) -> bool:
    if not email:
        return False
    return email.strip().lower() in SUPER_ADMIN_EMAILS


def sign_up(email: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Registra un nuevo usuario en Supabase Auth con rol de superadministrador si corresponde."""
    client = get_client()
    if not client:
        raise RuntimeError("Supabase no está configurado. Revisa SUPABASE_URL y SUPABASE_ANON_KEY en .env")
    email_clean = email.strip().lower()
    is_admin = is_super_admin(email_clean)
    meta = dict(metadata or {})
    if is_admin:
        meta["role"] = "superadmin"
        meta["is_super_admin"] = True
    res = client.auth.sign_up({
        "email": email_clean,
        "password": password,
        "options": {"data": meta}
    })
    user = res.user
    session = res.session
    return {
        "user_id": user.id if user else None,
        "email": email_clean,
        "session": bool(session),
        "access_token": session.access_token if session else None,
        "is_super_admin": is_admin,
        "role": "superadmin" if is_admin else "user"
    }


def sign_in(email: str, password: str) -> Dict[str, Any]:
    """Inicia sesión con correo y contraseña en Supabase Auth y verifica permisos de superadministrador."""
    client = get_client()
    if not client:
        raise RuntimeError("Supabase no está configurado. Revisa SUPABASE_URL y SUPABASE_ANON_KEY en .env")
    email_clean = email.strip().lower()
    res = client.auth.sign_in_with_password({
        "email": email_clean,
        "password": password
    })
    user = res.user
    session = res.session
    is_admin = is_super_admin(email_clean)
    return {
        "user_id": user.id if user else None,
        "email": email_clean,
        "access_token": session.access_token if session else None,
        "user_metadata": user.user_metadata if user else {},
        "is_super_admin": is_admin,
        "role": "superadmin" if is_admin else "user"
    }


def sign_out(access_token: Optional[str] = None) -> bool:
    """Cierra la sesión del usuario."""
    client = get_client()
    if not client:
        return False
    try:
        client.auth.sign_out()
        return True
    except Exception:
        return False


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Valida un token JWT de Supabase y obtiene los datos del usuario."""
    client = get_client()
    if not client:
        return None
    try:
        user_res = client.auth.get_user(token)
        if user_res and user_res.user:
            u = user_res.user
            return {"user_id": u.id, "email": u.email, "metadata": u.user_metadata}
    except Exception:
        return None
    return None


def fetch_table(table_name: str, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Consulta registros de una tabla en Supabase PostgreSQL."""
    client = get_client()
    if not client:
        return []
    query = client.table(table_name).select("*")
    if user_id:
        query = query.eq("user_id", user_id)
    res = query.limit(limit).execute()
    return res.data or []


def insert_record(table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Inserta un registro en una tabla de Supabase."""
    client = get_client()
    if not client:
        raise RuntimeError("Supabase no configurado")
    res = client.table(table_name).insert(record).execute()
    return res.data[0] if res.data else {}
