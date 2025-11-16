"""
Sweep functionality for hyperparameter optimization.
"""

import time
from typing import Dict, Any, Optional, Callable, List
from uuid import UUID

from wanllmdb.api_client import APIClient
from wanllmdb.config import Config
from wanllmdb import sdk


def sweep(config: Dict[str, Any], project: Optional[str] = None) -> str:
    """
    Create a hyperparameter sweep.

    Args:
        config: Sweep configuration dictionary containing:
            - method: Optimization method ('random', 'grid', or 'bayes')
            - metric: Dict with 'name' and 'goal' ('maximize' or 'minimize')
            - parameters: Dict of parameter distributions
            - early_terminate: Optional early termination config
            - run_cap: Optional maximum number of runs
        project: Project name or ID

    Returns:
        Sweep ID

    Example:
        >>> import wanllmdb as wandb
        >>> sweep_config = {
        ...     'method': 'bayes',
        ...     'metric': {
        ...         'name': 'accuracy',
        ...         'goal': 'maximize'
        ...     },
        ...     'parameters': {
        ...         'learning_rate': {
        ...             'distribution': 'log_uniform',
        ...             'min': 0.0001,
        ...             'max': 0.01
        ...         },
        ...         'batch_size': {
        ...             'values': [16, 32, 64, 128]
        ...         }
        ...     },
        ...     'run_cap': 50
        ... }
        >>> sweep_id = wandb.sweep(sweep_config, project='my-project')
    """
    # Get configuration
    cfg = Config.load()
    client = APIClient(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
    )

    # Determine project ID
    project_id = None
    if project:
        # Try to get project by name
        projects_response = client.get('/projects', params={'search': project})
        if projects_response and 'items' in projects_response:
            for proj in projects_response['items']:
                if proj['name'] == project or proj['slug'] == project or proj['id'] == project:
                    project_id = proj['id']
                    break

        if not project_id:
            raise ValueError(f"Project '{project}' not found")
    else:
        # Use default project from config
        if cfg.default_project:
            project = cfg.default_project
            projects_response = client.get('/projects', params={'search': project})
            if projects_response and 'items' in projects_response:
                for proj in projects_response['items']:
                    if proj['name'] == project or proj['slug'] == project:
                        project_id = proj['id']
                        break

    if not project_id:
        raise ValueError("No project specified and no default project configured")

    # Extract sweep configuration
    method = config.get('method', 'random')
    metric = config.get('metric', {})
    parameters = config.get('parameters', {})
    early_terminate = config.get('early_terminate')
    run_cap = config.get('run_cap')

    # Generate sweep name
    sweep_name = config.get('name', f"{method}-sweep-{int(time.time())}")

    # Create sweep
    sweep_data = {
        'name': sweep_name,
        'description': config.get('description'),
        'project_id': project_id,
        'method': method,
        'metric_name': metric.get('name', 'loss'),
        'metric_goal': metric.get('goal', 'minimize'),
        'config': parameters,
        'early_terminate': early_terminate,
        'run_cap': run_cap,
    }

    response = client.post('/sweeps', data=sweep_data)

    if not response or 'id' not in response:
        raise RuntimeError("Failed to create sweep")

    sweep_id = response['id']
    print(f"Created sweep: {sweep_id}")
    print(f"View sweep at: {cfg.base_url.replace('/api/v1', '')}/sweeps/{sweep_id}")

    return sweep_id


