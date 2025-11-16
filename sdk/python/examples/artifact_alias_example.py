"""
Artifact Alias Example

This example demonstrates how to use artifact aliases for version management.
Aliases allow you to tag artifact versions with human-readable names like
'latest', 'production', 'stable', etc.
"""

import wanllmdb
import time
import os

# Example 1: Create dataset with 'latest' alias
print("=" * 60)
print("Example 1: Create dataset with 'latest' alias")
print("=" * 60)

run1 = wanllmdb.init(project="artifact-aliases-demo", name="prepare-data-v1")

# Create training dataset
dataset = wanllmdb.Artifact('training-dataset', type='dataset', description='Training data v1')

# For demo purposes, create a dummy file
with open('/tmp/data_v1.csv', 'w') as f:
    f.write('id,feature1,feature2,label\n')
    f.write('1,0.5,0.3,1\n')
    f.write('2,0.8,0.1,0\n')

dataset.add_file('/tmp/data_v1.csv', 'train.csv')

# Log with 'latest' and 'v1' aliases
run1.log_artifact(dataset, aliases=['latest', 'v1'])
run1.finish()

print("\n✓ Dataset logged with aliases: 'latest', 'v1'\n")
time.sleep(1)


# Example 2: Update dataset and move 'latest' alias
print("=" * 60)
print("Example 2: Update dataset and move 'latest' alias")
print("=" * 60)

run2 = wanllmdb.init(project="artifact-aliases-demo", name="prepare-data-v2")

# Create improved dataset
dataset_v2 = wanllmdb.Artifact('training-dataset', type='dataset', description='Training data v2')

# Create v2 file with more data
with open('/tmp/data_v2.csv', 'w') as f:
    f.write('id,feature1,feature2,label\n')
    f.write('1,0.5,0.3,1\n')
    f.write('2,0.8,0.1,0\n')
    f.write('3,0.6,0.7,1\n')
    f.write('4,0.2,0.9,0\n')

dataset_v2.add_file('/tmp/data_v2.csv', 'train.csv')

# Log with 'latest' and 'v2' aliases
# The 'latest' alias will move from v1 to v2
run2.log_artifact(dataset_v2, aliases=['latest', 'v2'])
run2.finish()

print("\n✓ Dataset v2 logged, 'latest' alias moved to v2\n")
time.sleep(1)


# Example 3: Use dataset by alias
print("=" * 60)
print("Example 3: Use dataset by alias")
print("=" * 60)

run3 = wanllmdb.init(project="artifact-aliases-demo", name="train-model")

# Get dataset using 'latest' alias (will get v2)
dataset_latest = run3.use_artifact('training-dataset', alias='latest')
data_dir = dataset_latest.download()

print(f"\n✓ Downloaded dataset from alias 'latest'")
print(f"  Path: {data_dir}")

# Read the data
with open(os.path.join(data_dir, 'train.csv'), 'r') as f:
    lines = f.readlines()
    print(f"  Rows: {len(lines) - 1}")  # Exclude header

run3.finish()
time.sleep(1)


# Example 4: Use specific version by alias
print("\n" + "=" * 60)
print("Example 4: Use specific version by alias 'v1'")
print("=" * 60)

run4 = wanllmdb.init(project="artifact-aliases-demo", name="compare-datasets")

# Get v1 using alias
dataset_v1 = run4.use_artifact('training-dataset', alias='v1')
data_dir_v1 = dataset_v1.download()

print(f"\n✓ Downloaded dataset from alias 'v1'")
print(f"  Path: {data_dir_v1}")

with open(os.path.join(data_dir_v1, 'train.csv'), 'r') as f:
    lines = f.readlines()
    print(f"  Rows: {len(lines) - 1}")

run4.finish()


# Example 5: Production workflow with aliases
print("\n" + "=" * 60)
print("Example 5: Production workflow")
print("=" * 60)

run5 = wanllmdb.init(project="artifact-aliases-demo", name="deploy-model")

# Create model
model_artifact = wanllmdb.Artifact('my-classifier', type='model', description='Production model')

# Create dummy model file
with open('/tmp/model.pkl', 'w') as f:
    f.write('# Model weights here')

model_artifact.add_file('/tmp/model.pkl')

# Log with production aliases
run5.log_artifact(model_artifact, aliases=['production', 'stable', 'v1.0.0'])

print("\n✓ Model deployed with aliases: 'production', 'stable', 'v1.0.0'")

run5.finish()


# Example 6: Use production model
print("\n" + "=" * 60)
print("Example 6: Use production model")
print("=" * 60)

run6 = wanllmdb.init(project="artifact-aliases-demo", name="inference")

# Always use the production model
prod_model = run6.use_artifact('my-classifier', alias='production')
model_dir = prod_model.download()

print(f"\n✓ Downloaded production model")
print(f"  Path: {model_dir}")

run6.finish()


# Cleanup
print("\n" + "=" * 60)
print("Cleaning up temporary files...")
print("=" * 60)

os.remove('/tmp/data_v1.csv')
os.remove('/tmp/data_v2.csv')
os.remove('/tmp/model.pkl')

print("\n✓ Cleanup complete!")
print("\n" + "=" * 60)
print("Summary:")
print("=" * 60)
print("Aliases allow you to:")
print("  • Tag versions with human-readable names")
print("  • Move aliases between versions (e.g., update 'latest')")
print("  • Access artifacts without knowing version numbers")
print("  • Implement staging workflows (dev/staging/production)")
print("  • Simplify artifact version management")
print("=" * 60)
