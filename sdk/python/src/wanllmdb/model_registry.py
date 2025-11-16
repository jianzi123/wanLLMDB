"""Model Registry for managing model versions and deployments."""

from typing import Optional, List, Dict, Any
import os
import time
from datetime import datetime

from wanllmdb.errors import WanLLMDBError
from wanllmdb.artifact import Artifact


class ModelRegistry:
    """Client for interacting with the Model Registry."""

    def __init__(self, api_client, project_id: str):
        """Initialize Model Registry client.

        Args:
            api_client: API client instance
            project_id: Project ID
        """
        self.api_client = api_client
        self.project_id = project_id

    def log_model(
        self,
        run,
        model_path: str,
        registered_model_name: str,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log a model to the registry.

        This creates a model artifact and registers it in the Model Registry.

        Args:
            run: Active run instance
            model_path: Path to model file or directory
            registered_model_name: Name of the registered model
            version: Version string (auto-generated if None)
            description: Version description
            tags: Tags for this version
            metadata: Additional metadata

        Returns:
            Dictionary with model version info

        Example:
            >>> registry = ModelRegistry(api_client, project_id)
            >>> version_info = registry.log_model(
            ...     run=run,
            ...     model_path="model.pkl",
            ...     registered_model_name="my-model",
            ...     version="v1.0.0",
            ...     tags=["production-ready"]
            ... )
        """
        if not run or not run.id:
            raise WanLLMDBError("No active run. Call wandb.init() first.")

        print(f"Logging model '{registered_model_name}' to registry...")

        # 1. Create or get registered model
        try:
            # Try to get existing model
            models_response = self.api_client.get(
                '/registry/models',
                params={'project_id': self.project_id, 'search': registered_model_name}
            )

            existing_model = None
            for model in models_response.get('items', []):
                if model['name'] == registered_model_name:
                    existing_model = model
                    break

            if existing_model:
                model_id = existing_model['id']
                print(f"  Using existing model: {registered_model_name}")
            else:
                # Create new registered model
                model_response = self.api_client.post(
                    '/registry/models',
                    data={
                        'name': registered_model_name,
                        'project_id': self.project_id,
                        'description': description or f"Model registered from run {run.name}",
                        'tags': tags or [],
                    }
                )
                model_id = model_response['id']
                print(f"  Created new model: {registered_model_name}")

        except Exception as e:
            raise WanLLMDBError(f"Failed to create/get registered model: {e}")

        # 2. Create model artifact
        artifact_name = f"{registered_model_name}-model"
        artifact = Artifact(
            name=artifact_name,
            type='model',
            description=description or f"Model {registered_model_name}"
        )

        # Add model files
        if os.path.isfile(model_path):
            artifact.add_file(model_path)
        elif os.path.isdir(model_path):
            artifact.add_dir(model_path)
        else:
            raise WanLLMDBError(f"Model path not found: {model_path}")

        # 3. Log artifact
        print(f"  Uploading model artifact...")
        artifact = run.log_artifact(artifact)

        # 4. Auto-generate version if not provided
        if version is None:
            # Use timestamp-based version
            version = f"v{int(time.time())}"

        # 5. Register model version
        try:
            version_response = self.api_client.post(
                f'/registry/models/{model_id}/versions',
                data={
                    'version': version,
                    'description': description,
                    'stage': 'none',
                    'run_id': run.id,
                    'artifact_version_id': artifact._version_id,
                    'metrics': dict(run.summary),
                    'tags': tags or [],
                    'metadata': metadata or {},
                }
            )
            print(f"  ✓ Registered version: {version}")
            print(f"  Model ID: {model_id}")
            print(f"  Version ID: {version_response['id']}")

            return {
                'model_id': model_id,
                'version_id': version_response['id'],
                'version': version,
                'artifact_version_id': artifact._version_id,
            }

        except Exception as e:
            raise WanLLMDBError(f"Failed to register model version: {e}")

    def use_model(
        self,
        registered_model_name: str,
        version: Optional[str] = None,
        stage: Optional[str] = None,
        download_path: Optional[str] = None,
    ) -> str:
        """Use a registered model.

        Downloads a model version from the registry.

        Args:
            registered_model_name: Name of the registered model
            version: Specific version to use (e.g., "v1.0.0")
            stage: Stage to use (e.g., "production", "staging")
            download_path: Path to download model to (default: ~/.wanllmdb/models/)

        Returns:
            Path to downloaded model

        Example:
            >>> registry = ModelRegistry(api_client, project_id)
            >>> model_path = registry.use_model(
            ...     registered_model_name="my-model",
            ...     stage="production"
            ... )
        """
        print(f"Loading model '{registered_model_name}' from registry...")

        # 1. Get registered model
        try:
            models_response = self.api_client.get(
                '/registry/models',
                params={'project_id': self.project_id, 'search': registered_model_name}
            )

            model = None
            for m in models_response.get('items', []):
                if m['name'] == registered_model_name:
                    model = m
                    break

            if not model:
                raise WanLLMDBError(f"Model '{registered_model_name}' not found")

            model_id = model['id']

        except Exception as e:
            raise WanLLMDBError(f"Failed to get model: {e}")

        # 2. Get model version
        try:
            if stage:
                # Get latest version in stage
                version_response = self.api_client.get(
                    f'/registry/models/stages/{stage}/latest',
                    params={'model_id': model_id}
                )
                print(f"  Using latest version in stage '{stage}': {version_response['version']}")

            elif version:
                # Get specific version
                version_response = self.api_client.get(
                    f'/registry/models/{model_id}/versions/{version}'
                )
                print(f"  Using version: {version}")

            else:
                # Get latest version (any stage)
                versions_response = self.api_client.get(
                    f'/registry/models/{model_id}/versions',
                    params={'limit': 1}
                )
                if not versions_response.get('items'):
                    raise WanLLMDBError(f"No versions found for model '{registered_model_name}'")

                version_response = versions_response['items'][0]
                print(f"  Using latest version: {version_response['version']}")

        except Exception as e:
            raise WanLLMDBError(f"Failed to get model version: {e}")

        # 3. Get artifact version
        artifact_version_id = version_response.get('artifact_version_id')
        if not artifact_version_id:
            raise WanLLMDBError("Model version has no associated artifact")

        # 4. Download artifact
        try:
            # Get artifact version details
            artifact_version = self.api_client.get(f'/artifacts/versions/{artifact_version_id}')
            artifact_id = artifact_version['artifact_id']

            # Create Artifact instance for download
            artifact = Artifact(
                name=registered_model_name,
                type='model'
            )
            artifact._artifact_id = artifact_id
            artifact._version_id = artifact_version_id
            artifact._version = artifact_version['version']
            artifact._project_id = self.project_id

            # Download
            if download_path is None:
                download_path = os.path.join(
                    os.path.expanduser("~/.wanllmdb/models"),
                    registered_model_name,
                    version_response['version']
                )

            model_path = artifact.download(root=download_path)
            print(f"  ✓ Model downloaded to: {model_path}")

            return model_path

        except Exception as e:
            raise WanLLMDBError(f"Failed to download model: {e}")

    def transition_stage(
        self,
        registered_model_name: str,
        version: str,
        stage: str,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transition a model version to a different stage.

        Args:
            registered_model_name: Name of the registered model
            version: Version string
            stage: Target stage ('staging', 'production', 'archived')
            comment: Transition comment

        Returns:
            Updated model version

        Example:
            >>> registry.transition_stage(
            ...     registered_model_name="my-model",
            ...     version="v1.0.0",
            ...     stage="production",
            ...     comment="Passed all tests"
            ... )
        """
        # 1. Get model
        try:
            models_response = self.api_client.get(
                '/registry/models',
                params={'project_id': self.project_id, 'search': registered_model_name}
            )

            model = None
            for m in models_response.get('items', []):
                if m['name'] == registered_model_name:
                    model = m
                    break

            if not model:
                raise WanLLMDBError(f"Model '{registered_model_name}' not found")

            model_id = model['id']

        except Exception as e:
            raise WanLLMDBError(f"Failed to get model: {e}")

        # 2. Get version
        try:
            version_response = self.api_client.get(
                f'/registry/models/{model_id}/versions/{version}'
            )
            version_id = version_response['id']

        except Exception as e:
            raise WanLLMDBError(f"Failed to get version: {e}")

        # 3. Transition stage
        try:
            updated_version = self.api_client.post(
                f'/registry/models/versions/{version_id}/transition',
                data={
                    'stage': stage,
                    'comment': comment,
                }
            )
            print(f"✓ Transitioned {registered_model_name}:{version} to {stage}")
            return updated_version

        except Exception as e:
            raise WanLLMDBError(f"Failed to transition stage: {e}")

    def list_models(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """List registered models in the project.

        Args:
            search: Search in model names

        Returns:
            List of registered models
        """
        try:
            response = self.api_client.get(
                '/registry/models',
                params={
                    'project_id': self.project_id,
                    'search': search,
                    'limit': 100,
                }
            )
            return response.get('items', [])

        except Exception as e:
            raise WanLLMDBError(f"Failed to list models: {e}")

    def get_model_versions(
        self,
        registered_model_name: str,
        stage: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get versions of a registered model.

        Args:
            registered_model_name: Name of the registered model
            stage: Filter by stage

        Returns:
            List of model versions
        """
        # Get model
        models_response = self.api_client.get(
            '/registry/models',
            params={'project_id': self.project_id, 'search': registered_model_name}
        )

        model = None
        for m in models_response.get('items', []):
            if m['name'] == registered_model_name:
                model = m
                break

        if not model:
            raise WanLLMDBError(f"Model '{registered_model_name}' not found")

        # Get versions
        params = {'limit': 100}
        if stage:
            params['stage'] = stage

        response = self.api_client.get(
            f'/registry/models/{model["id"]}/versions',
            params=params
        )
        return response.get('items', [])
