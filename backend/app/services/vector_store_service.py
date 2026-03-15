"""
Vector Store Service for RAG (Retrieval-Augmented Generation).

This service manages ChromaDB collections for:
- Ground truth historical events (1880-1970 markdown files)
- Generated reports (structured 8-section reports)
- Generated narratives (storyteller prose)

Uses sentence-transformers for local embedding generation (fully offline).
"""

import os
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timezone
from uuid import uuid4

import chromadb
from chromadb.config import Settings
from google import genai
from google.genai import types as genai_types
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db_models import VectorStoreIndexDB

logger = logging.getLogger(__name__)

# Global singleton instance
_vector_store_service: Optional["VectorStoreService"] = None


class VectorStoreService:
    """
    Manages vector database operations for RAG.

    Collections:
    - ground_truth_events: Historical facts from markdown files
    - generated_reports: Structured reports from historian/skeleton_historian agents
    - generated_narratives: Narrative prose from storyteller agent
    """

    def __init__(self, persist_directory: Optional[str] = None, embedding_model: Optional[str] = None):
        """
        Initialize vector store service.

        Args:
            persist_directory: Path to ChromaDB persistence directory (default: from env)
            embedding_model: Sentence-transformers model name (default: from env)
        """
        # Configuration from environment
        self.debug = os.getenv("RAG_DEBUG_MODE", "false").lower() == "true"
        self.enabled = os.getenv("VECTOR_STORE_ENABLED", "true").lower() == "true"

        # Paths and models
        self.persist_directory = persist_directory or os.getenv(
            "VECTOR_STORE_PATH",
            "data/vector_store"
        )
        self.embedding_model_name = embedding_model or os.getenv(
            "EMBEDDING_MODEL",
            "gemini-embedding-001"
        )
        self.embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
        self.embedding_task_type = os.getenv("EMBEDDING_TASK_TYPE", "RETRIEVAL_DOCUMENT")
        self.embedding_query_task_type = os.getenv("EMBEDDING_QUERY_TASK_TYPE", "RETRIEVAL_QUERY")

        # Get Gemini API key
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        # Retrieval parameters
        self.ground_truth_top_k = int(os.getenv("RAG_GROUND_TRUTH_TOP_K", "10"))
        self.previous_gen_top_k = int(os.getenv("RAG_PREVIOUS_GEN_TOP_K", "8"))
        self.chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "800"))
        self.chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))
        self.query_count = int(os.getenv("RAG_QUERY_COUNT", "4"))

        # Initialize components
        self.client: Optional[chromadb.ClientAPI] = None
        self.collections: Dict[str, Any] = {}

        # Collection names
        self.collection_names = {
            "ground_truth": "ground_truth_events",
            "reports": "generated_reports",
            "narratives": "generated_narratives",
            "historical_figures": "historical_figures",
        }

        if self.enabled:
            self._initialize()
        else:
            logger.info("Vector store disabled (VECTOR_STORE_ENABLED=false)")

    def _initialize(self):
        """Initialize ChromaDB client and Gemini API."""
        try:
            # Create persistence directory if it doesn't exist
            persist_path = Path(self.persist_directory)
            persist_path.mkdir(parents=True, exist_ok=True)

            # Initialize ChromaDB client with persistence
            logger.info(f"Initializing ChromaDB at {self.persist_directory}")
            self.client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            self.genai_client: Optional[genai.Client] = None  # created lazily on first embed
            logger.info(f"Gemini embedding model: {self.embedding_model_name} ({self.embedding_dimensions} dimensions)")

            # Initialize collections
            self._initialize_collections()

            if self.debug:
                logger.debug("Vector store initialized in DEBUG mode")

        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            self.enabled = False
            raise

    def _initialize_collections(self):
        """Create or get ChromaDB collections."""
        for key, collection_name in self.collection_names.items():
            try:
                collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": f"Collection for {key}"}
                )
                self.collections[key] = collection
                logger.info(f"Collection '{collection_name}' ready ({collection.count()} documents)")
            except Exception as e:
                logger.error(f"Failed to initialize collection '{collection_name}': {e}")
                raise

    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """
        Normalize embedding vector for accurate similarity comparisons.

        Required for dimensions < 3,072 per Gemini docs.
        """
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        if norm == 0:
            return embedding
        return (embedding_array / norm).tolist()

    def _embed_texts(
        self,
        texts: List[str],
        task_type: Optional[str] = None,
        max_retries: int = 5
    ) -> List[List[float]]:
        """
        Generate embeddings for texts using Gemini API with retry logic.

        Args:
            texts: List of text strings to embed
            task_type: Task type for optimization (RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY)
            max_retries: Maximum number of retry attempts for rate limits (default: 5)

        Returns:
            List of embedding vectors (normalized)

        Raises:
            Exception: If all retries exhausted or non-rate-limit error
        """
        import time

        # Use provided task type or default
        if task_type is None:
            task_type = self.embedding_task_type

        last_error = None

        for attempt in range(max_retries):
            try:
                # Lazily create genai client — key may arrive after service init
                if self.genai_client is None:
                    api_key = os.getenv("GEMINI_API_KEY")
                    if not api_key:
                        raise ValueError("GEMINI_API_KEY not found in environment variables")
                    self.genai_client = genai.Client(api_key=api_key)

                # Generate embeddings using Gemini API
                contents = [texts] if isinstance(texts, str) else texts
                result = self.genai_client.models.embed_content(
                    model=f"models/{self.embedding_model_name}",
                    contents=contents,
                    config=genai_types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=self.embedding_dimensions,
                    ),
                )

                # Extract embedding vectors from response objects
                embeddings = [e.values for e in result.embeddings]

                # Normalize embeddings (required for dimensions < 3,072)
                normalized = [self._normalize_embedding(emb) for emb in embeddings]

                if self.debug:
                    logger.debug(f"Generated {len(normalized)} embeddings ({self.embedding_dimensions}-dim)")

                return normalized

            except Exception as e:
                last_error = e
                error_str = str(e)

                # Check if it's a rate limit error (429)
                is_rate_limit = "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower()

                if is_rate_limit and attempt < max_retries - 1:
                    # Exponential backoff: 2s, 4s, 8s, 16s, 32s (max 62s total)
                    wait_time = min(2 ** (attempt + 1), 60)
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    # Non-rate-limit error or retries exhausted
                    if is_rate_limit:
                        logger.error(
                            f"Rate limit persists after {max_retries} retries. "
                            f"Consider waiting or enabling background indexing."
                        )
                    else:
                        logger.error(f"Failed to generate embeddings: {e}")
                    raise

        # Should never reach here, but just in case
        raise last_error if last_error else Exception("Embedding generation failed")

    def _compute_hash(self, content: str) -> str:
        """Compute MD5 hash of content for change detection."""
        return hashlib.md5(content.encode()).hexdigest()

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata to ensure ChromaDB compatibility.

        ChromaDB only accepts str, int, float, bool, or None values.
        Lists and other types need to be converted.
        """
        sanitized = {}
        for key, value in metadata.items():
            if value is None:
                # ChromaDB does not accept None — skip the key entirely
                continue
            elif isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                sanitized[key] = ", ".join(str(v) for v in value)
            else:
                sanitized[key] = str(value)
        return sanitized

    async def index_ground_truth_chunk(
        self,
        chunk_id: str,
        text: str,
        metadata: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """
        Index a single ground truth chunk.

        Args:
            chunk_id: Unique identifier for the chunk
            text: Chunk text content
            metadata: Metadata dict with year_start, year_end, source_file, etc.
            db: Database session for tracking

        Returns:
            True if indexed successfully
        """
        try:
            # Generate embedding
            embedding = self._embed_texts([text])[0]

            # Sanitize metadata for ChromaDB
            sanitized_metadata = self._sanitize_metadata(metadata)

            # Add to ChromaDB
            self.collections["ground_truth"].add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[sanitized_metadata]
            )

            if self.debug:
                logger.debug(f"Indexed ground truth chunk: {chunk_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to index ground truth chunk {chunk_id}: {e}")
            return False

    async def index_report_section(
        self,
        generation_id: str,
        timeline_id: str,
        section_name: str,
        section_content: str,
        metadata: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """
        Index a single report section.

        Args:
            generation_id: UUID of the generation
            timeline_id: UUID of the timeline
            section_name: Name of the section (e.g., 'political_landscape')
            section_content: Section text content
            metadata: Additional metadata
            db: Database session

        Returns:
            True if indexed successfully
        """
        try:
            chunk_id = f"gen_{generation_id}_{section_name}"

            # Generate embedding
            embedding = self._embed_texts([section_content])[0]

            # Prepare metadata
            full_metadata = {
                "chunk_id": chunk_id,
                "timeline_id": timeline_id,
                "generation_id": generation_id,
                "section_name": section_name,
                **metadata
            }

            # Sanitize metadata for ChromaDB
            sanitized_metadata = self._sanitize_metadata(full_metadata)

            # Add to ChromaDB
            self.collections["reports"].add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[section_content],
                metadatas=[sanitized_metadata]
            )

            if self.debug:
                logger.debug(
                    f"Indexed report section: {chunk_id}\n"
                    f"  Metadata: {sanitized_metadata}"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to index report section {section_name}: {e}")
            return False

    async def retrieve_relevant_ground_truth(
        self,
        deviation_description: str,
        scenario_type: str,
        year_start: int,
        year_end: int,
        custom_queries: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        debug: bool = False
    ) -> Tuple[str, Optional[Dict]]:
        """
        Retrieve relevant ground truth chunks using multi-query strategy.

        Args:
            deviation_description: Description of the historical deviation
            scenario_type: Type of scenario (local_deviation, global_deviation, etc.)
            year_start: Start year for filtering
            year_end: End year for filtering
            custom_queries: Optional list of custom queries to use instead of auto-generated ones
            top_k: Number of chunks to retrieve (default: from config)
            debug: Return debug information

        Returns:
            Tuple of (formatted_context, debug_info)
        """
        top_k = top_k or self.ground_truth_top_k
        debug = debug or self.debug

        # Use custom queries if provided, otherwise generate default queries
        if custom_queries:
            queries = custom_queries
            if debug:
                logger.info(f"[RAG DEBUG] Using {len(queries)} custom queries for ground truth retrieval")
        else:
            # Generate multiple queries for better coverage
            queries = self._generate_multi_queries(
                deviation_description,
                scenario_type,
                year_start,
                year_end
            )

        if debug:
            logger.info(f"[RAG DEBUG] Generated {len(queries)} queries for ground truth retrieval:")
            for i, query in enumerate(queries, 1):
                logger.info(f"  Query {i}: {query}")

        # Generate query embeddings using RETRIEVAL_QUERY task type
        query_embeddings = self._embed_texts(queries, task_type=self.embedding_query_task_type)

        # Retrieve with each query
        all_results = []
        query_debug_info = []

        for i, (query, query_embedding) in enumerate(zip(queries, query_embeddings)):
            try:
                results = self.collections["ground_truth"].query(
                    query_embeddings=[query_embedding],
                    n_results=5,
                    where={
                        "$and": [
                            {"year_start": {"$lte": year_end}},
                            {"year_end": {"$gte": year_start}}
                        ]
                    },
                    include=["documents", "metadatas", "distances"]
                )

                if results["documents"] and results["documents"][0]:
                    for doc, metadata, distance in zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0]
                    ):
                        all_results.append({
                            "text": doc,
                            "metadata": metadata,
                            "distance": distance,
                            "similarity": 1 - distance
                        })

                    if debug:
                        avg_distance = sum(results["distances"][0]) / len(results["distances"][0])
                        query_debug_info.append({
                            "query_index": i,
                            "query_text": query,
                            "results_count": len(results["documents"][0]),
                            "avg_distance": round(avg_distance, 3)
                        })

            except Exception as e:
                logger.error(f"Query {i} failed: {e}")
                continue

        # Deduplicate by chunk_id
        unique_chunks = {}
        for result in all_results:
            chunk_id = result["metadata"].get("chunk_id", str(uuid4()))
            if chunk_id not in unique_chunks or result["similarity"] > unique_chunks[chunk_id]["similarity"]:
                unique_chunks[chunk_id] = result

        # Sort by similarity and take top_k
        ranked_chunks = sorted(
            unique_chunks.values(),
            key=lambda x: x["similarity"],
            reverse=True
        )[:top_k]

        # Format context
        context = self._format_ground_truth_context(ranked_chunks)

        # Debug info
        debug_info = None
        if debug:
            debug_info = {
                "total_queries": len(queries),
                "total_candidates": len(all_results),
                "unique_chunks": len(unique_chunks),
                "final_chunks": len(ranked_chunks),
                "total_tokens": sum(len(c["text"].split()) for c in ranked_chunks) * 1.3,
                "query_details": query_debug_info,
                "top_chunks": [
                    {
                        "chunk_id": c["metadata"].get("chunk_id", "unknown"),
                        "similarity": round(c["similarity"], 3),
                        "years": f"{c['metadata'].get('year_start', '?')}-{c['metadata'].get('year_end', '?')}",
                        "source": c["metadata"].get("source_file", "N/A"),
                        "preview": c["text"][:150] + "..."
                    }
                    for c in ranked_chunks[:5]
                ]
            }
            # Log detailed retrieval info at INFO level when debug mode is enabled
            logger.info(
                f"[RAG DEBUG] Ground truth retrieval complete:\n"
                f"  Total queries: {debug_info['total_queries']}\n"
                f"  Candidates found: {debug_info['total_candidates']}\n"
                f"  After deduplication: {debug_info['unique_chunks']}\n"
                f"  Final chunks: {debug_info['final_chunks']}\n"
                f"  Estimated tokens: ~{debug_info['total_tokens']:.0f}"
            )

            # Log top matching chunks
            logger.info("[RAG DEBUG] Top matching chunks:")
            for i, chunk in enumerate(debug_info['top_chunks'], 1):
                logger.info(
                    f"  {i}. Similarity: {chunk['similarity']:.3f} | "
                    f"Years: {chunk['years']} | "
                    f"Source: {chunk['source']}"
                )
                logger.info(f"     Preview: {chunk['preview']}")

        return context, debug_info

    async def retrieve_previous_generation_context(
        self,
        timeline_id: str,
        current_year_start: int,
        deviation_description: str,
        scenario_type: str,
        top_k: Optional[int] = None,
        debug: Optional[bool] = None
    ) -> Tuple[str, Optional[Dict]]:
        """
        Retrieve relevant chunks from previous generations in this timeline.

        This is used for timeline extensions to get context from what happened
        in the alternate timeline so far.

        Args:
            timeline_id: The timeline UUID
            current_year_start: Start year of the extension period
            deviation_description: Original deviation description
            scenario_type: Type of scenario
            top_k: Number of top chunks to return (default: 8)
            debug: Enable debug logging

        Returns:
            Tuple of (formatted_context, debug_info)
        """
        top_k = top_k or 8  # Fewer chunks than ground truth (previous gen is more focused)
        debug = debug or self.debug

        # Generate extension-specific queries
        key_terms = self._extract_key_terms(deviation_description)

        queries = [
            # Query 1: Consequences and developments
            f"Consequences and developments from: {deviation_description}",

            # Query 2: Key changes in alternate timeline
            f"Political, economic, social changes in alternate timeline {scenario_type}",

            # Query 3: Narrative continuity
            f"Key figures, conflicts, events leading up to {current_year_start}",

            # Query 4: Long-term implications
            f"Long-term implications and systemic changes from {key_terms}"
        ]

        if debug:
            logger.info(
                f"[RAG DEBUG] Generated {len(queries)} queries for previous generation retrieval:\n"
                f"  Timeline: {timeline_id}\n"
                f"  Extension starts at year: {current_year_start}"
            )
            for i, query in enumerate(queries, 1):
                logger.info(f"  Query {i}: {query}")

        # Generate query embeddings
        query_embeddings = self._embed_texts(queries, task_type=self.embedding_query_task_type)

        # Retrieve from both reports and narratives collections
        all_results = []
        collection_stats = {"reports": 0, "narratives": 0}

        for collection_key in ["reports", "narratives"]:
            if collection_key not in self.collections:
                continue

            collection = self.collections[collection_key]

            for i, (query, query_embedding) in enumerate(zip(queries, query_embeddings)):
                try:
                    query_filter = {
                        "$and": [
                            {"timeline_id": timeline_id},
                            {"year_end": {"$lte": current_year_start}}
                        ]
                    }

                    if debug:
                        logger.info(
                            f"[RAG DEBUG] Querying {collection_key} collection:\n"
                            f"  Filter: timeline_id={timeline_id}, year_end <= {current_year_start}"
                        )

                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=2,  # 2 results per query per collection
                        where=query_filter,
                        include=["documents", "metadatas", "distances"]
                    )

                    if results["documents"] and results["documents"][0]:
                        collection_stats[collection_key] += len(results["documents"][0])
                        for doc, metadata, distance in zip(
                            results["documents"][0],
                            results["metadatas"][0],
                            results["distances"][0]
                        ):
                            all_results.append({
                                "text": doc,
                                "metadata": metadata,
                                "distance": distance,
                                "similarity": 1 - distance,
                                "collection": collection_key
                            })

                except Exception as e:
                    logger.error(f"Query {i} failed on {collection_key} collection: {e}")
                    continue

        # Deduplicate by chunk_id
        unique_chunks = {}
        for result in all_results:
            chunk_id = result["metadata"].get("chunk_id", str(uuid4()))
            if chunk_id not in unique_chunks or result["similarity"] > unique_chunks[chunk_id]["similarity"]:
                unique_chunks[chunk_id] = result

        # Sort by similarity and take top_k
        ranked_chunks = sorted(
            unique_chunks.values(),
            key=lambda x: x["similarity"],
            reverse=True
        )[:top_k]

        # Format context with clear labeling
        context = self._format_previous_generation_context(ranked_chunks, timeline_id)

        # Debug info
        debug_info = None
        if debug:
            debug_info = {
                "total_queries": len(queries),
                "total_candidates": len(all_results),
                "collection_stats": collection_stats,
                "unique_chunks": len(unique_chunks),
                "final_chunks": len(ranked_chunks),
                "total_tokens": sum(len(c["text"].split()) for c in ranked_chunks) * 1.3,
                "top_chunks": [
                    {
                        "chunk_id": c["metadata"].get("chunk_id", "unknown"),
                        "similarity": round(c["similarity"], 3),
                        "collection": c.get("collection", "unknown"),
                        "generation_id": c["metadata"].get("generation_id", "N/A"),
                        "years": f"{c['metadata'].get('year_start', '?')}-{c['metadata'].get('year_end', '?')}",
                        "preview": c["text"][:150] + "..."
                    }
                    for c in ranked_chunks[:5]
                ]
            }

            # Log detailed retrieval info
            logger.info(
                f"[RAG DEBUG] Previous generation retrieval complete:\n"
                f"  Total queries: {debug_info['total_queries']}\n"
                f"  Candidates found: {debug_info['total_candidates']}\n"
                f"  - From reports: {collection_stats['reports']}\n"
                f"  - From narratives: {collection_stats['narratives']}\n"
                f"  After deduplication: {debug_info['unique_chunks']}\n"
                f"  Final chunks: {debug_info['final_chunks']}\n"
                f"  Estimated tokens: ~{debug_info['total_tokens']:.0f}"
            )

            # Log top matching chunks
            logger.info("[RAG DEBUG] Top matching chunks from previous generations:")
            for i, chunk in enumerate(debug_info['top_chunks'], 1):
                logger.info(
                    f"  {i}. Similarity: {chunk['similarity']:.3f} | "
                    f"Collection: {chunk['collection']} | "
                    f"Years: {chunk['years']}"
                )
                logger.info(f"     Preview: {chunk['preview']}")

        return context, debug_info

    def _format_previous_generation_context(
        self,
        ranked_chunks: List[Dict],
        timeline_id: str
    ) -> str:
        """
        Format previous generation chunks with clear labeling.

        Args:
            ranked_chunks: Sorted list of chunk results
            timeline_id: Timeline UUID for attribution

        Returns:
            Formatted context string
        """
        if not ranked_chunks:
            return ""

        context_parts = [
            "# Context from Previous Generations in This Timeline",
            "",
            f"Timeline ID: {timeline_id}",
            f"Retrieved {len(ranked_chunks)} relevant passages from previous simulation periods:",
            ""
        ]

        for i, chunk in enumerate(ranked_chunks, 1):
            metadata = chunk["metadata"]
            year_range = f"{metadata.get('year_start', '?')}-{metadata.get('year_end', '?')}"
            generation_id = metadata.get('generation_id', 'unknown')
            content_type = chunk.get('collection', 'unknown')

            context_parts.append(f"## Passage {i} ({year_range}) - {content_type.title()}")
            context_parts.append(f"Generation: {generation_id}")
            context_parts.append(f"Relevance: {chunk['similarity']:.2%}")
            context_parts.append("")
            context_parts.append(chunk["text"])
            context_parts.append("")
            context_parts.append("---")
            context_parts.append("")

        return "\n".join(context_parts)

    def _generate_multi_queries(
        self,
        deviation_description: str,
        scenario_type: str,
        year_start: int,
        year_end: int
    ) -> List[str]:
        """
        Generate multiple query perspectives for comprehensive retrieval.

        Args:
            deviation_description: The historical deviation
            scenario_type: Type of scenario
            year_start: Start year
            year_end: End year

        Returns:
            List of query strings
        """
        # Extract key terms for focused queries
        key_terms = self._extract_key_terms(deviation_description)

        # queries = [
        #     # Query 1: Direct deviation focus
        #     deviation_description,

        #     # Query 2: Temporal + thematic context
        #     f"Major events {year_start}-{year_end}: political, economic, social, technological changes",

        #     # Query 3: Consequences and implications focus
        #     f"What were the consequences and historical significance of events related to {key_terms} during {year_start}-{year_end}",

        #     # Query 4: Key entities and time period
        #     f"{key_terms} historical context {year_start}-{year_end}"
        # ]

        queries = [
            # 1. THE DICTIONARY CHECK (Fixes Terminology Drift)
            f"Definitions and specific terminology regarding {key_terms} mechanisms and phenomena",

            # 2. THE HUMAN ELEMENT (Fixes Fictional Characters)
            f"Psychological impact of {key_terms} on specific historical figures, leadership, and decision-makers {year_start}-{year_end}",

            # 3. THE SYSTEMIC CRASH (Fixes Kinetic Causality)
            f"Systemic failures in economics, infrastructure, and ideology caused by {key_terms} {year_start}-{year_end}",

            # 4. THE CULTURAL TEXTURE (Fixes Historical Depth)
            f"Cultural shifts, religious movements, and intellectual reactions to {key_terms} {year_start}-{year_end}",

            # 5. THE SPECIFIC INTERSECTION (The Anchor)
            f"How {key_terms} altered specific real-world historical events and timelines between {year_start}-{year_end}"
]

        return queries

    def _extract_key_terms(self, text: str) -> str:
        """
        Extract key terms from deviation description.

        Simple keyword extraction (can be enhanced with NLP later).
        """
        # Remove common words and extract important terms
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "was", "are", "were", "been", "be"
        }

        words = text.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        return " ".join(keywords[:10])  # Top 10 keywords

    def _format_ground_truth_context(self, chunks: List[Dict]) -> str:
        """
        Format retrieved ground truth chunks for prompt injection.

        Args:
            chunks: List of chunk dictionaries with text and metadata

        Returns:
            Formatted context string
        """
        if not chunks:
            return ""

        context_parts = ["[GROUND TRUTH HISTORICAL CONTEXT]", ""]
        context_parts.append(
            "The following snippets represent what happened in REAL history. "
            "Use this ONLY for context on what typically happens in this era. "
            "Do NOT treat these as facts for your simulation unless they logically survive the deviation."
        )

        for chunk in chunks:
            source = chunk["metadata"].get("source_file", "Unknown")
            years = f"{chunk['metadata'].get('year_start', '?')}-{chunk['metadata'].get('year_end', '?')}"
            context_parts.append(f"\n[Source: Real History | {source} | Years: {years}]")
            context_parts.append(chunk["text"])
            context_parts.append("-" * 80)

        return "\n".join(context_parts)

    async def get_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get vector store statistics.

        Args:
            db: Database session

        Returns:
            Statistics dictionary
        """
        if not self.enabled:
            return {"enabled": False, "message": "Vector store is disabled"}

        try:
            stats = {
                "enabled": True,
                "embedding_model": self.embedding_model_name,
                "collections": {}
            }

            for key, collection in self.collections.items():
                stats["collections"][key] = {
                    "name": self.collection_names[key],
                    "count": collection.count()
                }

            # Get index tracking stats
            result = await db.execute(
                select(VectorStoreIndexDB.content_type, VectorStoreIndexDB.id)
            )
            index_records = result.all()

            stats["index_records"] = {
                "total": len(index_records),
                "by_type": {}
            }

            for content_type in ["ground_truth", "report", "narrative"]:
                count = sum(1 for r in index_records if r[0] == content_type)
                stats["index_records"]["by_type"][content_type] = count

            return stats

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"enabled": True, "error": str(e)}

    async def delete_timeline_vectors(
        self,
        timeline_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Delete all vector chunks for a timeline and its generations.

        Args:
            timeline_id: Timeline UUID
            db: Database session

        Returns:
            Deletion statistics
        """
        if not self.enabled:
            return {"deleted": 0, "message": "Vector store is disabled"}

        try:
            deleted_count = 0

            # Delete from both reports and narratives collections
            for collection_key in ["reports", "narratives"]:
                if collection_key not in self.collections:
                    continue

                collection = self.collections[collection_key]

                # Get all chunks with this timeline_id
                results = collection.get(
                    where={"timeline_id": timeline_id},
                    include=["metadatas"]
                )

                if results and results["ids"]:
                    chunk_ids = results["ids"]
                    collection.delete(ids=chunk_ids)
                    deleted_count += len(chunk_ids)
                    logger.info(f"Deleted {len(chunk_ids)} vector chunks from {collection_key} for timeline {timeline_id}")

            # Delete index records
            await db.execute(
                delete(VectorStoreIndexDB).where(
                    VectorStoreIndexDB.timeline_id == timeline_id
                )
            )
            await db.flush()

            return {
                "deleted": deleted_count,
                "timeline_id": timeline_id
            }

        except Exception as e:
            logger.error(f"Failed to delete timeline vectors: {e}")
            return {"deleted": 0, "error": str(e)}

    async def delete_generation_vectors(
        self,
        generation_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Delete vector chunks for a specific generation.

        Args:
            generation_id: Generation UUID
            db: Database session

        Returns:
            Deletion statistics
        """
        if not self.enabled:
            return {"deleted": 0, "message": "Vector store is disabled"}

        try:
            deleted_count = 0

            # Delete from both reports and narratives collections
            for collection_key in ["reports", "narratives"]:
                if collection_key not in self.collections:
                    continue

                collection = self.collections[collection_key]

                # Get all chunks with this generation_id
                results = collection.get(
                    where={"generation_id": generation_id},
                    include=["metadatas"]
                )

                if results and results["ids"]:
                    chunk_ids = results["ids"]
                    collection.delete(ids=chunk_ids)
                    deleted_count += len(chunk_ids)
                    logger.info(f"Deleted {len(chunk_ids)} vector chunks from {collection_key} for generation {generation_id}")

            # Delete index records
            await db.execute(
                delete(VectorStoreIndexDB).where(
                    VectorStoreIndexDB.content_id == generation_id
                )
            )
            await db.flush()

            return {
                "deleted": deleted_count,
                "generation_id": generation_id
            }

        except Exception as e:
            logger.error(f"Failed to delete generation vectors: {e}")
            return {"deleted": 0, "error": str(e)}


    def _chunk_markdown(
        self,
        markdown_content: str,
        source_file: str,
        year_start: int,
        year_end: int,
        chunk_size: int = 800
    ) -> List[Dict[str, Any]]:
        """
        Split markdown content into semantic chunks by H2 sections.

        Args:
            markdown_content: Full markdown content
            source_file: Source filename
            year_start: Start year from filename
            year_end: End year from filename
            chunk_size: Target tokens per chunk (approximate)

        Returns:
            List of chunk dictionaries with text and metadata
        """
        import re

        chunks = []

        # Extract H1 title for context
        h1_match = re.search(r'^# (.+)$', markdown_content, re.MULTILINE)
        title_context = h1_match.group(1) if h1_match else f"Historical Period {year_start}-{year_end}"

        # Split by H2 sections
        sections = re.split(r'\n## ', markdown_content)

        for idx, section in enumerate(sections):
            if not section.strip():
                continue

            # Skip the title section (before first H2)
            if idx == 0 and section.startswith("#"):
                continue

            # Add H2 marker back if not first section
            if idx > 0 and not section.startswith("##"):
                section = "## " + section

            # Extract section heading
            section_match = re.match(r'##\s+(.+?)(\n|$)', section)
            section_heading = section_match.group(1) if section_match else "Section"

            # Create chunk with context
            chunk_text = f"[Period: {year_start}-{year_end}] {title_context}\n\n{section.strip()}"

            # Approximate token count (words * 1.3)
            approx_tokens = len(chunk_text.split()) * 1.3

            # If section is too large, split by H3 subsections
            if approx_tokens > chunk_size * 1.5:
                subsections = re.split(r'\n### ', section)
                for sub_idx, subsection in enumerate(subsections):
                    if not subsection.strip():
                        continue

                    if sub_idx > 0:
                        subsection = "### " + subsection

                    sub_chunk_text = f"[Period: {year_start}-{year_end}] {title_context}\n\n## {section_heading}\n\n{subsection.strip()}"

                    chunks.append({
                        "text": sub_chunk_text,
                        "metadata": {
                            "chunk_id": f"gt_{source_file}_{idx}_{sub_idx}",
                            "source_file": source_file,
                            "year_start": year_start,
                            "year_end": year_end,
                            "section_heading": f"{section_heading} > Subsection {sub_idx}",
                            "chunk_type": "ground_truth"
                        }
                    })
            else:
                # Keep section as single chunk
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "chunk_id": f"gt_{source_file}_{idx}",
                        "source_file": source_file,
                        "year_start": year_start,
                        "year_end": year_end,
                        "section_heading": section_heading,
                        "chunk_type": "ground_truth"
                    }
                })

        if self.debug:
            logger.debug(f"Chunked {source_file} into {len(chunks)} chunks")

        return chunks

    async def index_ground_truth_reports(
        self,
        ground_truth_dir: str,
        db: AsyncSession,
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """
        Index all ground truth markdown files from directory.

        Args:
            ground_truth_dir: Path to ground truth directory
            db: Database session
            force_reindex: If True, re-index even if already indexed

        Returns:
            Dictionary with indexing stats
        """
        import re
        from pathlib import Path

        if not self.enabled:
            return {"error": "Vector store is disabled"}

        logger.info(f"Starting ground truth indexing from {ground_truth_dir}")

        stats = {
            "files_processed": 0,
            "files_skipped": 0,
            "chunks_indexed": 0,
            "errors": []
        }

        ground_truth_path = Path(ground_truth_dir)
        if not ground_truth_path.exists():
            return {"error": f"Directory not found: {ground_truth_dir}"}

        # Get all markdown files
        md_files = sorted(ground_truth_path.glob("*.md"))

        for md_file in md_files:
            try:
                # Extract year range from filename (e.g., "1900-1910.md")
                filename = md_file.stem
                year_match = re.match(r'(\d{4})-(\d{4})', filename)

                if not year_match:
                    logger.warning(f"Skipping {md_file.name}: filename doesn't match YYYY-YYYY pattern")
                    stats["files_skipped"] += 1
                    continue

                year_start = int(year_match.group(1))
                year_end = int(year_match.group(2))

                # Read and chunk the file first (needed for partial index detection)
                content = md_file.read_text(encoding="utf-8")
                current_hash = self._compute_hash(content)

                chunks = self._chunk_markdown(
                    content,
                    filename,
                    year_start,
                    year_end,
                    self.chunk_size
                )

                if not chunks:
                    logger.warning(f"No chunks extracted from {filename}")
                    stats["files_skipped"] += 1
                    continue

                # Check if already indexed (unless force_reindex)
                should_reindex = force_reindex
                existing_index = None

                if not force_reindex:
                    result = await db.execute(
                        select(VectorStoreIndexDB).where(
                            VectorStoreIndexDB.content_type == "ground_truth",
                            VectorStoreIndexDB.content_id == filename
                        )
                    )
                    existing_index = result.scalar_one_or_none()

                    if existing_index:
                        # Check if content changed via hash
                        if current_hash != existing_index.source_hash:
                            logger.info(f"Re-indexing {filename}: content changed (hash mismatch)")
                            should_reindex = True
                        # Check for partial indexing (rate limit mid-process)
                        elif existing_index.chunk_count < len(chunks):
                            logger.warning(
                                f"Re-indexing {filename}: partial index detected "
                                f"({existing_index.chunk_count}/{len(chunks)} chunks)"
                            )
                            should_reindex = True
                        else:
                            # Fully indexed, skip
                            logger.info(f"Skipping {filename}: already indexed ({existing_index.chunk_count} chunks)")
                            stats["files_skipped"] += 1
                            continue

                # Delete old chunks if re-indexing
                if should_reindex and existing_index:
                    # Try to delete all possible chunk IDs (including sub-chunks)
                    chunk_ids_to_delete = []
                    for i in range(existing_index.chunk_count + 10):  # Extra buffer for sub-chunks
                        chunk_ids_to_delete.append(f"gt_{filename}_{i}")
                        for sub_i in range(10):  # Sub-chunks
                            chunk_ids_to_delete.append(f"gt_{filename}_{i}_{sub_i}")

                    try:
                        self.collections["ground_truth"].delete(ids=chunk_ids_to_delete)
                        logger.debug(f"Deleted old chunks for {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old chunks: {e}")

                # Index each chunk
                indexed_count = 0
                for chunk in chunks:
                    success = await self.index_ground_truth_chunk(
                        chunk_id=chunk["metadata"]["chunk_id"],
                        text=chunk["text"],
                        metadata=chunk["metadata"],
                        db=db
                    )
                    if success:
                        indexed_count += 1

                # Update index tracking in database
                result = await db.execute(
                    select(VectorStoreIndexDB).where(
                        VectorStoreIndexDB.content_type == "ground_truth",
                        VectorStoreIndexDB.content_id == filename
                    )
                )
                existing_index = result.scalar_one_or_none()

                if existing_index:
                    existing_index.chunk_count = indexed_count
                    existing_index.source_hash = current_hash
                    existing_index.indexed_at = datetime.now(timezone.utc)
                else:
                    new_index = VectorStoreIndexDB(
                        content_type="ground_truth",
                        content_id=filename,
                        timeline_id=None,
                        chunk_count=indexed_count,
                        embedding_model=self.embedding_model_name,
                        source_hash=current_hash
                    )
                    db.add(new_index)

                await db.commit()

                logger.info(f"Indexed {filename}: {indexed_count}/{len(chunks)} chunks")
                stats["files_processed"] += 1
                stats["chunks_indexed"] += indexed_count

            except Exception as e:
                error_msg = f"Error processing {md_file.name}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
                continue

        logger.info(
            f"Ground truth indexing complete: "
            f"{stats['files_processed']} files, "
            f"{stats['chunks_indexed']} chunks, "
            f"{stats['files_skipped']} skipped, "
            f"{len(stats['errors'])} errors"
        )

        return stats

    async def is_generation_indexed(
        self,
        generation_id: str,
        db: AsyncSession
    ) -> bool:
        """
        Check if a generation has been indexed in the vector store.

        Args:
            generation_id: UUID of the generation
            db: Database session

        Returns:
            True if generation is fully indexed, False otherwise
        """
        try:
            result = await db.execute(
                select(VectorStoreIndexDB).where(
                    VectorStoreIndexDB.content_type == "report",
                    VectorStoreIndexDB.content_id == generation_id
                )
            )
            index_record = result.scalar_one_or_none()
            return index_record is not None and index_record.chunk_count > 0
        except Exception as e:
            logger.error(f"Error checking if generation indexed: {e}")
            return False

    async def index_generation_background(
        self,
        generation_id: str,
        timeline_id: str,
        report_sections: Dict[str, str],
        narrative: Optional[str],
        year_start: int,
        year_end: int,
        db: AsyncSession
    ):
        """
        Index a generation in the background (non-blocking).

        This method indexes both report sections and narrative without blocking
        the main timeline generation flow. Uses generous retry logic to handle
        rate limits gracefully.

        Args:
            generation_id: UUID of the generation
            timeline_id: UUID of the timeline
            report_sections: Dictionary of section_name -> section_content
            narrative: Optional narrative text
            year_start: Start year of this generation
            year_end: End year of this generation
            db: Database session
        """
        import asyncio

        logger.info(
            f"Starting background indexing for generation {generation_id}\n"
            f"  Timeline: {timeline_id}\n"
            f"  Years: {year_start}-{year_end}"
        )

        indexed_sections = 0
        failed_sections = []

        # Index report sections
        for section_name, section_content in report_sections.items():
            try:
                success = await self.index_report_section(
                    generation_id=generation_id,
                    timeline_id=timeline_id,
                    section_name=section_name,
                    section_content=section_content,
                    metadata={
                        "year_start": year_start,
                        "year_end": year_end
                    },
                    db=db
                )
                if success:
                    indexed_sections += 1
                else:
                    failed_sections.append(section_name)
            except Exception as e:
                logger.error(f"Failed to index section {section_name}: {e}")
                failed_sections.append(section_name)
                continue

        # Index narrative if present
        if narrative:
            try:
                chunk_id = f"gen_{generation_id}_narrative"
                embedding = self._embed_texts([narrative])[0]

                self.collections["narratives"].add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[narrative],
                    metadatas=[{
                        "chunk_id": chunk_id,
                        "timeline_id": timeline_id,
                        "generation_id": generation_id,
                        "year_start": year_start,
                        "year_end": year_end
                    }]
                )
                indexed_sections += 1
                logger.debug(f"Indexed narrative for generation {generation_id}")
            except Exception as e:
                logger.error(f"Failed to index narrative: {e}")
                failed_sections.append("narrative")

        # Log results
        if failed_sections:
            logger.warning(
                f"Generation {generation_id}: Indexed {indexed_sections} sections, "
                f"failed: {', '.join(failed_sections)}"
            )
        else:
            logger.info(
                f"Generation {generation_id}: Successfully indexed all {indexed_sections} sections"
            )

    async def retrieve_relevant_ground_truth_safe(
        self,
        deviation_description: str,
        scenario_type: str,
        year_start: int,
        year_end: int,
        fallback_loader: Optional[callable] = None,
        custom_queries: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        debug: bool = False
    ) -> Tuple[str, Optional[Dict]]:
        """
        Retrieve relevant ground truth with graceful fallback to legacy mode.

        If RAG fails (rate limits, vector store unavailable, etc.), automatically
        falls back to provided fallback_loader function.

        Args:
            deviation_description: Description of the historical deviation
            scenario_type: Type of scenario
            year_start: Start year for filtering
            year_end: End year for filtering
            fallback_loader: Optional function to call if RAG fails (legacy loader)
            custom_queries: Optional list of custom queries to use instead of auto-generated ones
            top_k: Number of chunks to retrieve
            debug: Return debug information

        Returns:
            Tuple of (formatted_context, debug_info)
        """
        try:
            # Try RAG retrieval
            return await self.retrieve_relevant_ground_truth(
                deviation_description=deviation_description,
                scenario_type=scenario_type,
                year_start=year_start,
                year_end=year_end,
                custom_queries=custom_queries,
                top_k=top_k,
                debug=debug
            )
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

            # Fall back to legacy mode if provided
            if fallback_loader:
                logger.info("Falling back to legacy full-text loading")
                try:
                    legacy_context = fallback_loader(year_start, year_end)
                    debug_info = {
                        "mode": "legacy_fallback",
                        "reason": str(e),
                        "estimated_tokens": len(legacy_context.split()) * 1.3
                    } if debug else None
                    return legacy_context, debug_info
                except Exception as fallback_error:
                    logger.error(f"Legacy fallback also failed: {fallback_error}")
                    raise

            # No fallback provided, re-raise
            raise


def get_vector_store_service() -> VectorStoreService:
    """
    Get or create singleton vector store service instance.

    Returns:
        VectorStoreService instance
    """
    global _vector_store_service

    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()

    return _vector_store_service
