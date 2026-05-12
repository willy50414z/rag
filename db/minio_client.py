# -*- coding: utf-8 -*-
"""
MinIO upload layer for typical-characteristic chart images.

Public API:
    build_minio_client(endpoint_raw, access_key, secret_key) -> Minio
    upload_charts(client, bucket, charts) -> None
"""

import io

from minio import Minio


def _minio_endpoint(raw: str) -> tuple[str, bool]:
    """Strip scheme from endpoint, return (host:port, is_secure)."""
    if raw.startswith("https://"):
        return raw[len("https://"):], True
    if raw.startswith("http://"):
        return raw[len("http://"):], False
    return raw, False


def build_minio_client(endpoint_raw: str, access_key: str, secret_key: str) -> Minio:
    """Construct a Minio client from a raw endpoint string (with or without scheme)."""
    host, secure = _minio_endpoint(endpoint_raw)
    return Minio(host, access_key=access_key, secret_key=secret_key, secure=secure)


def upload_charts(client: Minio, bucket: str, charts: list[dict]) -> None:
    """Upload chart PNGs to MinIO. Each record MUST contain `image_bytes` and `minio_key`."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        print(f"  Created MinIO bucket '{bucket}'")
    for r in charts:
        data = r["image_bytes"]
        client.put_object(
            bucket,
            r["minio_key"],
            io.BytesIO(data),
            length=len(data),
            content_type="image/png",
        )
    print(f"  Uploaded {len(charts)} chart(s) → s3://{bucket}/")
