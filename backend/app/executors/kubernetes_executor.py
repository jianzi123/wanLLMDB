"""
Kubernetes executor for running jobs on Kubernetes clusters.

Supports:
- Training jobs (K8s Job)
- Inference jobs (K8s Deployment + Service)
- Workflow jobs (inspired by Argo Workflows DAG)
"""

import os
import logging
from typing import Dict, Any, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from app.models.job import Job, JobTypeEnum, JobStatusEnum
from app.executors.base import (
    BaseExecutor,
    JobSubmissionError,
    JobCancellationError,
    JobStatusError,
    ExecutorError,
)

logger = logging.getLogger(__name__)


class KubernetesExecutor(BaseExecutor):
    """Kubernetes job executor."""

    def __init__(self, executor_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Kubernetes executor.

        Args:
            executor_config: Global K8s configuration
                {
                    "kubeconfig_path": "/path/to/kubeconfig",  # Optional, uses in-cluster if not specified
                    "default_namespace": "wanllmdb-jobs",
                    "default_service_account": "job-runner",
                    "image_pull_secrets": ["regcred"],
                }
        """
        super().__init__(executor_config)

        # Load Kubernetes configuration
        try:
            if self.config.get("kubeconfig_path"):
                config.load_kube_config(config_file=self.config["kubeconfig_path"])
            else:
                # Try in-cluster config first, fall back to default kubeconfig
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config()
        except Exception as e:
            logger.error(f"Failed to load Kubernetes config: {e}")
            raise ExecutorError(f"Failed to initialize Kubernetes client: {e}")

        # Initialize API clients
        self.batch_v1 = client.BatchV1Api()
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

        self.default_namespace = self.config.get("default_namespace", "wanllmdb-jobs")
        self.default_service_account = self.config.get("default_service_account", "default")
        self.image_pull_secrets = self.config.get("image_pull_secrets", [])

    def submit_job(self, job: Job) -> str:
        """Submit job to Kubernetes."""
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
        except ApiException as e:
            raise JobSubmissionError(f"Kubernetes API error: {e.status} {e.reason}")
        except Exception as e:
            raise JobSubmissionError(f"Failed to submit job: {str(e)}")

    def _submit_training_job(self, job: Job) -> str:
        """Submit a training job as a K8s Job."""
        config = job.executor_config
        namespace = config.get("namespace", self.default_namespace)

        # Generate unique job name
        job_name = self._generate_job_name(job)

        # Build Job spec
        job_spec = self._build_training_spec(job)

        # Create Job
        try:
            self.batch_v1.create_namespaced_job(namespace=namespace, body=job_spec)
            logger.info(f"Created K8s Job: {job_name} in namespace {namespace}")
            return job_name
        except ApiException as e:
            if e.status == 409:  # Already exists
                logger.warning(f"Job {job_name} already exists")
                return job_name
            raise

    def _submit_inference_job(self, job: Job) -> str:
        """Submit an inference job as a K8s Deployment + Service."""
        config = job.executor_config
        namespace = config.get("namespace", self.default_namespace)

        deployment_name = self._generate_job_name(job)

        # Build Deployment spec
        deployment_spec = self._build_inference_spec(job)

        # Create Deployment
        try:
            self.apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment_spec)
            logger.info(f"Created K8s Deployment: {deployment_name}")
        except ApiException as e:
            if e.status != 409:  # Ignore if already exists
                raise

        # Create Service if specified
        if "service" in config:
            service_spec = self._build_service_spec(job, deployment_name)
            try:
                self.core_v1.create_namespaced_service(namespace=namespace, body=service_spec)
                logger.info(f"Created K8s Service: {deployment_name}")
            except ApiException as e:
                if e.status != 409:
                    raise

        return deployment_name

    def _submit_workflow_job(self, job: Job) -> str:
        """
        Submit a workflow job.

        Creates multiple K8s Jobs based on DAG definition.
        This is a simplified version - for production, consider using Argo Workflows.
        """
        config = job.executor_config
        namespace = config.get("namespace", self.default_namespace)

        # Build workflow spec
        workflow_name = self._generate_job_name(job)

        # For simplicity, we'll create a ConfigMap with the workflow definition
        # and a controller job that executes the workflow
        configmap_spec = self._build_workflow_configmap(job, workflow_name)
        controller_job_spec = self._build_workflow_controller_spec(job, workflow_name)

        try:
            # Create ConfigMap
            self.core_v1.create_namespaced_config_map(namespace=namespace, body=configmap_spec)

            # Create controller Job
            self.batch_v1.create_namespaced_job(namespace=namespace, body=controller_job_spec)

            logger.info(f"Created workflow: {workflow_name}")
            return workflow_name
        except ApiException as e:
            if e.status != 409:
                raise
            return workflow_name

    def get_job_status(self, external_id: str) -> JobStatusEnum:
        """Get K8s job status."""
        namespace = self.default_namespace

        try:
            # Try to get as a Job first
            try:
                job = self.batch_v1.read_namespaced_job(name=external_id, namespace=namespace)
                return self._parse_job_status(job)
            except ApiException as e:
                if e.status == 404:
                    # Try as Deployment
                    try:
                        deployment = self.apps_v1.read_namespaced_deployment(name=external_id, namespace=namespace)
                        return self._parse_deployment_status(deployment)
                    except ApiException:
                        raise JobStatusError(f"Job {external_id} not found")
                raise
        except Exception as e:
            raise JobStatusError(f"Failed to get job status: {str(e)}")

    def cancel_job(self, external_id: str) -> None:
        """Cancel a K8s job."""
        namespace = self.default_namespace

        try:
            # Try to delete as Job
            try:
                self.batch_v1.delete_namespaced_job(
                    name=external_id,
                    namespace=namespace,
                    propagation_policy='Background'
                )
                logger.info(f"Cancelled Job: {external_id}")
                return
            except ApiException as e:
                if e.status == 404:
                    # Try as Deployment
                    self.apps_v1.delete_namespaced_deployment(
                        name=external_id,
                        namespace=namespace,
                        propagation_policy='Background'
                    )
                    logger.info(f"Cancelled Deployment: {external_id}")
                    return
                raise
        except Exception as e:
            raise JobCancellationError(f"Failed to cancel job: {str(e)}")

    def get_job_logs(self, external_id: str) -> str:
        """Get job logs."""
        namespace = self.default_namespace

        try:
            # Get pods for this job
            pods = self.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"job-name={external_id}"
            )

            if not pods.items:
                # Try with app label (for Deployments)
                pods = self.core_v1.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=f"app={external_id}"
                )

            if not pods.items:
                return "No pods found"

            # Get logs from first pod
            pod_name = pods.items[0].metadata.name
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=1000
            )
            return logs
        except Exception as e:
            logger.error(f"Failed to get logs for {external_id}: {e}")
            return f"Error getting logs: {str(e)}"

    def get_job_metrics(self, external_id: str) -> Dict[str, Any]:
        """Get job metrics."""
        # This would require metrics-server to be installed
        # For now, return basic info
        return {
            "external_id": external_id,
            "metrics_available": False,
            "message": "Metrics require metrics-server installation"
        }

    def _build_training_spec(self, job: Job) -> Dict[str, Any]:
        """Build K8s Job spec for training."""
        config = job.executor_config
        job_name = self._generate_job_name(job)

        # Build container spec
        container = client.V1Container(
            name="training",
            image=config["image"],
            command=config.get("command"),
            args=config.get("args"),
            env=self._build_env_vars(config.get("env", [])),
            resources=self._build_resources(config.get("resources")),
            volume_mounts=self._build_volume_mounts(config.get("volumeMounts", [])),
        )

        # Build pod template
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                labels={
                    "app": "wanllmdb",
                    "job-type": "training",
                    "job-id": str(job.id),
                    "job-name": job_name,
                }
            ),
            spec=client.V1PodSpec(
                containers=[container],
                restart_policy=config.get("restartPolicy", "OnFailure"),
                service_account_name=config.get("serviceAccount", self.default_service_account),
                node_selector=config.get("nodeSelector"),
                tolerations=self._build_tolerations(config.get("tolerations", [])),
                volumes=self._build_volumes(config.get("volumes", [])),
                image_pull_secrets=[client.V1LocalObjectReference(name=s) for s in self.image_pull_secrets],
            ),
        )

        # Build Job spec
        job_spec = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=job_name,
                labels={
                    "app": "wanllmdb",
                    "job-type": "training",
                    "job-id": str(job.id),
                },
            ),
            spec=client.V1JobSpec(
                template=pod_template,
                backoff_limit=config.get("backoffLimit", 3),
                ttl_seconds_after_finished=config.get("ttlSecondsAfterFinished", 86400),
            ),
        )

        return job_spec

    def _build_inference_spec(self, job: Job) -> Dict[str, Any]:
        """Build K8s Deployment spec for inference."""
        config = job.executor_config
        deployment_name = self._generate_job_name(job)

        container = client.V1Container(
            name="inference",
            image=config["image"],
            ports=[client.V1ContainerPort(container_port=config.get("port", 8080))],
            env=self._build_env_vars(config.get("env", [])),
            resources=self._build_resources(config.get("resources")),
        )

        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=deployment_name,
                labels={"app": deployment_name, "job-type": "inference"},
            ),
            spec=client.V1DeploymentSpec(
                replicas=config.get("replicas", 1),
                selector=client.V1LabelSelector(
                    match_labels={"app": deployment_name}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": deployment_name}),
                    spec=client.V1PodSpec(
                        containers=[container],
                        image_pull_secrets=[client.V1LocalObjectReference(name=s) for s in self.image_pull_secrets],
                    ),
                ),
            ),
        )

        return deployment

    def _build_workflow_spec(self, job: Job) -> Dict[str, Any]:
        """Build workflow spec (simplified DAG executor)."""
        # This is a simplified implementation
        # For production, use Argo Workflows
        return {
            "workflow_name": self._generate_job_name(job),
            "templates": job.executor_config.get("templates", []),
        }

    def _build_workflow_configmap(self, job: Job, workflow_name: str) -> Dict[str, Any]:
        """Build ConfigMap for workflow definition."""
        import json

        configmap = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=client.V1ObjectMeta(name=f"{workflow_name}-config"),
            data={
                "workflow.json": json.dumps(job.executor_config)
            },
        )
        return configmap

    def _build_workflow_controller_spec(self, job: Job, workflow_name: str) -> Dict[str, Any]:
        """Build K8s Job to control workflow execution."""
        container = client.V1Container(
            name="workflow-controller",
            image="python:3.10-slim",
            command=["python", "/scripts/workflow_executor.py"],
            volume_mounts=[
                client.V1VolumeMount(name="workflow-config", mount_path="/config"),
            ],
        )

        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": workflow_name}),
            spec=client.V1PodSpec(
                containers=[container],
                restart_policy="OnFailure",
                volumes=[
                    client.V1Volume(
                        name="workflow-config",
                        config_map=client.V1ConfigMapVolumeSource(
                            name=f"{workflow_name}-config"
                        ),
                    )
                ],
            ),
        )

        job_spec = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=workflow_name),
            spec=client.V1JobSpec(template=pod_template),
        )

        return job_spec

    def _build_service_spec(self, job: Job, deployment_name: str) -> Dict[str, Any]:
        """Build K8s Service spec."""
        config = job.executor_config.get("service", {})

        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=client.V1ServiceSpec(
                type=config.get("type", "ClusterIP"),
                selector={"app": deployment_name},
                ports=[
                    client.V1ServicePort(
                        port=config.get("port", 80),
                        target_port=config.get("targetPort", 8080),
                    )
                ],
            ),
        )

        return service

    def _generate_job_name(self, job: Job) -> str:
        """Generate unique K8s job name."""
        import re
        # K8s names must be DNS-1123 compliant
        name = re.sub(r'[^a-z0-9-]', '-', job.name.lower())
        name = name[:50]  # Truncate to max length
        return f"{name}-{str(job.id)[:8]}"

    def _build_env_vars(self, env_list: list) -> list:
        """Build K8s environment variables."""
        env_vars = []
        for env in env_list:
            if "value" in env:
                env_vars.append(client.V1EnvVar(name=env["name"], value=env["value"]))
            elif "valueFrom" in env:
                value_from = env["valueFrom"]
                if "secretKeyRef" in value_from:
                    secret_ref = value_from["secretKeyRef"]
                    env_vars.append(
                        client.V1EnvVar(
                            name=env["name"],
                            value_from=client.V1EnvVarSource(
                                secret_key_ref=client.V1SecretKeySelector(
                                    name=secret_ref["name"],
                                    key=secret_ref["key"],
                                )
                            ),
                        )
                    )
        return env_vars

    def _build_resources(self, resources_config: Optional[Dict]) -> Optional[client.V1ResourceRequirements]:
        """Build K8s resource requirements."""
        if not resources_config:
            return None

        return client.V1ResourceRequirements(
            requests=resources_config.get("requests"),
            limits=resources_config.get("limits"),
        )

    def _build_volume_mounts(self, mounts: list) -> list:
        """Build K8s volume mounts."""
        return [
            client.V1VolumeMount(
                name=mount["name"],
                mount_path=mount["mountPath"],
                sub_path=mount.get("subPath"),
                read_only=mount.get("readOnly", False),
            )
            for mount in mounts
        ]

    def _build_volumes(self, volumes: list) -> list:
        """Build K8s volumes."""
        volume_list = []
        for vol in volumes:
            if "persistentVolumeClaim" in vol:
                pvc = vol["persistentVolumeClaim"]
                volume_list.append(
                    client.V1Volume(
                        name=vol["name"],
                        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=pvc["claimName"]
                        ),
                    )
                )
            elif "emptyDir" in vol:
                volume_list.append(
                    client.V1Volume(
                        name=vol["name"],
                        empty_dir=client.V1EmptyDirVolumeSource(),
                    )
                )
        return volume_list

    def _build_tolerations(self, tolerations: list) -> list:
        """Build K8s tolerations."""
        return [
            client.V1Toleration(
                key=t.get("key"),
                operator=t.get("operator", "Equal"),
                value=t.get("value"),
                effect=t.get("effect"),
            )
            for t in tolerations
        ]

    def _parse_job_status(self, job: client.V1Job) -> JobStatusEnum:
        """Parse K8s Job status."""
        status = job.status

        if status.succeeded:
            return JobStatusEnum.SUCCEEDED
        elif status.failed:
            return JobStatusEnum.FAILED
        elif status.active:
            return JobStatusEnum.RUNNING
        else:
            return JobStatusEnum.PENDING

    def _parse_deployment_status(self, deployment: client.V1Deployment) -> JobStatusEnum:
        """Parse K8s Deployment status."""
        status = deployment.status

        if status.ready_replicas and status.ready_replicas == deployment.spec.replicas:
            return JobStatusEnum.RUNNING
        elif status.unavailable_replicas:
            return JobStatusEnum.PENDING
        else:
            return JobStatusEnum.QUEUED
