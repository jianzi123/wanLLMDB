"""
Example demonstrating Model Registry for versioning and deploying models.

This shows how to:
1. Register models to the registry
2. Create model versions
3. Transition between stages (staging → production)
4. Use models from the registry
"""

import wanllmdb as wandb
import os
import pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split


def example_1_register_model():
    """Train and register a model to the registry."""
    print("\n=== Example 1: Register Model ===\n")

    # Initialize run
    run = wandb.init(
        project="model-registry-demo",
        name="train-credit-model-v1",
        config={
            "model_type": "logistic_regression",
            "max_iter": 1000,
            "C": 1.0,
        }
    )

    # Train a model
    print("Training model...")
    X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LogisticRegression(max_iter=1000, C=1.0)
    model.fit(X_train, y_train)

    # Evaluate
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)

    print(f"Train accuracy: {train_acc:.4f}")
    print(f"Test accuracy: {test_acc:.4f}")

    # Log metrics
    wandb.log({"train_accuracy": train_acc, "test_accuracy": test_acc})
    run.summary["accuracy"] = test_acc

    # Save model to file
    model_path = "credit_risk_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    # Register model to Model Registry
    registry = wandb.ModelRegistry(run.api_client, run.project_id)

    version_info = registry.log_model(
        run=run,
        model_path=model_path,
        registered_model_name="credit-risk-model",
        version="v1.0.0",
        description="Initial logistic regression model",
        tags=["baseline", "sklearn"],
        metadata={"framework": "scikit-learn", "algorithm": "LogisticRegression"}
    )

    print(f"\nModel registered!")
    print(f"  Model ID: {version_info['model_id']}")
    print(f"  Version: {version_info['version']}")

    # Clean up
    os.remove(model_path)
    wandb.finish()

    print("\n✓ Example 1 completed")
    return version_info


def example_2_register_improved_model():
    """Train an improved model and register a new version."""
    print("\n=== Example 2: Register Improved Model ===\n")

    # Initialize run
    run = wandb.init(
        project="model-registry-demo",
        name="train-credit-model-v2",
        config={
            "model_type": "logistic_regression",
            "max_iter": 2000,
            "C": 0.5,  # Different hyperparameter
        }
    )

    # Train improved model
    print("Training improved model...")
    X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LogisticRegression(max_iter=2000, C=0.5)
    model.fit(X_train, y_train)

    # Evaluate
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)

    print(f"Train accuracy: {train_acc:.4f}")
    print(f"Test accuracy: {test_acc:.4f}")

    # Log metrics
    wandb.log({"train_accuracy": train_acc, "test_accuracy": test_acc})
    run.summary["accuracy"] = test_acc

    # Save model
    model_path = "credit_risk_model_v2.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    # Register as new version
    registry = wandb.ModelRegistry(run.api_client, run.project_id)

    version_info = registry.log_model(
        run=run,
        model_path=model_path,
        registered_model_name="credit-risk-model",  # Same model name
        version="v2.0.0",  # New version
        description="Improved model with tuned hyperparameters",
        tags=["improved", "sklearn"],
    )

    print(f"\nNew version registered!")
    print(f"  Version: {version_info['version']}")

    # Clean up
    os.remove(model_path)
    wandb.finish()

    print("\n✓ Example 2 completed")
    return version_info


def example_3_promote_to_staging():
    """Promote a model version to staging."""
    print("\n=== Example 3: Promote to Staging ===\n")

    # Get API client (without active run)
    from wanllmdb.config import Config
    from wanllmdb.api_client import APIClient

    config = Config.load()
    api_client = APIClient(
        api_url=config.api_url,
        metric_url=config.metric_url,
        username=config.username,
        password=config.password,
        api_key=config.api_key,
    )
    api_client.login()

    # Get project
    project_data = api_client.get_project_by_name("model-registry-demo")
    project_id = project_data["id"]

    # Create registry
    registry = wandb.ModelRegistry(api_client, project_id)

    # Transition v2.0.0 to staging
    updated_version = registry.transition_stage(
        registered_model_name="credit-risk-model",
        version="v2.0.0",
        stage="staging",
        comment="Testing improved model in staging environment"
    )

    print(f"\nModel version transitioned to staging!")
    print(f"  Version: {updated_version['version']}")
    print(f"  Stage: {updated_version['stage']}")

    print("\n✓ Example 3 completed")


