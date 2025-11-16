"""
Optuna integration service for Bayesian hyperparameter optimization.
"""

import optuna
from optuna.samplers import TPESampler, RandomSampler, GridSampler
from optuna.importance import get_param_importances
from typing import Dict, Any, Optional, List
from uuid import UUID
import json

from app.models.sweep import Sweep, SweepMethod, MetricGoal


class OptunaService:
    """Service for Optuna-based hyperparameter optimization."""

    def __init__(self):
        """Initialize Optuna service."""
        # Store studies in memory (could be replaced with database storage)
        self._studies: Dict[str, optuna.Study] = {}

    def create_study(
        self,
        sweep: Sweep,
        study_name: Optional[str] = None,
    ) -> optuna.Study:
        """
        Create or get an Optuna study for a sweep.

        Args:
            sweep: Sweep model instance
            study_name: Optional study name (defaults to sweep ID)

        Returns:
            Optuna study instance
        """
        if not study_name:
            study_name = str(sweep.id)

        # Check if study already exists
        if study_name in self._studies:
            return self._studies[study_name]

        # Determine direction
        direction = "maximize" if sweep.metric_goal == MetricGoal.MAXIMIZE else "minimize"

        # Create sampler based on method
        sampler = self._create_sampler(sweep)

        # Create study
        study = optuna.create_study(
            study_name=study_name,
            direction=direction,
            sampler=sampler,
            load_if_exists=True,
        )

        self._studies[study_name] = study
        return study

    def _create_sampler(self, sweep: Sweep) -> optuna.samplers.BaseSampler:
        """Create appropriate sampler based on sweep method."""
        if sweep.method == SweepMethod.RANDOM:
            return RandomSampler()
        elif sweep.method == SweepMethod.GRID:
            # Grid sampler requires search space definition
            search_space = self._build_search_space(sweep.config)
            return GridSampler(search_space)
        elif sweep.method == SweepMethod.BAYES:
            return TPESampler(n_startup_trials=10)
        else:
            # Default to TPE for unknown methods
            return TPESampler()

    def _build_search_space(self, config: Dict[str, Any]) -> Dict[str, List[Any]]:
        """Build search space for grid sampler."""
        search_space = {}

        for param_name, param_config in config.items():
            if "values" in param_config:
                search_space[param_name] = param_config["values"]
            elif "distribution" in param_config:
                # For grid search with continuous params, discretize
                dist = param_config["distribution"]
                min_val = param_config.get("min", 0)
                max_val = param_config.get("max", 1)

                if dist in ["uniform", "log_uniform"]:
                    # Create discrete grid
                    import numpy as np
                    if dist == "log_uniform":
                        values = np.logspace(np.log10(min_val), np.log10(max_val), 10)
                    else:
                        values = np.linspace(min_val, max_val, 10)
                    search_space[param_name] = values.tolist()

        return search_space

    def suggest_parameters(
        self,
        sweep: Sweep,
        trial_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Suggest next set of hyperparameters.

        Args:
            sweep: Sweep model instance
            trial_number: Optional trial number

        Returns:
            Dictionary of suggested parameter values
        """
        study = self.create_study(sweep)

        # Create a trial
        trial = study.ask()

        # Suggest parameters based on configuration
        suggested_params = {}

        for param_name, param_config in sweep.config.items():
            if "values" in param_config:
                # Categorical parameter
                suggested_params[param_name] = trial.suggest_categorical(
                    param_name,
                    param_config["values"]
                )
            elif "distribution" in param_config:
                dist = param_config["distribution"]
                min_val = param_config.get("min", 0)
                max_val = param_config.get("max", 1)

                if dist == "uniform":
                    # Continuous uniform
                    q = param_config.get("q")
                    if q:
                        suggested_params[param_name] = trial.suggest_float(
                            param_name, min_val, max_val, step=q
                        )
                    else:
                        suggested_params[param_name] = trial.suggest_float(
                            param_name, min_val, max_val
                        )
                elif dist == "log_uniform":
                    # Log-scale uniform
                    suggested_params[param_name] = trial.suggest_float(
                        param_name, min_val, max_val, log=True
                    )
                elif dist == "int_uniform":
                    # Integer uniform
                    suggested_params[param_name] = trial.suggest_int(
                        param_name, int(min_val), int(max_val)
                    )
                elif dist == "normal":
                    # Normal distribution (using uniform as approximation)
                    mu = param_config.get("mu", 0)
                    sigma = param_config.get("sigma", 1)
                    # Approximate with 3-sigma range
                    suggested_params[param_name] = trial.suggest_float(
                        param_name, mu - 3*sigma, mu + 3*sigma
                    )

        return {
            "suggested_params": suggested_params,
            "trial_number": trial.number,
            "trial": trial,  # Store for later reporting
        }

    def report_result(
        self,
        sweep: Sweep,
        trial_number: int,
        metric_value: float,
        state: str = "complete",
    ) -> None:
        """
        Report trial result to Optuna.

        Args:
            sweep: Sweep model instance
            trial_number: Trial number
            metric_value: Metric value to report
            state: Trial state (complete, pruned, fail)
        """
        study = self.create_study(sweep)

        # Find the trial by number
        trials = study.trials
        trial = None
        for t in trials:
            if t.number == trial_number:
                trial = t
                break

        if not trial:
            print(f"Warning: Trial {trial_number} not found in study")
            return

        # Report the result
        if state == "complete":
            study.tell(trial, metric_value)
        elif state == "pruned":
            study.tell(trial, state=optuna.trial.TrialState.PRUNED)
        elif state == "fail":
            study.tell(trial, state=optuna.trial.TrialState.FAIL)

    def get_best_params(self, sweep: Sweep) -> Optional[Dict[str, Any]]:
        """
        Get best parameters found so far.

        Args:
            sweep: Sweep model instance

        Returns:
            Dictionary of best parameter values or None
        """
        study_name = str(sweep.id)
        if study_name not in self._studies:
            return None

        study = self._studies[study_name]

        if not study.best_trial:
            return None

        return study.best_trial.params

    def get_best_value(self, sweep: Sweep) -> Optional[float]:
        """
        Get best metric value found so far.

        Args:
            sweep: Sweep model instance

        Returns:
            Best metric value or None
        """
        study_name = str(sweep.id)
        if study_name not in self._studies:
            return None

        study = self._studies[study_name]

        if not study.best_trial:
            return None

        return study.best_value

    def get_parameter_importance(
        self,
        sweep: Sweep,
        n_trials: Optional[int] = None,
    ) -> Optional[Dict[str, float]]:
        """
        Calculate parameter importance using fANOVA.

        Args:
            sweep: Sweep model instance
            n_trials: Number of trials to use (None = all)

        Returns:
            Dictionary mapping parameter names to importance scores (0-1)
        """
        study_name = str(sweep.id)
        if study_name not in self._studies:
            return None

        study = self._studies[study_name]

        # Need at least 2 completed trials
        completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
        if len(completed_trials) < 2:
            return None

        try:
            # Calculate importance
            importance = get_param_importances(
                study,
                n_trials=n_trials,
            )
            return importance
        except Exception as e:
            print(f"Error calculating parameter importance: {e}")
            return None

    def get_optimization_history(self, sweep: Sweep) -> List[Dict[str, Any]]:
        """
        Get optimization history for visualization.

        Args:
            sweep: Sweep model instance

        Returns:
            List of trial information
        """
        study_name = str(sweep.id)
        if study_name not in self._studies:
            return []

        study = self._studies[study_name]

        history = []
        for trial in study.trials:
            if trial.state != optuna.trial.TrialState.COMPLETE:
                continue

            history.append({
                "trial_number": trial.number,
                "params": trial.params,
                "value": trial.value,
                "datetime_start": trial.datetime_start.isoformat() if trial.datetime_start else None,
                "datetime_complete": trial.datetime_complete.isoformat() if trial.datetime_complete else None,
            })

        return history

    def should_prune_trial(
        self,
        sweep: Sweep,
        trial_number: int,
        step: int,
        intermediate_value: float,
    ) -> bool:
        """
        Check if trial should be pruned (early stopped).

        Args:
            sweep: Sweep model instance
            trial_number: Trial number
            step: Current step/epoch
            intermediate_value: Intermediate metric value

        Returns:
            True if trial should be pruned
        """
        if not sweep.early_terminate:
            return False

        study = self.create_study(sweep)

        # Find trial
        trial = None
        for t in study.trials:
            if t.number == trial_number:
                trial = t
                break

        if not trial:
            return False

        # Report intermediate value
        trial.report(intermediate_value, step)

        # Check if should prune
        return trial.should_prune()


# Global Optuna service instance
optuna_service = OptunaService()
