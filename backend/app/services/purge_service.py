"""
Data Purge Service for DeviationEngine.

This service provides functionality to completely reset the application data
while preserving:
- Ground truth historical data (vector store + markdown files)
- Configuration settings (LLM, translation, audio presets)
"""

import logging
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from sqlalchemy import update

from app.db_models import (
    TimelineDB,
    SkeletonDB,
    AudioScriptDB,
    AudioFileDB,
    VectorStoreIndexDB,
    ImagePromptSkeletonDB,
    ScriptTranslationDB,
    LLMConfigDB,
    AgentLLMConfigDB,
    TranslationConfigDB,
)

logger = logging.getLogger(__name__)


class PurgeService:
    """Service for purging application data."""

    def __init__(self, data_dir: Path):
        """
        Initialize purge service.

        Args:
            data_dir: Path to backend data directory
        """
        self.data_dir = data_dir
        self.audio_dir = data_dir / "audio"
        self.images_dir = data_dir / "images"
        self.agent_prompts_dir = data_dir / "agent_prompts"
        self.vector_store_dir = data_dir / "vector_store"

    async def purge_all_data(
        self,
        db: AsyncSession,
        preserve_ground_truth: bool = True
    ) -> Dict[str, Any]:
        """
        Purge all user-generated data from the system.

        This removes:
        - All timelines and their generations (cascades to all related data)
        - All skeleton drafts (workflow drafts)
        - All audio scripts and audio files
        - Vector store data (except ground truth if preserve_ground_truth=True)
        - Generated audio files from filesystem
        - Generated image files from filesystem
        - Agent prompt logs

        This preserves:
        - Configuration settings (LLM, translation, presets)
        - Ground truth historical data (if preserve_ground_truth=True)

        Args:
            db: Database session
            preserve_ground_truth: If True, preserve ground truth data (default: True)

        Returns:
            Dictionary with purge statistics
        """
        logger.warning("Starting complete data purge...")

        stats = {
            "timelines_deleted": 0,
            "skeletons_deleted": 0,
            "image_prompts_deleted": 0,
            "script_translations_deleted": 0,
            "audio_scripts_deleted": 0,
            "audio_files_deleted": 0,
            "vector_indices_deleted": 0,
            "filesystem_audio_deleted": 0,
            "filesystem_images_deleted": 0,
            "filesystem_prompts_deleted": 0,
            "vector_store_purged": False,
            "api_keys_cleared": False,
            "errors": []
        }

        try:
            # 1. Delete all timelines (cascades to generations, media, etc.)
            result = await db.execute(select(TimelineDB))
            timelines = result.scalars().all()
            timeline_count = len(timelines)

            if timeline_count > 0:
                await db.execute(delete(TimelineDB))
                stats["timelines_deleted"] = timeline_count
                logger.info(f"Deleted {timeline_count} timelines (cascaded to all related data)")

            # 2. Delete all skeletons (they have SET NULL on timeline delete, so they're orphaned)
            # These are draft timelines that may or may not be associated with actual timelines
            result = await db.execute(select(SkeletonDB))
            skeletons = result.scalars().all()
            skeleton_count = len(skeletons)

            if skeleton_count > 0:
                await db.execute(delete(SkeletonDB))
                stats["skeletons_deleted"] = skeleton_count
                logger.info(f"Deleted {skeleton_count} skeletons (draft timelines)")

            # 3. Delete all orphaned image prompt skeletons
            # These can have NULL timeline_id and generation_id
            result = await db.execute(select(ImagePromptSkeletonDB))
            image_prompts = result.scalars().all()
            image_prompt_count = len(image_prompts)

            if image_prompt_count > 0:
                await db.execute(delete(ImagePromptSkeletonDB))
                stats["image_prompts_deleted"] = image_prompt_count
                logger.info(f"Deleted {image_prompt_count} image prompt skeletons")

            # 4. Delete all script translations (orphaned after audio scripts are deleted)
            result = await db.execute(select(ScriptTranslationDB))
            script_translations = result.scalars().all()
            script_translation_count = len(script_translations)

            if script_translation_count > 0:
                await db.execute(delete(ScriptTranslationDB))
                stats["script_translations_deleted"] = script_translation_count
                logger.info(f"Deleted {script_translation_count} script translations")

            # 5. Delete all audio scripts and files
            result = await db.execute(select(AudioScriptDB))
            scripts = result.scalars().all()
            script_count = len(scripts)

            if script_count > 0:
                await db.execute(delete(AudioScriptDB))
                stats["audio_scripts_deleted"] = script_count
                logger.info(f"Deleted {script_count} audio scripts")

            result = await db.execute(select(AudioFileDB))
            audio_files = result.scalars().all()
            audio_file_count = len(audio_files)

            if audio_file_count > 0:
                await db.execute(delete(AudioFileDB))
                stats["audio_files_deleted"] = audio_file_count
                logger.info(f"Deleted {audio_file_count} audio file records")

            # 6. Delete vector store index records (except ground truth if preserving)
            if preserve_ground_truth:
                # Delete only non-ground-truth indices
                await db.execute(
                    delete(VectorStoreIndexDB).where(
                        VectorStoreIndexDB.content_type != "ground_truth"
                    )
                )
                logger.info("Deleted vector store indices (preserved ground truth)")
            else:
                # Delete all vector store indices
                result = await db.execute(select(VectorStoreIndexDB))
                indices = result.scalars().all()
                index_count = len(indices)
                await db.execute(delete(VectorStoreIndexDB))
                stats["vector_indices_deleted"] = index_count
                logger.info(f"Deleted {index_count} vector store index records")

            # 7. Clear stored API keys from config tables
            # (rows are preserved — the app needs them — only the key values are wiped)
            await db.execute(
                update(LLMConfigDB).values(api_key_google=None, api_key_openrouter=None)
            )
            await db.execute(
                update(AgentLLMConfigDB).values(api_key_google=None, api_key_openrouter=None)
            )
            # TranslationConfigDB.api_key is NOT NULL, so reset to sentinel + disable
            await db.execute(
                update(TranslationConfigDB).values(api_key="not_configured", enabled=0)
            )
            stats["api_keys_cleared"] = True
            logger.info("Cleared API keys from llm_config, agent_llm_configs, and translation_config")

            # Commit database changes
            await db.commit()
            logger.info("Database purge committed successfully")

        except Exception as e:
            logger.error(f"Error during database purge: {e}")
            stats["errors"].append(f"Database error: {str(e)}")
            await db.rollback()
            raise

        # 7. Clean up filesystem: audio files
        try:
            if self.audio_dir.exists():
                audio_files = list(self.audio_dir.glob("*.mp3")) + list(self.audio_dir.glob("*.wav"))
                for audio_file in audio_files:
                    try:
                        audio_file.unlink()
                        stats["filesystem_audio_deleted"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete audio file {audio_file}: {e}")
                logger.info(f"Deleted {stats['filesystem_audio_deleted']} audio files from filesystem")
        except Exception as e:
            logger.error(f"Error cleaning audio directory: {e}")
            stats["errors"].append(f"Audio filesystem error: {str(e)}")

        # 8. Clean up filesystem: image files
        try:
            if self.images_dir.exists():
                image_files = list(self.images_dir.glob("*"))
                for image_file in image_files:
                    if image_file.is_file():
                        try:
                            image_file.unlink()
                            stats["filesystem_images_deleted"] += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete image {image_file}: {e}")
                logger.info(f"Deleted {stats['filesystem_images_deleted']} images from filesystem")
        except Exception as e:
            logger.error(f"Error cleaning images directory: {e}")
            stats["errors"].append(f"Images filesystem error: {str(e)}")

        # 9. Clean up agent prompt logs
        try:
            if self.agent_prompts_dir.exists():
                prompt_files = list(self.agent_prompts_dir.glob("*.txt"))
                for prompt_file in prompt_files:
                    try:
                        prompt_file.unlink()
                        stats["filesystem_prompts_deleted"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete prompt log {prompt_file}: {e}")
                logger.info(f"Deleted {stats['filesystem_prompts_deleted']} agent prompt logs")
        except Exception as e:
            logger.error(f"Error cleaning agent prompts directory: {e}")
            stats["errors"].append(f"Agent prompts filesystem error: {str(e)}")

        # 10. Purge vector store (ChromaDB collections)
        try:
            from app.services.vector_store_service import get_vector_store_service

            vector_service = get_vector_store_service()

            if vector_service.enabled:
                # Clear generated reports collection
                if "reports" in vector_service.collections:
                    try:
                        collection = vector_service.collections["reports"]
                        # Use delete without IDs to clear entire collection
                        # ChromaDB allows delete with where={} to delete all
                        try:
                            # Method 1: Try getting all IDs and deleting
                            result = collection.get()
                            if result and result.get("ids"):
                                all_ids = result["ids"]
                                collection.delete(ids=all_ids)
                                logger.info(f"Cleared {len(all_ids)} documents from reports collection")
                            else:
                                logger.info("Reports collection is already empty")
                        except Exception as e:
                            # Method 2: Try resetting the collection
                            logger.warning(f"Standard delete failed, trying collection reset: {e}")
                            vector_service.client.delete_collection("generated_reports")
                            vector_service.client.get_or_create_collection("generated_reports")
                            logger.info("Reset reports collection")
                    except Exception as e:
                        logger.error(f"Failed to clear reports collection: {e}")
                        stats["errors"].append(f"Reports collection error: {str(e)}")

                # Clear generated narratives collection
                if "narratives" in vector_service.collections:
                    try:
                        collection = vector_service.collections["narratives"]
                        try:
                            result = collection.get()
                            if result and result.get("ids"):
                                all_ids = result["ids"]
                                collection.delete(ids=all_ids)
                                logger.info(f"Cleared {len(all_ids)} documents from narratives collection")
                            else:
                                logger.info("Narratives collection is already empty")
                        except Exception as e:
                            logger.warning(f"Standard delete failed, trying collection reset: {e}")
                            vector_service.client.delete_collection("generated_narratives")
                            vector_service.client.get_or_create_collection("generated_narratives")
                            logger.info("Reset narratives collection")
                    except Exception as e:
                        logger.error(f"Failed to clear narratives collection: {e}")
                        stats["errors"].append(f"Narratives collection error: {str(e)}")

                # Optionally clear ground truth collection
                if not preserve_ground_truth and "ground_truth" in vector_service.collections:
                    try:
                        collection = vector_service.collections["ground_truth"]
                        try:
                            result = collection.get()
                            if result and result.get("ids"):
                                all_ids = result["ids"]
                                collection.delete(ids=all_ids)
                                logger.info(f"Cleared {len(all_ids)} documents from ground_truth collection")
                            else:
                                logger.info("Ground truth collection is already empty")
                        except Exception as e:
                            logger.warning(f"Standard delete failed, trying collection reset: {e}")
                            vector_service.client.delete_collection("ground_truth_events")
                            vector_service.client.get_or_create_collection("ground_truth_events")
                            logger.info("Reset ground truth collection")
                    except Exception as e:
                        logger.error(f"Failed to clear ground_truth collection: {e}")
                        stats["errors"].append(f"Ground truth collection error: {str(e)}")
                else:
                    logger.info("Preserved ground truth vector store collection")

                stats["vector_store_purged"] = True
            else:
                logger.warning("Vector store service is disabled, skipping vector store purge")

        except Exception as e:
            logger.error(f"Error during vector store purge: {e}")
            stats["errors"].append(f"Vector store error: {str(e)}")

        # Log summary
        logger.warning("=" * 80)
        logger.warning("DATA PURGE COMPLETE")
        logger.warning("=" * 80)
        logger.warning(f"Timelines deleted: {stats['timelines_deleted']}")
        logger.warning(f"Skeletons deleted: {stats['skeletons_deleted']}")
        logger.warning(f"Image prompts deleted: {stats['image_prompts_deleted']}")
        logger.warning(f"Script translations deleted: {stats['script_translations_deleted']}")
        logger.warning(f"Audio scripts deleted: {stats['audio_scripts_deleted']}")
        logger.warning(f"Audio files deleted: {stats['audio_files_deleted']}")
        logger.warning(f"Vector indices deleted: {stats['vector_indices_deleted']}")
        logger.warning(f"Filesystem audio deleted: {stats['filesystem_audio_deleted']}")
        logger.warning(f"Filesystem images deleted: {stats['filesystem_images_deleted']}")
        logger.warning(f"Agent prompt logs deleted: {stats['filesystem_prompts_deleted']}")
        logger.warning(f"Vector store purged: {stats['vector_store_purged']}")
        logger.warning(f"API keys cleared: {stats['api_keys_cleared']}")
        logger.warning(f"Ground truth preserved: {preserve_ground_truth}")

        if stats["errors"]:
            logger.error(f"Errors encountered: {len(stats['errors'])}")
            for error in stats["errors"]:
                logger.error(f"  - {error}")
        else:
            logger.warning("No errors encountered ✓")

        logger.warning("=" * 80)

        return stats


def get_purge_service() -> PurgeService:
    """
    Get purge service instance.

    Returns:
        PurgeService instance configured with default data directory
    """
    from pathlib import Path
    data_dir = Path(__file__).parent.parent.parent / "data"
    return PurgeService(data_dir)