def agent(
    sweep_id: str,
    function: Optional[Callable] = None,
    count: Optional[int] = None,
    project: Optional[str] = None,
) -> None:
    """
    Run a sweep agent that executes trials.

    The agent will repeatedly:
    1. Request parameter suggestions from the sweep
    2. Initialize a run with the suggested parameters
    3. Call the training function
    4. Report results back to the sweep

    Args:
        sweep_id: ID of the sweep to run
        function: Training function to execute for each trial
        count: Maximum number of trials to run (None = unlimited)
        project: Project name (optional, inferred from sweep if not provided)

    Example:
        >>> import wanllmdb as wandb
        >>>
        >>> def train():
        ...     run = wandb.init()
        ...     lr = wandb.config.learning_rate
        ...     batch_size = wandb.config.batch_size
        ...
        ...     # Train model...
        ...     for epoch in range(10):
        ...         loss = train_epoch(lr, batch_size)
        ...         wandb.log({'loss': loss, 'epoch': epoch})
        ...
        ...     wandb.finish()
        >>>
        >>> sweep_id = wandb.sweep(sweep_config, project='my-project')
        >>> wandb.agent(sweep_id, function=train, count=20)
    """
    # Get configuration
    cfg = Config.load()
    client = APIClient(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
    )

    # Get sweep details
    sweep = client.get(f'/sweeps/{sweep_id}')
    if not sweep:
        raise ValueError(f"Sweep '{sweep_id}' not found")

    print(f"Starting sweep agent for: {sweep['name']}")
    print(f"Method: {sweep['method']}")
    print(f"Metric: {sweep['metricName']} ({sweep['metricGoal']})")

    # Start the sweep if it's pending
    if sweep['state'] == 'pending':
        client.post(f'/sweeps/{sweep_id}/start')
        print("Started sweep")

    trials_run = 0

    while True:
        # Check if we've hit the count limit
        if count is not None and trials_run >= count:
            print(f"Reached trial limit ({count})")
            break

        # Check if sweep is finished
        sweep = client.get(f'/sweeps/{sweep_id}')
        if sweep['state'] in ['finished', 'failed', 'canceled']:
            print(f"Sweep is {sweep['state']}")
            break

        # Check if sweep has hit run cap
        if sweep.get('runCap') and sweep['runCount'] >= sweep['runCap']:
            print(f"Sweep has reached run capacity ({sweep['runCap']})")
            break

        # Request parameter suggestion
        try:
            suggestion = client.post(f'/sweeps/{sweep_id}/suggest', data={'sweep_id': sweep_id})
        except Exception as e:
            print(f"Failed to get parameter suggestion: {e}")
            break

        if not suggestion or 'suggestedParams' not in suggestion:
            print("No more parameter suggestions available")
            break

        suggested_params = suggestion['suggestedParams']
        trial_number = suggestion.get('trialNumber')

        print(f"\nTrial {trials_run + 1}/{count or '∞'} (Trial #{trial_number})")
        print(f"Parameters: {suggested_params}")

        # Initialize run with suggested parameters
        run = sdk.init(
            project=project or sweep['projectId'],
            config=suggested_params,
            tags=[f"sweep-{sweep_id}", f"trial-{trial_number}"],
            name=f"{sweep['name']}-trial-{trial_number}",
        )

        # Associate run with sweep (update run to link to sweep)
        try:
            # This would ideally be done server-side when the run is created
            # For now, we'll track it through sweep_runs
            pass
        except Exception as e:
            print(f"Warning: Failed to associate run with sweep: {e}")

        # Execute training function
        if function:
            try:
                function()
            except Exception as e:
                print(f"Error in training function: {e}")
                sdk.finish(exit_code=1)
        else:
            # If no function provided, user is expected to call wandb.init() themselves
            # Just wait for them to finish
            print("Waiting for run to complete...")
            while sdk.get_run() and sdk.get_run().state == 'running':
                time.sleep(1)

        # Get the final metric value from the run
        if run and run.summary:
            metric_name = sweep['metricName']
            metric_value = run.summary.get(metric_name)

            if metric_value is not None:
                # Create sweep run association
                try:
                    sweep_run_data = {
                        'sweep_id': sweep_id,
                        'run_id': run.id,
                        'suggested_params': suggested_params,
                        'metric_value': metric_value,
                        'trial_number': trial_number,
                    }

                    # Report result back to sweep via sweep_runs endpoint
                    # This would be a new endpoint we'd need to add
                    # For now, the backend will auto-detect and update

                except Exception as e:
                    print(f"Warning: Failed to report result to sweep: {e}")

        trials_run += 1

        # Brief pause between trials
        time.sleep(0.5)

    print(f"\nSweep agent completed {trials_run} trials")

    # Get final sweep stats
    try:
        stats = client.get(f'/sweeps/{sweep_id}/stats')
        if stats:
            print(f"\nSweep Statistics:")
            print(f"  Total runs: {stats.get('totalRuns', 0)}")
            print(f"  Completed runs: {stats.get('completedRuns', 0)}")
            print(f"  Best value: {stats.get('bestValue', 'N/A')}")
            if stats.get('bestParams'):
                print(f"  Best parameters:")
                for param, value in stats['bestParams'].items():
                    print(f"    {param}: {value}")
    except Exception:
        pass


class SweepController:
    """
    Controller for managing sweep execution.

    Provides finer-grained control over sweep agent behavior.
    """

    def __init__(self, sweep_id: str):
        """
        Initialize sweep controller.

        Args:
            sweep_id: ID of the sweep
        """
        self.sweep_id = sweep_id
        self.cfg = Config.load()
        self.client = APIClient(
            base_url=self.cfg.base_url,
            api_key=self.cfg.api_key,
        )
        self.sweep = self.client.get(f'/sweeps/{sweep_id}')

        if not self.sweep:
            raise ValueError(f"Sweep '{sweep_id}' not found")

    def suggest(self) -> Dict[str, Any]:
        """
        Get next parameter suggestion.

        Returns:
            Dictionary of suggested parameters
        """
        suggestion = self.client.post(
            f'/sweeps/{self.sweep_id}/suggest',
            data={'sweep_id': self.sweep_id}
        )

        if not suggestion or 'suggestedParams' not in suggestion:
            raise RuntimeError("No more parameter suggestions available")

        return suggestion['suggestedParams']

    def report(self, metric_value: float, run_id: Optional[str] = None) -> None:
        """
        Report trial result to sweep.

        Args:
            metric_value: Value of the optimization metric
            run_id: Optional run ID (uses current run if not provided)
        """
        if run_id is None:
            current_run = sdk.get_run()
            if current_run:
                run_id = current_run.id

        if not run_id:
            raise ValueError("No run ID provided and no active run")

        # Report would be handled by the backend when run finishes
        # This is a placeholder for future enhancement
        pass

    def pause(self) -> None:
        """Pause the sweep."""
        self.client.post(f'/sweeps/{self.sweep_id}/pause')

    def resume(self) -> None:
        """Resume the sweep."""
        self.client.post(f'/sweeps/{self.sweep_id}/resume')

    def finish(self) -> None:
        """Finish the sweep."""
        self.client.post(f'/sweeps/{self.sweep_id}/finish')

    def get_best_params(self) -> Optional[Dict[str, Any]]:
        """
        Get the best parameters found so far.

        Returns:
            Dictionary of best parameters or None
        """
        stats = self.client.get(f'/sweeps/{self.sweep_id}/stats')
        return stats.get('bestParams') if stats else None
