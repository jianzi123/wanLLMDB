"""
Example: Hyperparameter search with wanLLMDB tracking.
"""

import random
import time
import wanllmdb as wandb


def train_model(config):
    """Simulate model training with given hyperparameters."""
    # Simulate training
    best_loss = float("inf")
    best_accuracy = 0.0

    for epoch in range(config["epochs"]):
        # Simulate epoch with random performance based on hyperparameters
        base_loss = 2.0 - epoch * 0.2
        base_accuracy = epoch * 0.1

        # Better hyperparameters = better performance
        lr_factor = 1.0 - abs(config["learning_rate"] - 0.001) * 100
        bs_factor = 1.0 - abs(config["batch_size"] - 32) / 100

        loss = base_loss * (2.0 - lr_factor * bs_factor) + random.random() * 0.1
        accuracy = base_accuracy * lr_factor * bs_factor + random.random() * 0.05

        # Log metrics
        wandb.log({
            "loss": loss,
            "accuracy": accuracy,
            "epoch": epoch,
        })

        # Track best metrics
        if loss < best_loss:
            best_loss = loss
        if accuracy > best_accuracy:
            best_accuracy = accuracy

        time.sleep(0.05)

    return best_loss, best_accuracy


def hyperparameter_search():
    """Run hyperparameter search."""

    # Define search space
    learning_rates = [0.0001, 0.0005, 0.001, 0.005, 0.01]
    batch_sizes = [16, 32, 64, 128]
    optimizers = ["adam", "sgd", "rmsprop"]

    # Try different combinations
    num_trials = 10
    best_config = None
    best_score = 0.0

    for trial in range(num_trials):
        # Sample hyperparameters
        config = {
            "learning_rate": random.choice(learning_rates),
            "batch_size": random.choice(batch_sizes),
            "optimizer": random.choice(optimizers),
            "epochs": 20,
        }

        print(f"\n{'='*60}")
        print(f"Trial {trial + 1}/{num_trials}")
        print(f"Config: {config}")
        print(f"{'='*60}")

        # Initialize run for this trial
        run = wandb.init(
            project="hyperparameter-search",
            name=f"trial-{trial + 1}",
            config=config,
            tags=["hyperparameter-search", f"trial-{trial + 1}"],
            reinit=True,  # Allow multiple runs in same script
        )

        # Train model
        best_loss, best_accuracy = train_model(config)

        # Set summary
        wandb.summary["best_loss"] = best_loss
        wandb.summary["best_accuracy"] = best_accuracy

        # Track overall best
        if best_accuracy > best_score:
            best_score = best_accuracy
            best_config = config.copy()

        print(f"\nTrial {trial + 1} Results:")
        print(f"  Best Loss: {best_loss:.4f}")
        print(f"  Best Accuracy: {best_accuracy:.4f}")

        # Finish run
        wandb.finish()

    print(f"\n{'='*60}")
    print("Hyperparameter Search Complete!")
    print(f"{'='*60}")
    print(f"Best Config: {best_config}")
    print(f"Best Accuracy: {best_score:.4f}")


if __name__ == "__main__":
    hyperparameter_search()
