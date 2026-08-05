from storage3.exceptions import StorageApiError
from supabase import AsyncClient, Client

from project_config import ALLOWED_MIME_TYPES


def get_or_create_bucket(
    supabase: Client,
    bucket_name: str = "CV",
    file_types: list[str] | None = None,
    max_size: int = 2 * 1024 * 1024,
):
    """Retrieves the details of an existing Storage bucket
    if the bucket doesn't exist, it creates it.
    """
    try:
        return supabase.storage.get_bucket(bucket_name)

    except StorageApiError as e:
        if "Bucket not found" in str(e) or e.status_code == 404:
            if file_types is None:
                file_types = ALLOWED_MIME_TYPES
            return supabase.storage.create_bucket(
                id=bucket_name,
                options={
                    "public": False,
                    "allowed_mime_types": file_types,
                    "file_size_limit": max_size,
                },
            )
        raise e


def get_bucket(supabase: Client, bucket_name: str) -> dict:
    return supabase.storage.get_bucket(bucket_name)


async def get_file_url(a_supabase: AsyncClient, full_path: str) -> str | None:
    """
    Creates a signed URL for a file.
    Use a signed URL to share a file for a fixed amount of time.
    """
    clean_path = full_path.strip().strip("'\"")
    bucket, storage_path = clean_path.split("/", maxsplit=1)
    res = await a_supabase.storage.from_(bucket).create_signed_url(storage_path, 300)
    return res["signedUrl"]


async def download_file_bytes(a_supabase: AsyncClient, full_path: str) -> bytes:
    """Downloads a file from Supabase Storage as bytes."""
    clean_path = full_path.strip().strip("'\"")
    bucket, storage_path = clean_path.split("/", maxsplit=1)
    res = await a_supabase.storage.from_(bucket).download(storage_path)
    return res
