import boto3
import os

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )

BUCKET = os.environ.get("R2_BUCKET_NAME", "jz-pipeline")

def upload_file(local_path: str, r2_key: str):
    client = get_r2_client()
    client.upload_file(local_path, BUCKET, r2_key)
    print(f"Uploaded: {local_path} → r2://{BUCKET}/{r2_key}")

def download_file(r2_key: str, local_path: str):
    client = get_r2_client()
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    client.download_file(BUCKET, r2_key, local_path)

def list_files(prefix: str):
    client = get_r2_client()
    paginator = client.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys

def sync_from_r2(r2_prefix: str, local_dir: str):
    files = list_files(r2_prefix)
    if not files:
        print(f"No files found in R2 at {r2_prefix}")
        return 0
    os.makedirs(local_dir, exist_ok=True)
    for key in files:
        filename = key.split("/")[-1]
        local_path = os.path.join(local_dir, filename)
        if not os.path.exists(local_path):
            download_file(key, local_path)
    print(f"Synced {len(files)} files from r2://{BUCKET}/{r2_prefix} → {local_dir}")
    return len(files)