"""
Example: Hyperparameter sweep with wanLLMDB.

This example demonstrates how to use wandb.sweep() and wandb.agent()
for automated hyperparameter optimization.
"""

import random
import time
import wanllmdb as wandb


def train():
    """
    Training function for sweep agent.

    This function is called by wandb.agent() for each trial.
    The hyperparameters are available in wandb.config.
    """
    # Initialize run (config is automatically set by agent)
    run = wandb.init()

    # Get hyperparameters from config
    lr = wandb.config.learning_rate
    batch_size = wandb.config.batch_size
    optimizer = wandb.config.optimizer
    epochs = wandb.config.get('epochs', 20)

    print(f"\nTraining with:")
    print(f"  Learning rate: {lr}")
    print(f"  Batch size: {batch_size}")
    print(f"  Optimizer: {optimizer}")

    # Simulate training
    best_accuracy = 0.0
    best_loss = float('inf')

    for epoch in range(epochs):
        # Simulate epoch with performance based on hyperparameters
        base_accuracy = epoch * 0.05
        base_loss = 2.0 - epoch * 0.1

        # Better hyperparameters = better performance
        lr_factor = 1.0 - abs(lr - 0.001) * 100
        bs_factor = 1.0 - abs(batch_size - 32) / 100
        opt_factor = 1.0 if optimizer == 'adam' else 0.95

        accuracy = base_accuracy * lr_factor * bs_factor * opt_factor + random.random() * 0.03
        loss = base_loss * (2.0 - lr_factor * bs_factor * opt_factor) + random.random() * 0.1

        # Clip values
        accuracy = max(0, min(1, accuracy))
        loss = max(0, loss)

        # Log metrics
        wandb.log({
            'accuracy': accuracy,
            'loss': loss,
            'epoch': epoch,
        })

        # Track best
        if accuracy > best_accuracy:
            best_accuracy = accuracy
        if loss < best_loss:
            best_loss = loss

        time.sleep(0.05)

    # Log best metrics to summary
    wandb.summary['best_accuracy'] = best_accuracy
    wandb.summary['best_loss'] = best_loss

    print(f"Final best accuracy: {best_accuracy:.4f}")

    # Finish run
    wandb.finish()


def main():
    """
    Main function to create and run a hyperparameter sweep.
    """
    # Define sweep configuration
    sweep_config = {
        'name': 'mnist-hyperparameter-search',
        'description': 'Bayesian optimization of MNIST hyperparameters',
        'method': 'bayes',  # or 'random', 'grid'
        'metric': {
            'name': 'best_accuracy',
            'goal': 'maximize',
        },
        'parameters': {
            'learning_rate': {
                'distribution': 'log_uniform',
                'min': 0.0001,
                'max': 0.01,
            },
            'batch_size': {
                'values': [16, 32, 64, 128],
            },
            'optimizer': {
                'values': ['adam', 'sgd', 'rmsprop'],
            },
            'epochs': {
                'value': 20,  # Fixed value
            },
        },
        'early_terminate': {
            'type': 'hyperband',
            'min_iter': 3,
            'eta': 3,
        },
        'run_cap': 30,  # Maximum 30 trials
    }

    # Create sweep
    print("Creating hyperparameter sweep...")
    sweep_id = wandb.sweep(sweep_config, project='hyperparameter-optimization')

    print(f"\nSweep created: {sweep_id}")
    print("Starting sweep agent...\n")

    # Run sweep agent
    # The agent will run up to 30 trials (or until manually stopped)
    wandb.agent(sweep_id, function=train, count=30)

    print("\n" + "="*60)
    print("Sweep complete!")
    print("="*60)


def advanced_example():
    """
    Advanced example using SweepController for finer-grained control.
    """
    sweep_config = {
        'method': 'random',
        'metric': {
            'name': 'loss',
            'goal': 'minimize',
        },
        'parameters': {
            'learning_rate': {
                'distribution': 'uniform',
                'min': 0.001,
                'max': 0.1,
            },
            'dropout': {
                'distribution': 'uniform',
                'min': 0.0,
                'max': 0.5,
            },
        },
    }

    # Create sweep
    sweep_id = wandb.sweep(sweep_config, project='advanced-sweep')

    # Use SweepController for manual control
    controller = wandb.SweepController(sweep_id)

    # Run custom sweep loop
    for trial in range(10):
        # Get parameter suggestion
        params = controller.suggest()
        print(f"Trial {trial + 1}: {params}")

        # Initialize run with suggested parameters
        run = wandb.init(config=params)

        # Custom training logic...
        loss = train_custom_model(params)

        # Report result
        wandb.log({'loss': loss})
        wandb.finish()

    # Finish sweep
    controller.finish()

    # Get best parameters
    best_params = controller.get_best_params()
    print(f"Best parameters: {best_params}")


def train_custom_model(params):
    """Custom training function for advanced example."""
    # Simulate training
    time.sleep(0.1)
    return random.random() * (1.0 - params['dropout']) + params['learning_rate'] * 0.1


if __name__ == "__main__":
    # Run basic sweep example
    main()

    # Uncomment to run advanced example
    # advanced_example()
