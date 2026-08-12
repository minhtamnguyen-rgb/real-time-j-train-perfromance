import boto3
import os
from dotenv import load_dotenv

load_dotenv()

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
    print(f"Downloaded: r2://{BUCKET}/{r2_key} → {local_path}")

def list_files(prefix: str):
    client = get_r2_client()
    response = client.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    return [obj["Key"] for obj in response.get("Contents", [])]
