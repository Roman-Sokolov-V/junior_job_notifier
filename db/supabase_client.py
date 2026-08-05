from supabase import create_client, Client
from supabase import AsyncClient, create_async_client
from project_config import SUPABASE_URL, SUPABASE_SECRET_KEY


def get_supabase_client() -> Client:
    return create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_SECRET_KEY)


async def get_async_supabase_client() -> AsyncClient:
    return await create_async_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
