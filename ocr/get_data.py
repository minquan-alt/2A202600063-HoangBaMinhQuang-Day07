import json
from google.cloud import storage

BUCKET_NAME = "quang-ocr-bucket-123"
PREFIX = "output/"

client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

blobs = list(bucket.list_blobs(prefix=PREFIX))

# sort đúng thứ tự trang
blobs = sorted(blobs, key=lambda x: x.name)

full_text = ""

for blob in blobs:
    if blob.name.endswith(".json"):
        data = json.loads(blob.download_as_text())

        for res in data.get("responses", []):
            if "fullTextAnnotation" in res:
                full_text += res["fullTextAnnotation"]["text"] + "\n"

with open("output.txt", "w", encoding="utf-8") as f:
    f.write(full_text)

print("✅ Saved to output.txt")