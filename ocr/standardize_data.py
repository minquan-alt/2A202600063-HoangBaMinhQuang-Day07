from google.cloud import vision

client = vision.ImageAnnotatorClient()

gcs_source_uri = "gs://quang-ocr-bucket-123/input.pdf"
gcs_destination_uri = "gs://quang-ocr-bucket-123/output/"

feature = vision.Feature(
    type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION
)

input_config = vision.InputConfig(
    gcs_source=vision.GcsSource(uri=gcs_source_uri),
    mime_type="application/pdf"
)

output_config = vision.OutputConfig(
    gcs_destination=vision.GcsDestination(uri=gcs_destination_uri),
    batch_size=10
)

request = vision.AsyncAnnotateFileRequest(
    features=[feature],
    input_config=input_config,
    output_config=output_config
)

operation = client.async_batch_annotate_files(requests=[request])

print("⏳ OCR running...")
operation.result(timeout=600)

print("✅ DONE")