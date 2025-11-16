"""
Simple example demonstrating basic wanLLMDB usage.
"""

import time
import random
import wanllmdb as wandb


def main():
    # Initialize a run
    run = wandb.init(
        project="quick-start",
        name="simple-example",
        config={
            "learning_rate": 0.001,
            "batch_size": 32,
            "epochs": 10,
        },
        tags=["example", "tutorial"],
    )

    print(f"Run started: {run.name}")
    print(f"Run ID: {run.id}")
    print(f"Config: {dict(run.config)}")

    # Simulate training loop
    for epoch in range(10):
        print(f"\nEpoch {epoch + 1}/10")

        for step in range(100):
            # Simulate training step
            loss = 2.0 - epoch * 0.15 + random.random() * 0.1
            accuracy = epoch * 0.08 + random.random() * 0.05

            # Log metrics
            wandb.log({
                "loss": loss,
                "accuracy": accuracy,
                "epoch": epoch,
            })

            # Simulate work
            time.sleep(0.01)

        print(f"Epoch {epoch + 1} complete - Loss: {loss:.4f}, Accuracy: {accuracy:.4f}")

    # Set summary metrics
    wandb.summary["best_accuracy"] = 0.95
    wandb.summary["final_loss"] = loss

    # Finish the run
    wandb.finish()
    print("\nRun finished!")


if __name__ == "__main__":
    main()
