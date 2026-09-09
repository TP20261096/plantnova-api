from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def anon_client() -> Client:
    
    return create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )


def user_client(token: str) -> Client:
    
    cliente = create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )
    cliente.postgrest.auth(token)
    return cliente


@lru_cache
def service_client() -> Client:
    
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )