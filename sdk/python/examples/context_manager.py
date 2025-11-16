"""
Example: Using wanLLMDB with context manager for automatic cleanup.
"""

import random
import time
import wanllmdb as wandb


def train_with_context_manager():
    """Example using context manager."""

    # Using context manager ensures run is finished even if error occurs
    with wandb.init(
        project="context-manager-example",
        name="auto-cleanup",
        config={"epochs": 10},
    ) as run:
        print(f"Run started: {run.name}")

        for epoch in range(10):
            # Simulate training
            loss = 2.0 - epoch * 0.15 + random.random() * 0.1
            accuracy = epoch * 0.08 + random.random() * 0.05

            wandb.log({
                "loss": loss,
                "accuracy": accuracy,
            })

            print(f"Epoch {epoch + 1}: loss={loss:.4f}, accuracy={accuracy:.4f}")
            time.sleep(0.1)

        # Run is automatically finished when exiting context


def train_with_error_handling():
    """Example with error handling."""

    run = wandb.init(
        project="error-handling-example",
        name="with-errors",
        config={"epochs": 10},
    )

    try:
        for epoch in range(10):
            # Simulate training
            loss = 2.0 - epoch * 0.15 + random.random() * 0.1

            # Simulate random error
            if random.random() < 0.1:
                raise ValueError("Simulated training error!")

            wandb.log({"loss": loss})
            print(f"Epoch {epoch + 1}: loss={loss:.4f}")
            time.sleep(0.1)

        # Success
        wandb.finish(exit_code=0)
        print("Training completed successfully!")

    except Exception as e:
        print(f"Error occurred: {e}")
        # Mark run as failed
        wandb.finish(exit_code=1)


def multiple_runs():
    """Example running multiple experiments."""

    configs = [
        {"lr": 0.001, "bs": 32},
        {"lr": 0.01, "bs": 64},
        {"lr": 0.0001, "bs": 16},
    ]

    for i, config in enumerate(configs):
        with wandb.init(
            project="multiple-runs",
            name=f"experiment-{i + 1}",
            config=config,
            reinit=True,  # Allow multiple runs
        ) as run:
            print(f"\nRunning experiment {i + 1}/{len(configs)}")
            print(f"Config: {config}")

            # Simulate training
            for step in range(50):
                loss = 2.0 - step * 0.02 + random.random() * 0.1
                wandb.log({"loss": loss})
                time.sleep(0.05)

            wandb.summary["final_loss"] = loss
            print(f"Experiment {i + 1} complete")


if __name__ == "__main__":
    print("=" * 60)
    print("Example 1: Context Manager")
    print("=" * 60)
    train_with_context_manager()

    print("\n" + "=" * 60)
    print("Example 2: Error Handling")
    print("=" * 60)
    train_with_error_handling()

    print("\n" + "=" * 60)
    print("Example 3: Multiple Runs")
    print("=" * 60)
    multiple_runs()
