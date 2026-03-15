#!/usr/bin/env python3
"""
CLI script to index ground truth historical data into vector store.

Usage:
    python scripts/index_ground_truth.py [--force] [--debug]

Options:
    --force     Force re-indexing even if files already indexed
    --debug     Enable debug logging
"""

import asyncio
import sys
import os
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.services.vector_store_service import get_vector_store_service
from dotenv import load_dotenv


def setup_logging(debug: bool = False):
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


async def main(force: bool = False, debug: bool = False):
    """
    Main indexing function.

    Args:
        force: Force re-indexing
        debug: Enable debug mode
    """
    setup_logging(debug)
    logger = logging.getLogger(__name__)

    # Load environment variables
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded .env from {env_path}")
    else:
        logger.warning(f"No .env file found at {env_path}")

    # Check for required API key
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY not set in environment")
        logger.error("Please create a .env file with your GEMINI_API_KEY")
        return 1

    # Check if vector store is enabled
    if os.getenv("VECTOR_STORE_ENABLED", "true").lower() != "true":
        logger.error("Vector store is disabled (VECTOR_STORE_ENABLED=false)")
        logger.error("Set VECTOR_STORE_ENABLED=true in .env to continue")
        return 1

    logger.info("=" * 80)
    logger.info("Ground Truth Indexing Script")
    logger.info("=" * 80)
    logger.info(f"Force re-index: {force}")
    logger.info(f"Debug mode: {debug}")
    logger.info("")

    try:
        # Get vector store service
        vector_service = get_vector_store_service()

        if not vector_service.enabled:
            logger.error("Vector store service failed to initialize")
            return 1

        logger.info(f"Vector store initialized:")
        logger.info(f"  - Model: {vector_service.embedding_model_name}")
        logger.info(f"  - Dimensions: {vector_service.embedding_dimensions}")
        logger.info(f"  - Persistence: {vector_service.persist_directory}")
        logger.info("")

        # Path to ground truth data
        ground_truth_dir = Path(__file__).parent.parent / "data" / "ground_truth"

        if not ground_truth_dir.exists():
            logger.error(f"Ground truth directory not found: {ground_truth_dir}")
            return 1

        # Count markdown files
        md_files = list(ground_truth_dir.glob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files in {ground_truth_dir}")
        logger.info("")

        if not md_files:
            logger.warning("No markdown files to index")
            return 0

        # Create database session
        async with AsyncSessionLocal() as db:
            # Index ground truth reports
            stats = await vector_service.index_ground_truth_reports(
                ground_truth_dir=str(ground_truth_dir),
                db=db,
                force_reindex=force
            )

            # Print results
            logger.info("")
            logger.info("=" * 80)
            logger.info("Indexing Complete")
            logger.info("=" * 80)
            logger.info(f"Files processed: {stats.get('files_processed', 0)}")
            logger.info(f"Files skipped: {stats.get('files_skipped', 0)}")
            logger.info(f"Chunks indexed: {stats.get('chunks_indexed', 0)}")

            if stats.get("errors"):
                logger.error(f"Errors encountered: {len(stats['errors'])}")
                for error in stats["errors"]:
                    logger.error(f"  - {error}")
            else:
                logger.info("No errors encountered ✓")

            # Get final stats
            logger.info("")
            logger.info("Vector Store Stats:")
            vector_stats = await vector_service.get_stats(db)

            if vector_stats.get("collections"):
                for collection_name, collection_info in vector_stats["collections"].items():
                    logger.info(f"  - {collection_name}: {collection_info['count']} documents")

        logger.info("")
        logger.info("=" * 80)
        logger.info("✓ Ground truth indexing completed successfully")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.exception(f"Fatal error during indexing: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Index ground truth historical data into vector store"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing even if files already indexed"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(force=args.force, debug=args.debug))
    sys.exit(exit_code)
