# StreamVault infrastructure helpers

Python scripts use **boto3** with your AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`).

## S3 + CloudFront bootstrap

```bash
pip install boto3
python s3_setup.py --bucket your-unique-bucket-name --region ca-central-1
```

Use `--skip-cloudfront` if you only want the bucket.

After CloudFront deploys, set `CLOUDFRONT_DOMAIN` in `.env` to the distribution domain (without `https://`). Create a CloudFront **key pair** in the AWS console, download the PEM, and set `CLOUDFRONT_KEY_PAIR_ID` and `CLOUDFRONT_PRIVATE_KEY_PATH` so the API can sign URLs.

## Cache invalidation

```bash
python cloudfront_invalidate.py --distribution-id E123ABCDEFG /content-id/*
```

## IAM (summary)

Your user or role needs permissions such as `s3:CreateBucket`, `s3:PutBucket*`, `cloudfront:CreateDistribution`, `cloudfront:CreateInvalidation`, and related read APIs. Tighten policies for production accounts.
