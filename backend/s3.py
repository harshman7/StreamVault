from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _client() -> BaseClient:
    kwargs: dict = {
        "region_name": os.environ.get("AWS_REGION", "ca-central-1"),
        "config": Config(signature_version="s3v4"),
    }
    endpoint = os.environ.get("S3_ENDPOINT_URL") or None
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


def bucket_name() -> str:
    name = os.environ.get("S3_BUCKET_NAME", "")
    if not name:
        raise RuntimeError("S3_BUCKET_NAME is not configured")
    return name


def get_object_bytes(s3_key: str) -> bytes:
    resp = _client().get_object(Bucket=bucket_name(), Key=s3_key)
    return resp["Body"].read()


def upload_file(local_path: str, s3_key: str, content_type: str | None = None) -> None:
    extra: dict = {}
    if content_type:
        extra["ContentType"] = content_type
    _client().upload_file(local_path, bucket_name(), s3_key, ExtraArgs=extra or None)


def _cloudfront_config() -> tuple[str, str, str] | None:
    domain = (os.environ.get("CLOUDFRONT_DOMAIN") or "").strip().rstrip("/")
    key_pair_id = (os.environ.get("CLOUDFRONT_KEY_PAIR_ID") or "").strip()
    key_path = (os.environ.get("CLOUDFRONT_PRIVATE_KEY_PATH") or "").strip()
    if not domain or not key_pair_id or not key_path:
        return None
    return domain, key_pair_id, key_path


def _rsa_signer(private_key_pem: bytes):
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    def sign(message: bytes) -> bytes:
        return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())

    return sign


def get_signed_cloudfront_url(s3_key: str, expiry_seconds: int = 3600) -> str:
    cfg = _cloudfront_config()
    if not cfg:
        raise RuntimeError("CloudFront signing is not fully configured")

    domain, key_pair_id, key_path = cfg
    pem = Path(key_path).expanduser().read_bytes()
    signer = _rsa_signer(pem)

    key_clean = s3_key.lstrip("/")
    resource = f"https://{domain}/{quote(key_clean, safe='/')}"
    expire = datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)

    from botocore.signers import CloudFrontSigner

    cf = CloudFrontSigner(key_pair_id, signer)
    return cf.generate_presigned_url(resource, date_less_than=expire)


def cloudfront_enabled() -> bool:
    return _cloudfront_config() is not None