def example_4_promote_to_production():
    """Promote a model version to production."""
    print("\n=== Example 4: Promote to Production ===\n")

    # Get API client
    from wanllmdb.config import Config
    from wanllmdb.api_client import APIClient

    config = Config.load()
    api_client = APIClient(
        api_url=config.api_url,
        metric_url=config.metric_url,
        username=config.username,
        password=config.password,
        api_key=config.api_key,
    )
    api_client.login()

    # Get project
    project_data = api_client.get_project_by_name("model-registry-demo")
    project_id = project_data["id"]

    # Create registry
    registry = wandb.ModelRegistry(api_client, project_id)

    # Transition to production
    updated_version = registry.transition_stage(
        registered_model_name="credit-risk-model",
        version="v2.0.0",
        stage="production",
        comment="Model passed all tests, deploying to production"
    )

    print(f"\nModel version deployed to production!")
    print(f"  Version: {updated_version['version']}")
    print(f"  Stage: {updated_version['stage']}")
    print(f"  Approved at: {updated_version.get('approved_at', 'N/A')}")

    print("\n✓ Example 4 completed")


def example_5_use_production_model():
    """Use the production model from registry."""
    print("\n=== Example 5: Use Production Model ===\n")

    # Get API client
    from wanllmdb.config import Config
    from wanllmdb.api_client import APIClient

    config = Config.load()
    api_client = APIClient(
        api_url=config.api_url,
        metric_url=config.metric_url,
        username=config.username,
        password=config.password,
        api_key=config.api_key,
    )
    api_client.login()

    # Get project
    project_data = api_client.get_project_by_name("model-registry-demo")
    project_id = project_data["id"]

    # Create registry
    registry = wandb.ModelRegistry(api_client, project_id)

    # Load production model
    model_path = registry.use_model(
        registered_model_name="credit-risk-model",
        stage="production"  # Get latest production version
    )

    print(f"\nProduction model loaded from: {model_path}")

    # Load and use the model
    model_file = os.path.join(model_path, "credit_risk_model_v2.pkl")
    if os.path.exists(model_file):
        with open(model_file, "rb") as f:
            model = pickle.load(f)

        # Make predictions
        X_test = np.random.randn(5, 20)
        predictions = model.predict(X_test)
        print(f"Predictions: {predictions}")
    else:
        print(f"Model file not found at expected location")

    print("\n✓ Example 5 completed")


def example_6_list_models_and_versions():
    """List all models and their versions."""
    print("\n=== Example 6: List Models and Versions ===\n")

    # Get API client
    from wanllmdb.config import Config
    from wanllmdb.api_client import APIClient

    config = Config.load()
    api_client = APIClient(
        api_url=config.api_url,
        metric_url=config.metric_url,
        username=config.username,
        password=config.password,
        api_key=config.api_key,
    )
    api_client.login()

    # Get project
    project_data = api_client.get_project_by_name("model-registry-demo")
    project_id = project_data["id"]

    # Create registry
    registry = wandb.ModelRegistry(api_client, project_id)

    # List all models
    models = registry.list_models()
    print(f"Found {len(models)} registered models:")

    for model in models:
        print(f"\n  Model: {model['name']}")
        print(f"    ID: {model['id']}")
        print(f"    Description: {model.get('description', 'N/A')}")

        # Get versions
        versions = registry.get_model_versions(model['name'])
        print(f"    Versions: {len(versions)}")

        for version in versions:
            print(f"      - {version['version']} (stage: {version['stage']})")
            if version.get('metrics'):
                print(f"        Metrics: {version['metrics']}")

    print("\n✓ Example 6 completed")


if __name__ == "__main__":
    print("=" * 60)
    print("Model Registry Examples")
    print("=" * 60)

    print("\nThese examples demonstrate the Model Registry workflow:")
    print("1. Register initial model (v1.0.0)")
    print("2. Register improved model (v2.0.0)")
    print("3. Promote v2.0.0 to staging")
    print("4. Promote v2.0.0 to production")
    print("5. Use production model")
    print("6. List all models and versions")

    # Run examples in order
    example_1_register_model()
    example_2_register_improved_model()
    example_3_promote_to_staging()
    example_4_promote_to_production()
    example_5_use_production_model()
    example_6_list_models_and_versions()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
