# wanLLMDB SDK Examples

This directory contains example scripts demonstrating how to use the wanLLMDB Python SDK.

## Examples

### 1. Simple Example (`simple_example.py`)

Basic usage demonstrating:
- Initializing a run
- Logging metrics
- Setting summary values
- Finishing a run

```bash
python simple_example.py
```

### 2. PyTorch MNIST (`pytorch_mnist.py`)

Complete PyTorch training example with:
- CNN model training on MNIST
- Logging training and test metrics
- Tracking best accuracy
- Saving model checkpoints

**Requirements**:
```bash
pip install torch torchvision
```

```bash
python pytorch_mnist.py
```

### 3. Hyperparameter Search (`hyperparameter_search.py`)

Demonstrates:
- Running multiple experiments
- Hyperparameter tuning
- Comparing results across runs
- Finding best configuration

```bash
python hyperparameter_search.py
```

### 4. Context Manager (`context_manager.py`)

Shows different usage patterns:
- Using context manager for automatic cleanup
- Error handling in training loops
- Running multiple sequential experiments
- Proper resource management

```bash
python context_manager.py
```

## Running Examples

### Prerequisites

1. **Start wanLLMDB services**:
```bash
cd ../../../  # Go to project root
make up
```

2. **Set environment variables** (optional):
```bash
export WANLLMDB_API_URL=http://localhost:8000/api/v1
export WANLLMDB_METRIC_URL=http://localhost:8001/api/v1
export WANLLMDB_USERNAME=your-username
export WANLLMDB_PASSWORD=your-password
```

3. **Install wanLLMDB SDK**:
```bash
cd ../  # Go to sdk/python directory
pip install -e .
```

### Running an Example

```bash
cd examples
python simple_example.py
```

### Viewing Results

1. **Open the UI**:
   - Navigate to http://localhost:3000
   - Go to Projects → Your Project → Runs
   - Click on a run to see details

2. **View metrics in workspace**:
   - Click on a run
   - Navigate to Workspace tab
   - Select metrics to visualize

## Configuration

### Using Config File

Create `.wanllmdb/config.yaml` in your home directory:

```yaml
api_url: http://localhost:8000/api/v1
metric_url: http://localhost:8001/api/v1
username: your-username
password: your-password
project: default-project
```

### Using Environment Variables

```bash
export WANLLMDB_API_URL=http://localhost:8000/api/v1
export WANLLMDB_METRIC_URL=http://localhost:8001/api/v1
export WANLLMDB_USERNAME=your-username
export WANLLMDB_PASSWORD=your-password
export WANLLMDB_PROJECT=default-project
```

## Common Patterns

### Basic Training Loop

```python
import wanllmdb as wandb

# Initialize
run = wandb.init(project="my-project", config={"lr": 0.001})

# Training loop
for epoch in range(10):
    for step in range(100):
        loss = train_step()
        wandb.log({"loss": loss}, step=step)

# Finish
wandb.finish()
```

### With Context Manager

```python
with wandb.init(project="my-project") as run:
    for epoch in range(10):
        loss = train_epoch()
        wandb.log({"loss": loss})
    # Automatically finished
```

### Error Handling

```python
run = wandb.init(project="my-project")

try:
    train()
    wandb.finish(exit_code=0)
except Exception as e:
    print(f"Error: {e}")
    wandb.finish(exit_code=1)
```

### Multiple Runs

```python
for config in configs:
    run = wandb.init(project="sweep", config=config, reinit=True)
    train(config)
    wandb.finish()
```

## Troubleshooting

### Connection Error

If you get connection errors:
1. Make sure services are running: `make up`
2. Check service status: `make status`
3. View logs: `make logs`

### Authentication Error

If authentication fails:
1. Check credentials in config or env vars
2. Create a user account first via UI
3. Use API key instead of username/password

### Import Error

If you get import errors:
1. Install SDK: `pip install -e .`
2. Make sure you're in the right directory
3. Check Python version (>=3.8 required)

## Next Steps

- Read the [SDK Documentation](../README.md)
- Explore the [API Reference](../docs/api.md)
- Check out advanced features:
  - System metrics monitoring
  - Git integration
  - Custom metrics
  - Artifact management (coming soon)
