# wanLLMDB Python SDK

Python SDK for wanLLMDB - A powerful ML experiment management platform.

## Installation

```bash
pip install wanllmdb
```

Or install from source:

```bash
cd sdk/python
pip install -e .
```

## Quick Start

```python
import wanllmdb as wandb

# Initialize a new run
run = wandb.init(
    project="my-project",
    name="experiment-1",
    config={
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 10,
    }
)

# Log metrics during training
for epoch in range(10):
    for step in range(100):
        loss = train_step()
        wandb.log({"loss": loss, "epoch": epoch}, step=step)

# Finish the run
wandb.finish()
```

## Features

### Run Initialization

```python
run = wandb.init(
    project="my-project",      # Project name (required)
    name="my-run",            # Run name (optional, auto-generated if not provided)
    config={...},             # Hyperparameters and configuration
    tags=["baseline", "v1"],  # Tags for organizing runs
    notes="Experiment notes", # Description of the run
)
```

### Configuration Management

```python
# Set configuration
wandb.config.update({
    "learning_rate": 0.001,
    "batch_size": 32,
})

# Access configuration
lr = wandb.config.learning_rate
batch_size = wandb.config["batch_size"]

# Update during runtime
wandb.config.update({"learning_rate": 0.0005})
```

### Metric Logging

```python
# Log single metric
wandb.log({"loss": 0.5})

# Log multiple metrics
wandb.log({
    "loss": 0.5,
    "accuracy": 0.95,
    "learning_rate": 0.001,
})

# Log with step
wandb.log({"loss": 0.5}, step=100)

# Automatic step increment
for i in range(100):
    wandb.log({"metric": value})  # Step auto-increments
```

### Summary Metrics

```python
# Set summary metrics (best values)
wandb.summary["best_accuracy"] = 0.98
wandb.summary["final_loss"] = 0.05

# Summary is automatically saved at the end
```

### Tags Management

```python
# Add tags during initialization
run = wandb.init(project="my-project", tags=["baseline"])

# Add tags during run
wandb.run.tags.append("important")
wandb.run.tags.extend(["v1", "production"])

# Remove tags
wandb.run.tags.remove("baseline")
```

### System Metrics

System metrics (CPU, GPU, memory, disk) are automatically collected every 30 seconds by default.

```python
# Disable system metrics
run = wandb.init(project="my-project", monitor_system=False)

# Custom interval (in seconds)
run = wandb.init(project="my-project", monitor_interval=60)
```

### Git Integration

Git information is automatically captured when available:

```python
# Automatic git tracking
run = wandb.init(project="my-project")
# Captures: commit hash, branch, remote URL

# Disable git tracking
run = wandb.init(project="my-project", git_tracking=False)
```

### Run Finish

```python
# Normal finish
wandb.finish()

# Finish with exit code
wandb.finish(exit_code=0)

# Mark as failed
wandb.finish(exit_code=1)
```

## Configuration

### Environment Variables

```bash
# API endpoint
export WANLLMDB_API_URL=http://localhost:8000/api/v1
export WANLLMDB_METRIC_URL=http://localhost:8001/api/v1

# Authentication
export WANLLMDB_API_KEY=your-api-key
export WANLLMDB_USERNAME=your-username
export WANLLMDB_PASSWORD=your-password

# Project defaults
export WANLLMDB_PROJECT=default-project

# System monitoring
export WANLLMDB_MONITOR_SYSTEM=true
export WANLLMDB_MONITOR_INTERVAL=30
```

### Configuration File

Create `.wanllmdb/config.yaml` in your home directory:

```yaml
api_url: http://localhost:8000/api/v1
metric_url: http://localhost:8001/api/v1
username: your-username
password: your-password
project: default-project
monitor_system: true
monitor_interval: 30
```

## Advanced Usage

### Context Manager

```python
with wandb.init(project="my-project") as run:
    # Training code
    wandb.log({"loss": 0.5})
    # Automatically finished when exiting context
```

### Multiple Runs

```python
# Run 1
run1 = wandb.init(project="project-a", name="run-1")
wandb.log({"metric": 1})
wandb.finish()

# Run 2
run2 = wandb.init(project="project-a", name="run-2")
wandb.log({"metric": 2})
wandb.finish()
```

### Error Handling

```python
try:
    run = wandb.init(project="my-project")
    # Training code
    wandb.log({"loss": 0.5})
except Exception as e:
    print(f"Error: {e}")
    wandb.finish(exit_code=1)
else:
    wandb.finish(exit_code=0)
```

## API Reference

### wandb.init()

Initialize a new run.

**Parameters**:
- `project` (str, required): Project name
- `name` (str, optional): Run name (auto-generated if not provided)
- `config` (dict, optional): Configuration dictionary
- `tags` (list, optional): List of tags
- `notes` (str, optional): Run description
- `monitor_system` (bool, default=True): Enable system metrics
- `monitor_interval` (int, default=30): System metrics interval in seconds
- `git_tracking` (bool, default=True): Enable git tracking

**Returns**: Run object

### wandb.log()

Log metrics.

**Parameters**:
- `metrics` (dict): Dictionary of metric name-value pairs
- `step` (int, optional): Step number (auto-increments if not provided)
- `commit` (bool, default=True): Immediately send to server

### wandb.finish()

Finish the current run.

**Parameters**:
- `exit_code` (int, default=0): Exit code (0=success, non-zero=failure)

### wandb.config

Configuration object for accessing and updating hyperparameters.

### wandb.summary

Summary object for storing best/final metric values.

### wandb.run

Current active run object. Properties:
- `id`: Run ID
- `name`: Run name
- `project_id`: Project ID
- `state`: Run state
- `tags`: List of tags
- `config`: Configuration dictionary
- `summary`: Summary dictionary

## Examples

See `examples/` directory for complete examples:

- `examples/pytorch_mnist.py`: PyTorch MNIST training
- `examples/tensorflow_keras.py`: TensorFlow/Keras training
- `examples/scikit_learn.py`: Scikit-learn model training
- `examples/hyperparameter_search.py`: Hyperparameter tuning

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=wanllmdb tests/

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## License

MIT License

## Support

- Documentation: https://docs.wanllmdb.dev
- Issues: https://github.com/wanllmdb/wanllmdb/issues
- Discord: https://discord.gg/wanllmdb
