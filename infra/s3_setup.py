#!/usr/bin/env python3
"""
Provision S3 (versioning, private) and a CloudFront distribution (OAI → S3).
Requires: boto3, AWS credentials with IAM permissions for S3 and CloudFront.

This is a reference script for portfolio demos — tune origins, price class, and
TLS certificates for production.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

import boto3
from botocore.exceptions import ClientError


def ensure_bucket(s3, name: str, region: str) -> None:
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=name)
        else:
            s3.create_bucket(
                Bucket=name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code != "BucketAlreadyOwnedByYou":
            raise
    s3.put_bucket_versioning(Bucket=name, VersioningConfiguration={"Status": "Enabled"})
    s3.put_public_access_block(
        Bucket=name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )


def origin_access_identity(cf, caller_ref: str) -> str:
    resp = cf.create_cloud_front_origin_access_identity(
        CloudFrontOriginAccessIdentityConfig={
            "CallerReference": caller_ref,
            "Comment": "StreamVault OAI",
        }
    )
    return resp["CloudFrontOriginAccessIdentity"]["Id"]


def bucket_policy_for_oai(bucket: str, oai_canonical_user: str) -> str:
    doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontOAI",
                "Effect": "Allow",
                "Principal": {"CanonicalUser": oai_canonical_user},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*",
            }
        ],
    }
    return json.dumps(doc)


def create_distribution(
    cf,
    bucket: str,
    region: str,
    oai_id: str,
    caller_ref: str,
    price_class: str = "PriceClass_100",
) -> dict:
    domain = f"{bucket}.s3.{region}.amazonaws.com"
    resp = cf.create_distribution(
        DistributionConfig={
            "CallerReference": caller_ref,
            "Comment": "StreamVault segments",
            "Enabled": True,
            "Origins": {
                "Quantity": 1,
                "Items": [
                    {
                        "Id": "S3-StreamVault",
                        "DomainName": domain,
                        "S3OriginConfig": {
                            "OriginAccessIdentity": f"origin-access-identity/cloudfront/{oai_id}"
                        },
                    }
                ],
            },
            "DefaultCacheBehavior": {
                "TargetOriginId": "S3-StreamVault",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 2,
                    "Items": ["GET", "HEAD"],
                    "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                },
                "ForwardedValues": {
                    "QueryString": True,
                    "Cookies": {"Forward": "none"},
                },
                "TrustedSigners": {"Enabled": False, "Quantity": 0},
                "MinTTL": 0,
                "DefaultTTL": 86400,
                "MaxTTL": 31536000,
                "Compress": True,
            },
            "PriceClass": price_class,
        }
    )
    return resp["Distribution"]


def main() -> int:
    p = argparse.ArgumentParser(description="Create StreamVault S3 + CloudFront")
    p.add_argument("--bucket", required=True, help="Globally unique bucket name")
    p.add_argument("--region", default="ca-central-1")
    p.add_argument("--skip-cloudfront", action="store_true")
    args = p.parse_args()

    session = boto3.session.Session(region_name=args.region)
    s3 = session.client("s3")

    ensure_bucket(s3, args.bucket, args.region)
    print(f"Bucket ready: {args.bucket} (versioning on, public access blocked)")

    if args.skip_cloudfront:
        print("Skipping CloudFront (--skip-cloudfront).")
        return 0

    cf = session.client("cloudfront")
    ref = f"streamvault-{uuid.uuid4().hex[:12]}"
    oai_id = origin_access_identity(cf, ref + "-oai")

    oai_meta = cf.get_cloud_front_origin_access_identity(Id=oai_id)
    s3_canonical = oai_meta["CloudFrontOriginAccessIdentity"]["S3CanonicalUserId"]

    policy = bucket_policy_for_oai(args.bucket, s3_canonical)
    s3.put_bucket_policy(Bucket=args.bucket, Policy=policy)

    dist = create_distribution(cf, args.bucket, args.region, oai_id, ref + "-dist")
    domain = dist["DomainName"]
    print(f"CloudFront distribution creating: {domain}")
    print("Status: InProgress (can take 10–20 minutes). Poll in AWS console or CLI.")

    did = dist["Id"]
    for _ in range(36):
        d = cf.get_distribution(Id=did)["Distribution"]
        if d["Status"] == "Deployed":
            print(f"Deployed: https://{d['DomainName']}")
            break
        time.sleep(10)
    else:
        print("Still deploying; check CloudFront console for status.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
