"""
Example demonstrating wandb.save() for saving run files.

This shows how to save individual files and glob patterns to a run.
Run files are directly associated with a specific run (unlike artifacts which are versioned).
"""

import wanllmdb as wandb
import os
import json


def example_1_save_single_file():
    """Save a single file to the run."""
    print("\n=== Example 1: Save Single File ===\n")

    run = wandb.init(project="file-management-demo", name="save-single-file")

    # Create a sample file
    with open("model_weights.pkl", "w") as f:
        f.write("Mock model weights data...")

    # Save the file to the run
    wandb.save("model_weights.pkl")

    # Clean up
    os.remove("model_weights.pkl")

    wandb.finish()
    print("\n✓ Example 1 completed")


def example_2_save_multiple_files():
    """Save multiple files using glob patterns."""
    print("\n=== Example 2: Save Multiple Files with Glob ===\n")

    run = wandb.init(project="file-management-demo", name="save-multiple-files")

    # Create sample log files
    os.makedirs("logs", exist_ok=True)
    for i in range(3):
        with open(f"logs/training_{i}.txt", "w") as f:
            f.write(f"Training log {i}\nLoss: {0.5 - i * 0.1}\nAccuracy: {0.8 + i * 0.05}")

    # Save all log files
    wandb.save("logs/*.txt")

    # Clean up
    for i in range(3):
        os.remove(f"logs/training_{i}.txt")
    os.rmdir("logs")

    wandb.finish()
    print("\n✓ Example 2 completed")


def example_3_save_recursive():
    """Save files recursively with nested directories."""
    print("\n=== Example 3: Save Files Recursively ===\n")

    run = wandb.init(project="file-management-demo", name="save-recursive")

    # Create nested directory structure
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    # Create sample CSV files
    with open("data/raw/train.csv", "w") as f:
        f.write("id,feature1,feature2,label\n1,0.5,0.2,0\n2,0.3,0.8,1\n")

    with open("data/processed/train_normalized.csv", "w") as f:
        f.write("id,feature1,feature2,label\n1,0.5,0.2,0\n2,0.3,0.8,1\n")

    # Save all CSV files recursively
    wandb.save("data/**/*.csv")

    # Clean up
    os.remove("data/raw/train.csv")
    os.remove("data/processed/train_normalized.csv")
    os.rmdir("data/raw")
    os.rmdir("data/processed")
    os.rmdir("data")

    wandb.finish()
    print("\n✓ Example 3 completed")


def example_4_save_config_and_results():
    """Save configuration and results files."""
    print("\n=== Example 4: Save Config and Results ===\n")

    run = wandb.init(
        project="file-management-demo",
        name="save-config-results",
        config={"learning_rate": 0.001, "batch_size": 32}
    )

    # Save experiment configuration to file
    config_data = {
        "model": "ResNet50",
        "optimizer": "Adam",
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 10
    }

    with open("experiment_config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    wandb.save("experiment_config.json")

    # Simulate training and save results
    results = {
        "final_loss": 0.234,
        "final_accuracy": 0.956,
        "best_epoch": 8,
        "training_time_seconds": 1823
    }

    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)

    wandb.save("results.json")

    # Clean up
    os.remove("experiment_config.json")
    os.remove("results.json")

    wandb.finish()
    print("\n✓ Example 4 completed")


def example_5_save_with_base_path():
    """Save files with a specific base path."""
    print("\n=== Example 5: Save with Base Path ===\n")

    run = wandb.init(project="file-management-demo", name="save-with-base-path")

    # Create directory structure
    os.makedirs("outputs/models", exist_ok=True)

    # Create files
    with open("outputs/models/checkpoint_001.pkl", "w") as f:
        f.write("Model checkpoint 1")

    with open("outputs/models/checkpoint_002.pkl", "w") as f:
        f.write("Model checkpoint 2")

    # Save files with base_path to preserve directory structure
    wandb.save("models/*.pkl", base_path="outputs")

    # Clean up
    os.remove("outputs/models/checkpoint_001.pkl")
    os.remove("outputs/models/checkpoint_002.pkl")
    os.rmdir("outputs/models")
    os.rmdir("outputs")

    wandb.finish()
    print("\n✓ Example 5 completed")


if __name__ == "__main__":
    print("=" * 60)
    print("wandb.save() Examples")
    print("=" * 60)

    print("\nThese examples demonstrate different ways to save files to runs:")
    print("1. Save single file")
    print("2. Save multiple files with glob patterns")
    print("3. Save files recursively")
    print("4. Save configuration and results")
    print("5. Save with custom base path")

    # Run all examples
    example_1_save_single_file()
    example_2_save_multiple_files()
    example_3_save_recursive()
    example_4_save_config_and_results()
    example_5_save_with_base_path()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
