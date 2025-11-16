"""
Example demonstrating artifact usage with wanLLMDB.

This example shows how to:
1. Create and log a dataset artifact
2. Use an artifact in another run
3. Log a model artifact
4. Work with directories
"""

import os
import tempfile
import wanllmdb as wandb
import pandas as pd
import json


def create_sample_data():
    """Create sample data files for demonstration."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix='wandb_artifact_example_')

    # Create sample CSV file
    train_data = pd.DataFrame({
        'feature1': [1, 2, 3, 4, 5],
        'feature2': [10, 20, 30, 40, 50],
        'label': [0, 1, 0, 1, 0]
    })
    train_path = os.path.join(temp_dir, 'train.csv')
    train_data.to_csv(train_path, index=False)

    # Create sample test data
    test_data = pd.DataFrame({
        'feature1': [6, 7, 8],
        'feature2': [60, 70, 80],
        'label': [1, 0, 1]
    })
    test_path = os.path.join(temp_dir, 'test.csv')
    test_data.to_csv(test_path, index=False)

    # Create sample config file
    config = {
        'features': ['feature1', 'feature2'],
        'target': 'label',
        'train_size': len(train_data),
        'test_size': len(test_data)
    }
    config_path = os.path.join(temp_dir, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # Create images directory
    images_dir = os.path.join(temp_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)

    # Create dummy image files
    for i in range(3):
        img_path = os.path.join(images_dir, f'sample_{i}.txt')
        with open(img_path, 'w') as f:
            f.write(f"Dummy image data {i}")

    return temp_dir, {
        'train': train_path,
        'test': test_path,
        'config': config_path,
        'images_dir': images_dir
    }


def example_1_log_dataset_artifact():
    """Example 1: Log a dataset artifact."""
    print("\n" + "="*60)
    print("Example 1: Logging a Dataset Artifact")
    print("="*60)

    # Create sample data
    temp_dir, paths = create_sample_data()

    # Initialize run
    run = wandb.init(
        project='artifact-examples',
        name='prepare-dataset',
        tags=['dataset', 'preprocessing']
    )

    # Create artifact
    dataset = wandb.Artifact(
        name='sample-dataset',
        type='dataset',
        description='Sample dataset with train/test split',
        metadata={
            'source': 'synthetic',
            'features': ['feature1', 'feature2'],
            'num_classes': 2
        }
    )

    # Add individual files
    dataset.add_file(paths['train'], name='train.csv')
    dataset.add_file(paths['test'], name='test.csv')
    dataset.add_file(paths['config'], name='config.json')

    # Add entire directory
    dataset.add_dir(paths['images_dir'], name='images')

    # Log artifact
    print(f"\nLogging artifact with {dataset.file_count} files "
          f"({dataset.size / 1024:.2f} KB)")

    logged_artifact = run.log_artifact(dataset)

    print(f"Artifact logged: {logged_artifact.name}:{logged_artifact._version}")

    # Finish run
    wandb.finish()

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    return logged_artifact.name, logged_artifact._version


def example_2_use_artifact():
    """Example 2: Use an artifact in another run."""
    print("\n" + "="*60)
    print("Example 2: Using an Artifact")
    print("="*60)

    # Initialize run
    run = wandb.init(
        project='artifact-examples',
        name='train-model',
        tags=['training', 'model']
    )

    # Use artifact by name (gets latest version)
    print("\nUsing artifact...")
    dataset = run.use_artifact('sample-dataset:latest')

    # Download artifact
    data_dir = dataset.download()
    print(f"Dataset downloaded to: {data_dir}")

    # Access files
    train_path = dataset.get_path('train.csv')
    print(f"\nTrain data path: {train_path}")

    # Load and use data
    train_data = pd.read_csv(train_path)
    print(f"Train data shape: {train_data.shape}")
    print(f"Columns: {list(train_data.columns)}")

    # Simulate training
    for epoch in range(3):
        loss = 1.0 / (epoch + 1)  # Simulated loss
        accuracy = 0.5 + (epoch * 0.1)  # Simulated accuracy

        wandb.log({
            'loss': loss,
            'accuracy': accuracy,
            'epoch': epoch
        })

    # Save best metrics
    wandb.summary['best_accuracy'] = 0.75
    wandb.summary['best_loss'] = 0.25

    wandb.finish()


def example_3_log_model_artifact():
    """Example 3: Log a model artifact."""
    print("\n" + "="*60)
    print("Example 3: Logging a Model Artifact")
    print("="*60)

    # Create temporary model file
    temp_dir = tempfile.mkdtemp(prefix='wandb_model_')
    model_path = os.path.join(temp_dir, 'model.pth')

    # Create dummy model file
    model_data = {
        'architecture': 'CNN',
        'layers': [64, 128, 256],
        'weights': [0.1, 0.2, 0.3]  # Dummy weights
    }
    with open(model_path, 'w') as f:
        json.dump(model_data, f)

    # Initialize run
    run = wandb.init(
        project='artifact-examples',
        name='train-final-model',
        tags=['model', 'production']
    )

    # Log training metrics
    wandb.log({'final_loss': 0.15, 'final_accuracy': 0.92})

    # Create model artifact
    model = wandb.Artifact(
        name='sample-model',
        type='model',
        description='Trained CNN model',
        metadata={
            'framework': 'pytorch',
            'architecture': 'CNN',
            'accuracy': 0.92,
            'loss': 0.15
        }
    )

    # Add model file
    model.add_file(model_path, name='model.pth')

    # Add model config
    config_path = os.path.join(temp_dir, 'model_config.json')
    with open(config_path, 'w') as f:
        json.dump({
            'input_size': 784,
            'num_classes': 10,
            'dropout': 0.5
        }, f)
    model.add_file(config_path, name='config.json')

    # Log model artifact
    logged_model = run.log_artifact(model)

    print(f"Model artifact logged: {logged_model.name}:{logged_model._version}")

    wandb.finish()

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def example_4_versioning():
    """Example 4: Artifact versioning."""
    print("\n" + "="*60)
    print("Example 4: Artifact Versioning")
    print("="*60)

    # Version 1
    print("\nCreating version 1...")
    temp_dir = tempfile.mkdtemp()
    v1_path = os.path.join(temp_dir, 'data_v1.txt')
    with open(v1_path, 'w') as f:
        f.write("Version 1 data")

    run = wandb.init(project='artifact-examples', name='data-v1')
    artifact_v1 = wandb.Artifact('versioned-data', type='dataset')
    artifact_v1.add_file(v1_path)
    run.log_artifact(artifact_v1)
    wandb.finish()

    # Version 2
    print("\nCreating version 2...")
    v2_path = os.path.join(temp_dir, 'data_v2.txt')
    with open(v2_path, 'w') as f:
        f.write("Version 2 data with improvements")

    run = wandb.init(project='artifact-examples', name='data-v2')
    artifact_v2 = wandb.Artifact('versioned-data', type='dataset')
    artifact_v2.add_file(v2_path)
    run.log_artifact(artifact_v2)
    wandb.finish()

    # Use specific version
    print("\nUsing specific version...")
    run = wandb.init(project='artifact-examples', name='use-versioned-data')

    # Get latest (v2)
    latest = run.use_artifact('versioned-data:latest')
    print(f"Latest version: {latest._version}")

    # Get specific version
    v1 = run.use_artifact('versioned-data:v1')
    print(f"Specific version: {v1._version}")

    wandb.finish()

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("wanLLMDB Artifact Examples")
    print("="*60)

    try:
        # Example 1: Log dataset
        artifact_name, version = example_1_log_dataset_artifact()

        # Example 2: Use artifact
        example_2_use_artifact()

        # Example 3: Log model
        example_3_log_model_artifact()

        # Example 4: Versioning
        example_4_versioning()

        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60)

        print("\nKey Takeaways:")
        print("1. Artifacts version your datasets, models, and files")
        print("2. Use run.log_artifact() to save artifacts")
        print("3. Use run.use_artifact() to load artifacts")
        print("4. Artifacts are automatically versioned")
        print("5. You can add files or entire directories to artifacts")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
