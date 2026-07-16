"""File storage abstraction. The brief requires S3-compatible object
storage for attachments, never local disk, in production.

This sandbox has no real S3/R2/MinIO credentials to exercise, so
LocalDiskStorage exists purely as a dev fallback -- it is deliberately
the ONLY backend that can actually run here. Configure S3_BUCKET (plus
S3_ENDPOINT_URL for non-AWS S3-compatible providers, S3_ACCESS_KEY_ID,
S3_SECRET_ACCESS_KEY) in any real deployment and S3Storage takes over
automatically; no application code changes needed.
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageBackend:
    def save(self, key: str, file_obj, content_type: str | None = None) -> None:
        raise NotImplementedError

    def open_stream(self, key: str):
        """Returns a readable binary stream for the stored object."""
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError


class LocalDiskStorage(StorageBackend):
    """Dev-only fallback. Never use in production -- see module docstring."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError("Invalid storage key")
        return path

    def save(self, key: str, file_obj, content_type: str | None = None) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(file_obj.read())

    def open_stream(self, key: str):
        return open(self._path(key), "rb")

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()


class S3Storage(StorageBackend):
    """Real S3-compatible backend (AWS S3, MinIO, R2, etc). Untested in
    this sandbox for lack of credentials, but this is the code path any
    real deployment should run through."""

    def __init__(self, bucket: str, endpoint_url: str | None, access_key: str | None,
                 secret_key: str | None, region: str | None):
        import boto3

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def save(self, key: str, file_obj, content_type: str | None = None) -> None:
        extra_args = {"ContentType": content_type} if content_type else {}
        self.client.upload_fileobj(file_obj, self.bucket, key, ExtraArgs=extra_args)

    def open_stream(self, key: str):
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"]

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


_backend = None


def get_storage_backend() -> StorageBackend:
    global _backend
    if _backend is not None:
        return _backend

    bucket = os.environ.get("S3_BUCKET")
    if bucket:
        _backend = S3Storage(
            bucket=bucket,
            endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
            access_key=os.environ.get("S3_ACCESS_KEY_ID"),
            secret_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
            region=os.environ.get("S3_REGION"),
        )
    else:
        logger.warning(
            "S3_BUCKET not set -- falling back to local-disk file storage. "
            "This is a dev-only path; configure S3_BUCKET before deploying."
        )
        _backend = LocalDiskStorage(os.environ.get("LOCAL_STORAGE_ROOT", "./storage"))
    return _backend
