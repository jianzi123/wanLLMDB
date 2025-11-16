"""
Example: Using external file references with artifacts

This example demonstrates how to use artifact references to track files
stored in external cloud storage (S3, GCS, etc.) without uploading them
to the wanLLMDB storage.

Use cases:
- Track large datasets stored in S3/GCS without duplicating data
- Reference existing cloud storage resources
- Reduce storage costs by avoiding data duplication
- Enable hybrid storage scenarios (some files local, some in cloud)
"""

import wanllmdb
import os
import tempfile

# Initialize wanLLMDB
wandb = wanllmdb

# Example 1: Simple S3 reference
print("\n" + "="*60)
print("Example 1: Adding S3 file reference")
print("="*60)

run = wandb.init(project='reference-examples', name='s3-reference-demo')

# Create artifact with external S3 reference
artifact = wandb.Artifact('training-data', type='dataset')

# Add reference to S3 file
artifact.add_reference(
    uri='s3://my-bucket/datasets/train.csv',
    name='train.csv',
    size=1024000,  # Size in bytes (recommended)
)

# Add another reference
artifact.add_reference(
    uri='s3://my-bucket/datasets/test.csv',
    name='test.csv',
    size=512000,
)

# Log the artifact
run.log_artifact(artifact, aliases=['latest'])
run.finish()

print("\n✓ Artifact with S3 references logged successfully!")


# Example 2: Mixed local files and references
print("\n" + "="*60)
print("Example 2: Mixed local files and external references")
print("="*60)

run = wandb.init(project='reference-examples', name='hybrid-storage')

# Create artifact
artifact = wandb.Artifact('ml-pipeline-data', type='dataset')

# Add some local files
with tempfile.TemporaryDirectory() as tmpdir:
    # Create a local config file
    config_path = os.path.join(tmpdir, 'config.json')
    with open(config_path, 'w') as f:
        f.write('{"model": "resnet50", "epochs": 10}')

    artifact.add_file(config_path, 'config.json')

    # Add reference to large dataset in S3
    artifact.add_reference(
        uri='s3://my-bucket/datasets/imagenet-train.tar.gz',
        name='train_data.tar.gz',
        size=147000000,  # 147 MB
    )

    # Add reference to GCS
    artifact.add_reference(
        uri='gs://my-gcs-bucket/models/pretrained-weights.h5',
        name='pretrained_weights.h5',
        size=98000000,  # 98 MB
    )

    # Log the artifact
    run.log_artifact(artifact, aliases=['latest', 'v1'])

run.finish()

print("\n✓ Hybrid artifact (local + references) logged successfully!")


# Example 3: Using artifacts with references
print("\n" + "="*60)
print("Example 3: Using artifacts with external references")
print("="*60)

run = wandb.init(project='reference-examples', name='use-references')

# Use the artifact we just created
artifact = run.use_artifact('ml-pipeline-data', alias='latest')

# Download the artifact
# Note: External references won't be downloaded, only local files
download_path = artifact.download()

print(f"\n✓ Artifact downloaded to: {download_path}")
print("\nNote: External references (S3/GCS files) are not downloaded.")
print("You can access them using the reference URIs from the artifact metadata.")

run.finish()


# Example 4: References with checksums
print("\n" + "="*60)
print("Example 4: Adding references with checksums")
print("="*60)

run = wandb.init(project='reference-examples', name='references-with-checksums')

artifact = wandb.Artifact('verified-dataset', type='dataset')

# Add reference with checksums for data integrity
artifact.add_reference(
    uri='s3://my-bucket/data/important-dataset.parquet',
    name='important-dataset.parquet',
    size=5000000,
    md5_hash='d41d8cd98f00b204e9800998ecf8427e',  # Example MD5
    sha256_hash='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',  # Example SHA256
)

run.log_artifact(artifact, aliases=['latest', 'verified'])
run.finish()

print("\n✓ Artifact with verified checksums logged!")


# Example 5: HTTPS references
print("\n" + "="*60)
print("Example 5: Public dataset via HTTPS")
print("="*60)

run = wandb.init(project='reference-examples', name='https-reference')

artifact = wandb.Artifact('public-dataset', type='dataset')

# Reference a public dataset hosted on the web
artifact.add_reference(
    uri='https://storage.googleapis.com/download.tensorflow.org/data/iris_training.csv',
    name='iris_training.csv',
    size=2194,  # Actual file size
)

artifact.add_reference(
    uri='https://storage.googleapis.com/download.tensorflow.org/data/iris_test.csv',
    name='iris_test.csv',
    size=573,
)

run.log_artifact(artifact, aliases=['latest'])
run.finish()

print("\n✓ Public HTTPS dataset referenced successfully!")


# Example 6: Production workflow with references
print("\n" + "="*60)
print("Example 6: Production ML workflow")
print("="*60)

# Training script logs model and references training data
run = wandb.init(project='production-ml', name='train-model-v1')

# Create model artifact
model_artifact = wandb.Artifact('sentiment-model', type='model')

with tempfile.TemporaryDirectory() as tmpdir:
    # Save model file locally
    model_path = os.path.join(tmpdir, 'model.pkl')
    with open(model_path, 'wb') as f:
        f.write(b'<model binary data>')

    model_artifact.add_file(model_path, 'model.pkl')

    # Reference the training data in S3 (no need to upload again)
    model_artifact.add_reference(
        uri='s3://company-ml-data/sentiment/train-2024-01.parquet',
        name='training_data.parquet',
        size=500000000,  # 500 MB
    )

    # Log with production alias
    run.log_artifact(model_artifact, aliases=['production', 'latest'])

run.finish()

print("\n✓ Production model logged with training data reference!")


print("\n" + "="*60)
print("Summary: External File References")
print("="*60)
print("""
Key Benefits:
✓ No data duplication - reference existing cloud storage
✓ Reduced storage costs - don't upload large files twice
✓ Faster artifact creation - no upload time for references
✓ Data lineage - track which external data was used
✓ Hybrid storage - mix local files and cloud references

Supported URI Schemes:
- s3://      Amazon S3
- gs://      Google Cloud Storage
- http://    Public HTTP URLs
- https://   Public HTTPS URLs
- file://    Local file system paths

Best Practices:
1. Always provide file size for accurate tracking
2. Include checksums (MD5/SHA256) for data integrity
3. Use descriptive names within the artifact
4. Document external storage access requirements
5. Consider data availability and access permissions
""")
