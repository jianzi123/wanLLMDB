"""
Slurm executor for running jobs on Slurm clusters.

Supports:
- Training jobs (sbatch script)
- Inference jobs (persistent job with srun)
- Workflow jobs (job arrays and dependencies)
"""

import logging
import requests
import json
from typing import Dict, Any, Optional
from app.models.job import Job, JobTypeEnum, JobStatusEnum
from app.executors.base import (
    BaseExecutor,
    JobSubmissionError,
    JobCancellationError,
    JobStatusError,
    ExecutorError,
)

logger = logging.getLogger(__name__)


class SlurmExecutor(BaseExecutor):
    """Slurm job executor using REST API."""

    def __init__(self, executor_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Slurm executor.

        Args:
            executor_config: Global Slurm configuration
                {
                    "rest_api_url": "http://slurm-controller:6820",
                    "auth_token": "user:token",  # Or JWT token
                    "default_partition": "gpu",
                    "default_account": "ml_team",
                }
        """
        super().__init__(executor_config)

        self.rest_api_url = self.config.get("rest_api_url")
        if not self.rest_api_url:
            raise ExecutorError("Slurm REST API URL is required")

        self.auth_token = self.config.get("auth_token")
        if not self.auth_token:
            raise ExecutorError("Slurm auth token is required")

        self.default_partition = self.config.get("default_partition", "compute")
        self.default_account = self.config.get("default_account")

        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            "X-SLURM-USER-NAME": self.auth_token.split(":")[0] if ":" in self.auth_token else "wanllmdb",
            "X-SLURM-USER-TOKEN": self.auth_token.split(":")[1] if ":" in self.auth_token else self.auth_token,
            "Content-Type": "application/json",
        })

    def submit_job(self, job: Job) -> str:
        """Submit job to Slurm."""
        self.validate_config(job)

        try:
            if job.job_type == JobTypeEnum.TRAINING:
                return self._submit_training_job(job)
            elif job.job_type == JobTypeEnum.INFERENCE:
                return self._submit_inference_job(job)
            elif job.job_type == JobTypeEnum.WORKFLOW:
                return self._submit_workflow_job(job)
            else:
                raise ValueError(f"Unsupported job type: {job.job_type}")
        except requests.RequestException as e:
            raise JobSubmissionError(f"Slurm API error: {str(e)}")
        except Exception as e:
            raise JobSubmissionError(f"Failed to submit job: {str(e)}")

    def _submit_training_job(self, job: Job) -> str:
        """Submit a training job via sbatch."""
        config = job.executor_config

        # Build job submission request
        job_spec = self._build_training_spec(job)

        # Submit via REST API
        response = self._api_request(
            "POST",
            "/slurm/v0.0.40/job/submit",
            data=job_spec
        )

        # Parse response
        if "job_id" in response:
            job_id = str(response["job_id"])
            logger.info(f"Submitted Slurm job: {job_id}")
            return job_id
        else:
            raise JobSubmissionError(f"Unexpected response: {response}")

    def _submit_inference_job(self, job: Job) -> str:
        """Submit an inference job (long-running)."""
        config = job.executor_config

        # Build job spec for persistent inference service
        job_spec = self._build_inference_spec(job)

        response = self._api_request(
            "POST",
            "/slurm/v0.0.40/job/submit",
            data=job_spec
        )

        if "job_id" in response:
            job_id = str(response["job_id"])
            logger.info(f"Submitted Slurm inference job: {job_id}")
            return job_id
        else:
            raise JobSubmissionError(f"Unexpected response: {response}")

    def _submit_workflow_job(self, job: Job) -> str:
        """Submit a workflow job using job arrays and dependencies."""
        config = job.executor_config

        # Build workflow spec
        workflow_spec = self._build_workflow_spec(job)

        # Submit main workflow controller job
        response = self._api_request(
            "POST",
            "/slurm/v0.0.40/job/submit",
            data=workflow_spec
        )

        if "job_id" in response:
            job_id = str(response["job_id"])
            logger.info(f"Submitted Slurm workflow: {job_id}")
            return job_id
        else:
            raise JobSubmissionError(f"Unexpected response: {response}")

    def get_job_status(self, external_id: str) -> JobStatusEnum:
        """Get Slurm job status."""
        try:
            response = self._api_request(
                "GET",
                f"/slurm/v0.0.40/job/{external_id}"
            )

            if "jobs" in response and len(response["jobs"]) > 0:
                job_info = response["jobs"][0]
                return self._parse_job_state(job_info.get("job_state", "UNKNOWN"))
            else:
                # Job not found - might be completed and purged
                return JobStatusEnum.SUCCEEDED
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return JobStatusEnum.SUCCEEDED  # Job completed and removed from queue
            raise JobStatusError(f"Failed to get job status: {str(e)}")

    def cancel_job(self, external_id: str) -> None:
        """Cancel a Slurm job."""
        try:
            self._api_request(
                "DELETE",
                f"/slurm/v0.0.40/job/{external_id}"
            )
            logger.info(f"Cancelled Slurm job: {external_id}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Job {external_id} not found (might be already completed)")
                return
            raise JobCancellationError(f"Failed to cancel job: {str(e)}")

    def get_job_logs(self, external_id: str) -> str:
        """Get job logs."""
        # Note: Slurm REST API doesn't directly provide logs
        # Logs are typically written to files specified in the job script
        config = self.config
        log_dir = config.get("log_directory", "/var/log/slurm/jobs")

        return f"Logs are written to: {log_dir}/{external_id}.out\n" \
               f"Use `cat {log_dir}/{external_id}.out` on the Slurm cluster to view logs."

    def get_job_metrics(self, external_id: str) -> Dict[str, Any]:
        """Get job metrics via sacct."""
        try:
            # Get accounting data
            response = self._api_request(
                "GET",
                f"/slurm/v0.0.40/job/{external_id}"
            )

            if "jobs" in response and len(response["jobs"]) > 0:
                job_info = response["jobs"][0]
                return {
                    "job_id": external_id,
                    "state": job_info.get("job_state"),
                    "elapsed_time": job_info.get("elapsed_time"),
                    "nodes": job_info.get("nodes"),
                    "cpus": job_info.get("cpus"),
                    "partition": job_info.get("partition"),
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to get metrics for {external_id}: {e}")
            return {}

    def _build_training_spec(self, job: Job) -> Dict[str, Any]:
        """Build Slurm job spec for training."""
        config = job.executor_config

        # Build sbatch script
        script = self._generate_sbatch_script(job, config)

        # Build job submission request (Slurm v0.0.40 format)
        job_spec = {
            "job": {
                "name": job.name,
                "partition": config.get("partition", self.default_partition),
                "nodes": config.get("nodes", 1),
                "ntasks_per_node": config.get("ntasks_per_node", 1),
                "cpus_per_task": config.get("cpus_per_task", 1),
                "time_limit": self._parse_time_limit(config.get("time", "01:00:00")),
                "standard_output": config.get("output", f"/tmp/slurm-{job.id}-%j.out"),
                "standard_error": config.get("error", f"/tmp/slurm-{job.id}-%j.err"),
                "current_working_directory": config.get("working_dir", "/scratch"),
                "environment": self._build_environment(config.get("env", {})),
            },
            "script": script,
        }

        # Add GPU request if specified
        if config.get("gpus_per_node"):
            job_spec["job"]["gres"] = f"gpu:{config['gpus_per_node']}"

        # Add memory request
        if config.get("mem"):
            job_spec["job"]["memory_per_node"] = self._parse_memory(config["mem"])

        # Add account if specified
        if config.get("account") or self.default_account:
            job_spec["job"]["account"] = config.get("account", self.default_account)

        return job_spec

    def _build_inference_spec(self, job: Job) -> Dict[str, Any]:
        """Build Slurm job spec for inference (long-running)."""
        config = job.executor_config

        # Inference jobs run as persistent services
        script = config.get("script") or self._generate_inference_script(job, config)

        job_spec = {
            "job": {
                "name": f"{job.name}-inference",
                "partition": config.get("partition", self.default_partition),
                "nodes": config.get("nodes", 1),
                "ntasks": config.get("ntasks", 1),
                "cpus_per_task": config.get("cpus_per_task", 4),
                "time_limit": self._parse_time_limit(config.get("time", "UNLIMITED")),
                "standard_output": f"/tmp/slurm-inference-{job.id}-%j.out",
                "standard_error": f"/tmp/slurm-inference-{job.id}-%j.err",
                "environment": self._build_environment(config.get("env", {})),
            },
            "script": script,
        }

        if config.get("gpus"):
            job_spec["job"]["gres"] = f"gpu:{config['gpus']}"

        return job_spec

    def _build_workflow_spec(self, job: Job) -> Dict[str, Any]:
        """Build Slurm job spec for workflow."""
        config = job.executor_config

        # Workflows use a controller script that manages dependencies
        script = self._generate_workflow_script(job, config)

        job_spec = {
            "job": {
                "name": f"{job.name}-workflow",
                "partition": config.get("partition", self.default_partition),
                "nodes": 1,
                "ntasks": 1,
                "cpus_per_task": 2,
                "time_limit": self._parse_time_limit(config.get("time", "24:00:00")),
                "standard_output": f"/tmp/slurm-workflow-{job.id}-%j.out",
                "environment": self._build_environment(config.get("env", {})),
            },
            "script": script,
        }

        return job_spec

    def _generate_sbatch_script(self, job: Job, config: Dict[str, Any]) -> str:
        """Generate sbatch script for training."""
        script_lines = ["#!/bin/bash"]

        # Load modules
        for module in config.get("modules", []):
            script_lines.append(f"module load {module}")

        # Set environment variables
        for key, value in config.get("env", {}).items():
            script_lines.append(f"export {key}={value}")

        # Change to working directory
        if config.get("working_dir"):
            script_lines.append(f"cd {config['working_dir']}")

        # Add custom script or command
        if config.get("script"):
            script_lines.append(config["script"])
        elif config.get("command"):
            script_lines.append(" ".join(config["command"]))
        else:
            raise ValueError("Either 'script' or 'command' must be specified")

        return "\n".join(script_lines)

    def _generate_inference_script(self, job: Job, config: Dict[str, Any]) -> str:
        """Generate script for inference service."""
        script_lines = ["#!/bin/bash"]

        # Load modules
        for module in config.get("modules", []):
            script_lines.append(f"module load {module}")

        # Start inference service
        script_lines.append(f"# Start inference service")
        script_lines.append(config.get("command", "python serve.py"))

        return "\n".join(script_lines)

    def _generate_workflow_script(self, job: Job, config: Dict[str, Any]) -> str:
        """Generate workflow controller script."""
        # This is a simplified version - reads workflow config and submits sub-jobs
        script_lines = [
            "#!/bin/bash",
            "# Workflow controller",
            f"# Workflow: {job.name}",
            "",
            "# TODO: Implement workflow DAG execution",
            "# For now, run tasks sequentially",
        ]

        templates = config.get("templates", [])
        for i, template in enumerate(templates):
            if "container" in template:
                container = template["container"]
                cmd = " ".join(container.get("command", []))
                script_lines.append(f"echo 'Running step {i+1}: {template.get('name')}'")
                script_lines.append(cmd)

        return "\n".join(script_lines)

    def _build_environment(self, env_dict: Dict[str, str]) -> Dict[str, str]:
        """Build environment variables for Slurm."""
        return env_dict

    def _parse_time_limit(self, time_str: str) -> int:
        """Parse time limit to minutes."""
        if time_str == "UNLIMITED":
            return 0  # 0 means no limit in Slurm

        # Parse HH:MM:SS format
        parts = time_str.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 60 + minutes
        elif len(parts) == 2:
            hours, minutes = map(int, parts)
            return hours * 60 + minutes
        else:
            return int(parts[0])  # Assume minutes

    def _parse_memory(self, mem_str: str) -> int:
        """Parse memory string to MB."""
        mem_str = mem_str.upper()
        if "GB" in mem_str:
            return int(mem_str.replace("GB", "")) * 1024
        elif "MB" in mem_str:
            return int(mem_str.replace("MB", ""))
        elif "TB" in mem_str:
            return int(mem_str.replace("TB", "")) * 1024 * 1024
        else:
            return int(mem_str)  # Assume MB

    def _parse_job_state(self, state: str) -> JobStatusEnum:
        """Map Slurm job state to JobStatusEnum."""
        state_mapping = {
            "PENDING": JobStatusEnum.PENDING,
            "CONFIGURING": JobStatusEnum.QUEUED,
            "RUNNING": JobStatusEnum.RUNNING,
            "COMPLETED": JobStatusEnum.SUCCEEDED,
            "FAILED": JobStatusEnum.FAILED,
            "CANCELLED": JobStatusEnum.CANCELLED,
            "TIMEOUT": JobStatusEnum.TIMEOUT,
            "NODE_FAIL": JobStatusEnum.FAILED,
            "PREEMPTED": JobStatusEnum.CANCELLED,
            "OUT_OF_MEMORY": JobStatusEnum.FAILED,
        }
        return state_mapping.get(state, JobStatusEnum.PENDING)

    def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make Slurm REST API request."""
        url = f"{self.rest_api_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Slurm API request failed: {method} {url} - {str(e)}")
            raise
