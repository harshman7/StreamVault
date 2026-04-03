#!/usr/bin/env python3
"""Create a CloudFront invalidation for one or more path patterns."""
from __future__ import annotations

import argparse
import sys
import uuid

import boto3
from botocore.exceptions import ClientError


def main() -> int:
    p = argparse.ArgumentParser(description="Invalidate CloudFront paths")
    p.add_argument("--distribution-id", required=True, help="CloudFront distribution ID (e.g. E123...)")
    p.add_argument(
        "paths",
        nargs="+",
        help="Paths to invalidate (e.g. /my-content-id/*)",
    )
    args = p.parse_args()

    cf = boto3.client("cloudfront")
    try:
        resp = cf.create_invalidation(
            DistributionId=args.distribution_id,
            InvalidationBatch={
                "Paths": {"Quantity": len(args.paths), "Items": args.paths},
                "CallerReference": str(uuid.uuid4()),
            },
        )
    except ClientError as e:
        print(e, file=sys.stderr)
        return 1

    inv = resp["Invalidation"]
    print(f"Invalidation {inv['Id']} status={inv['Status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
