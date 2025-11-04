"""Headless execution engine."""

import time
import uuid
from .models import RunnerPayload, ExecutionSummary
from .artifacts import ArtifactWriter
import structlog

logger = structlog.get_logger()


class HeadlessExecutor:
    """Executes lab simulation and captures artifacts."""

    def __init__(self, payload: RunnerPayload, gcs_bucket: str):
        """
        Initialize executor.

        Args:
            payload: Runner payload with topology and device configs
            gcs_bucket: GCS bucket name for artifacts
        """
        self.payload = payload
        self.exercise_id = payload.exercise_id
        self.build_id = self._generate_build_id()
        self.artifacts = ArtifactWriter(gcs_bucket, self.exercise_id, self.build_id)
        self.start_time = time.time()

    def _generate_build_id(self) -> str:
        """Generate unique build ID."""
        return f"build-{uuid.uuid4().hex[:8]}"

    async def execute(self) -> ExecutionSummary:
        """
        Execute simulation (stub implementation).

        This is a stub for M1. It logs what would be executed and creates
        dummy artifacts.
        """
        logger.info(
            "execution_starting",
            exercise_id=self.exercise_id,
            build_id=self.build_id,
            num_devices=len(self.payload.devices),
        )

        try:
            # Stub: Log topology
            logger.info(
                "topology_loaded",
                topology_length=len(self.payload.topology_yaml),
            )

            # Stub: Process each device
            device_histories = {}
            for device_name, device_spec in self.payload.devices.items():
                logger.info(
                    "processing_device",
                    device=device_name,
                    platform=device_spec.platform,
                    num_initial=len(device_spec.initial),
                    num_steps=len(device_spec.steps),
                )

                # Simulate execution history
                history = []

                # Log initial config
                for cmd in device_spec.initial:
                    history.append({
                        "type": "initial_config",
                        "command": cmd,
                        "output": f"[STUB] Would execute: {cmd}",
                        "timestamp": time.time(),
                    })

                # Log steps
                for step in device_spec.steps:
                    history.append({
                        "type": step.type,
                        "command": step.value,
                        "output": f"[STUB] Would execute {step.type}: {step.value}",
                        "timestamp": time.time(),
                    })

                device_histories[device_name] = history

            # Write artifacts
            duration = time.time() - self.start_time

            await self.artifacts.write_json("device_histories.json", device_histories)
            await self.artifacts.write_text("topology.yaml", self.payload.topology_yaml)

            # Write dummy configs
            for device_name in self.payload.devices.keys():
                await self.artifacts.write_text(
                    f"initial_config/{device_name}.txt",
                    f"! Initial config for {device_name}\n! [STUB]\n",
                )
                await self.artifacts.write_text(
                    f"final_config/{device_name}.txt",
                    f"! Final config for {device_name}\n! [STUB]\n",
                )

            # Create summary
            summary = ExecutionSummary(
                success=True,
                exercise_id=self.exercise_id,
                build_id=self.build_id,
                duration_seconds=duration,
                devices=list(self.payload.devices.keys()),
            )

            await self.artifacts.write_json("summary.json", summary.model_dump())

            logger.info(
                "execution_completed",
                exercise_id=self.exercise_id,
                build_id=self.build_id,
                duration=duration,
                success=True,
            )

            return summary

        except Exception as e:
            logger.error(
                "execution_failed",
                exercise_id=self.exercise_id,
                build_id=self.build_id,
                error=str(e),
                exc_info=True,
            )

            summary = ExecutionSummary(
                success=False,
                exercise_id=self.exercise_id,
                build_id=self.build_id,
                duration_seconds=time.time() - self.start_time,
                error=str(e),
            )

            await self.artifacts.write_json("summary.json", summary.model_dump())
            return summary
