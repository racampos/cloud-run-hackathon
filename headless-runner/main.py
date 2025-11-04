"""Headless Runner - Cloud Run Job Entry Point."""

import asyncio
import json
import os
import sys
import argparse
import structlog

from runner.models import RunnerPayload
from runner.executor import HeadlessExecutor

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


async def main():
    """Main entry point for headless runner job."""
    parser = argparse.ArgumentParser(description="NetGenius Headless Runner")
    parser.add_argument(
        "--payload",
        type=str,
        help="JSON payload string or path to payload file",
    )
    parser.add_argument(
        "--payload-file",
        type=str,
        help="Path to payload JSON file",
    )
    parser.add_argument(
        "--gcs-bucket",
        type=str,
        default=os.getenv("GCS_BUCKET", "netgenius-artifacts-dev"),
        help="GCS bucket for artifacts",
    )

    args = parser.parse_args()

    # Load payload
    payload_data = None

    # Try environment variable first (for Cloud Run Jobs)
    if os.getenv("PAYLOAD_JSON"):
        logger.info("loading_payload_from_env")
        payload_data = json.loads(os.getenv("PAYLOAD_JSON"))

    # Try command line argument
    elif args.payload:
        logger.info("loading_payload_from_arg")
        try:
            payload_data = json.loads(args.payload)
        except json.JSONDecodeError:
            # Maybe it's a file path
            with open(args.payload, "r") as f:
                payload_data = json.load(f)

    # Try file argument
    elif args.payload_file:
        logger.info("loading_payload_from_file", file=args.payload_file)
        with open(args.payload_file, "r") as f:
            payload_data = json.load(f)

    if not payload_data:
        logger.error("no_payload_provided")
        print("ERROR: No payload provided. Use --payload, --payload-file, or PAYLOAD_JSON env var.")
        sys.exit(1)

    try:
        # Parse and validate payload
        payload = RunnerPayload(**payload_data)
        logger.info(
            "payload_validated",
            exercise_id=payload.exercise_id,
            num_devices=len(payload.devices),
        )

        # Execute simulation
        executor = HeadlessExecutor(payload, args.gcs_bucket)
        summary = await executor.execute()

        # Print summary to stdout
        print(json.dumps(summary.model_dump(), indent=2))

        # Exit with appropriate code
        if summary.success:
            logger.info("job_succeeded", build_id=summary.build_id)
            sys.exit(0)
        else:
            logger.error("job_failed", build_id=summary.build_id, error=summary.error)
            sys.exit(1)

    except Exception as e:
        logger.error("job_crashed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
