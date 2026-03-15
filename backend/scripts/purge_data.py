#!/usr/bin/env python3
"""
CLI script to purge all user-generated data from DeviationEngine.

⚠️  DANGER: This script permanently deletes all timelines, generations, media, and vector data.
Only configuration settings and (optionally) ground truth historical data are preserved.

Usage:
    python scripts/purge_data.py [--include-ground-truth]

Options:
    --include-ground-truth     Also delete ground truth data (default: preserve ground truth)
    --yes                      Skip confirmation prompt (use with caution!)
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.services.purge_service import get_purge_service
from dotenv import load_dotenv


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def confirm_purge(preserve_ground_truth: bool) -> bool:
    """
    Ask user for confirmation before proceeding with purge.

    Args:
        preserve_ground_truth: Whether ground truth will be preserved

    Returns:
        True if user confirms, False otherwise
    """
    print()
    print("=" * 80)
    print("⚠️  WARNING: DATA PURGE OPERATION")
    print("=" * 80)
    print()
    print("This will PERMANENTLY DELETE:")
    print("  ✗ All timelines and generations")
    print("  ✗ All skeleton drafts (workflow drafts)")
    print("  ✗ All audio scripts and audio files")
    print("  ✗ All images and media")
    print("  ✗ Vector store data (generated reports and narratives)")
    print("  ✗ Agent prompt logs")
    print()
    print("This will PRESERVE:")
    print("  ✓ LLM configuration")
    print("  ✓ Translation configuration")
    print("  ✓ Audio script presets")

    if preserve_ground_truth:
        print("  ✓ Ground truth historical data")
    else:
        print("  ✗ Ground truth historical data (WILL BE DELETED)")

    print()
    print("=" * 80)
    print()

    response = input("Are you ABSOLUTELY SURE you want to proceed? Type 'DELETE' to confirm: ")
    return response.strip() == "DELETE"


async def main(include_ground_truth: bool = False, skip_confirmation: bool = False):
    """
    Main purge function.

    Args:
        include_ground_truth: If True, also delete ground truth data
        skip_confirmation: If True, skip confirmation prompt
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    # Load environment variables
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded .env from {env_path}")

    preserve_ground_truth = not include_ground_truth

    # Confirm with user unless --yes flag provided
    if not skip_confirmation:
        if not confirm_purge(preserve_ground_truth):
            print()
            print("❌ Purge operation cancelled by user")
            print()
            return 1

    print()
    print("=" * 80)
    print("🔥 Starting data purge...")
    print("=" * 80)
    print()

    try:
        # Get purge service
        purge_service = get_purge_service()

        # Create database session and execute purge
        async with AsyncSessionLocal() as db:
            stats = await purge_service.purge_all_data(
                db=db,
                preserve_ground_truth=preserve_ground_truth
            )

        # Print results
        print()
        print("=" * 80)
        print("✅ PURGE COMPLETE")
        print("=" * 80)
        print()
        print(f"Timelines deleted: {stats['timelines_deleted']}")
        print(f"Skeleton drafts deleted: {stats['skeletons_deleted']}")
        print(f"Audio scripts deleted: {stats['audio_scripts_deleted']}")
        print(f"Audio files deleted: {stats['audio_files_deleted']}")
        print(f"Vector indices deleted: {stats['vector_indices_deleted']}")
        print(f"Filesystem audio deleted: {stats['filesystem_audio_deleted']}")
        print(f"Filesystem images deleted: {stats['filesystem_images_deleted']}")
        print(f"Agent prompt logs deleted: {stats['filesystem_prompts_deleted']}")
        print(f"Vector store purged: {stats['vector_store_purged']}")
        print(f"Ground truth preserved: {preserve_ground_truth}")

        if stats["errors"]:
            print()
            print(f"⚠️  {len(stats['errors'])} errors encountered:")
            for error in stats["errors"]:
                print(f"  - {error}")
            print()
            return 1
        else:
            print()
            print("✓ No errors encountered")
            print()

        print("=" * 80)
        print()
        print("The database is now clean and ready for new timelines.")
        print()

        return 0

    except Exception as e:
        logger.exception(f"Fatal error during purge: {e}")
        print()
        print("=" * 80)
        print("❌ PURGE FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        print("Check the logs above for details.")
        print()
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="⚠️  Purge all user-generated data from DeviationEngine"
    )
    parser.add_argument(
        "--include-ground-truth",
        action="store_true",
        help="Also delete ground truth historical data (default: preserve ground truth)"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (DANGEROUS!)"
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(
        include_ground_truth=args.include_ground_truth,
        skip_confirmation=args.yes
    ))
    sys.exit(exit_code)
