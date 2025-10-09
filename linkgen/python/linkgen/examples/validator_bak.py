"""Law title validation module.

This module provides comprehensive law title validation functionality that:
- Extracts core terms, prefixes, and suffixes from law titles
- Queries DynamoDB for matching documents
- Creates multi-dimensional inverted indexes for efficient searching
- Performs intersection-based matching with ranking

The validator uses a sophisticated matching algorithm that considers:
- Core term matching
- Prefix and suffix matching
- Date-based filtering
- Promulgator matching
- Issue number matching
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from linkgen.models import DocMeta, Entity, TokenSpan

from linkgen.tokenizer import LawTitleTokenizer

logger = logging.getLogger(__name__)


class DynamoDBClient(Protocol):
    """Protocol for DynamoDB client interface."""

    def query(
        self,
        table_name: str,
        index: str,
        pk: str
    ) -> list[DocMeta]:
        """Query DynamoDB table using the specified index and partition key."""
        ...


@dataclass
class ValidationResult:
    """Result of law title validation."""

    doc_meta: DocMeta | None
    confidence_score: float
    matched_attributes: dict[str, Any]
    search_metadata: dict[str, Any]


class MultiDimensionalIndex:
    """Multi-dimensional inverted index for efficient document searching."""

    def __init__(self) -> None:
        """Initialize the multi-dimensional index."""
        self._prefixes_index: dict[str, set[str]] = defaultdict(set)
        self._suffixes_index: dict[str, set[str]] = defaultdict(set)
        self._release_date_index: dict[str, set[str]] = defaultdict(set)
        self._effective_date_index: dict[str, set[str]] = defaultdict(set)
        self._issue_no_index: dict[str, set[str]] = defaultdict(set)
        self._promulgators_index: dict[str, set[str]] = defaultdict(set)
        self._doc_meta_map: dict[str, DocMeta] = {}

    def add_document(self, doc_meta: DocMeta) -> None:
        """Add a document to the index.

        Args:
            doc_meta: Document metadata to index.
        """
        doc_id = doc_meta.doc_id
        self._doc_meta_map[doc_id] = doc_meta

        # Index promulgators
        for promulgator in doc_meta.promulgators:
            self._promulgators_index[promulgator].add(doc_id)

        # Index dates
        self._release_date_index[doc_meta.release_date].add(doc_id)
        self._effective_date_index[doc_meta.effective_date].add(doc_id)

        # Index issue number
        self._issue_no_index[doc_meta.issue_no].add(doc_id)

    def add_tokenized_document(self, doc_meta: DocMeta, token_span: TokenSpan) -> None:
        """Add a tokenized document to the index.

        Args:
            doc_meta: Document metadata to index.
            token_span: Tokenized document title.
        """
        doc_id = doc_meta.doc_id
        self._doc_meta_map[doc_id] = doc_meta

        # Index prefixes
        for prefix in token_span.prefixes:
            self._prefixes_index[prefix.text].add(doc_id)

        # Index suffixes
        for suffix in token_span.suffixes:
            self._suffixes_index[suffix.text].add(doc_id)

        # Index other attributes
        self._release_date_index[doc_meta.release_date].add(doc_id)
        self._effective_date_index[doc_meta.effective_date].add(doc_id)
        self._issue_no_index[doc_meta.issue_no].add(doc_id)

        # Index promulgators
        for promulgator in doc_meta.promulgators:
            self._promulgators_index[promulgator].add(doc_id)

    def search_by_prefixes(self, prefixes: list[str]) -> set[str]:
        """Search for documents matching the given prefixes.

        Args:
            prefixes: List of prefix texts to search for.

        Returns:
            Set of document IDs matching the prefixes.
        """
        if not prefixes:
            return set()

        # Start with documents matching the first prefix
        result: set[str] = self._prefixes_index.get(prefixes[0], set()).copy()

        # Intersect with documents matching subsequent prefixes
        for prefix in prefixes[1:]:
            result &= self._prefixes_index.get(prefix, set())

        return result

    def search_by_suffixes(self, suffixes: list[str]) -> set[str]:
        """Search for documents matching the given suffixes.

        Args:
            suffixes: List of suffix texts to search for.

        Returns:
            Set of document IDs matching the suffixes.
        """
        if not suffixes:
            return set()

        # Start with documents matching the first suffix
        result: set[str] = self._suffixes_index.get(suffixes[0], set()).copy()

        # Intersect with documents matching subsequent suffixes
        for suffix in suffixes[1:]:
            result &= self._suffixes_index.get(suffix, set())

        return result

    def search_by_promulgators(self, promulgators: list[str]) -> set[str]:
        """Search for documents matching the given promulgators.

        Args:
            promulgators: List of promulgator names to search for.

        Returns:
            Set of document IDs matching the promulgators.
        """
        if not promulgators:
            return set()

        # Start with documents matching the first promulgator
        result: set[str] = self._promulgators_index.get(promulgators[0], set()).copy()

        # Intersect with documents matching subsequent promulgators
        for promulgator in promulgators[1:]:
            result &= self._promulgators_index.get(promulgator, set())

        return result

    def search_by_date_range(
        self,
        release_date_start: str | None = None,
        release_date_end: str | None = None,
        effective_date_start: str | None = None,
        effective_date_end: str | None = None
    ) -> set[str]:
        """Search for documents within the specified date ranges.

        Args:
            release_date_start: Start of release date range.
            release_date_end: End of release date range.
            effective_date_start: Start of effective date range.
            effective_date_end: End of effective date range.

        Returns:
            Set of document IDs within the date ranges.
        """
        result: set[str] = set()

        # Filter by release date range
        if release_date_start or release_date_end:
            release_docs: set[str] = set()
            for date, doc_ids in self._release_date_index.items():
                if release_date_start and date < release_date_start:
                    continue
                if release_date_end and date > release_date_end:
                    continue
                release_docs.update(doc_ids)
            result = release_docs if not result else result & release_docs

        # Filter by effective date range
        if effective_date_start or effective_date_end:
            effective_docs: set[str] = set()
            for date, doc_ids in self._effective_date_index.items():
                if effective_date_start and date < effective_date_start:
                    continue
                if effective_date_end and date > effective_date_end:
                    continue
                effective_docs.update(doc_ids)
            result = effective_docs if not result else result & effective_docs

        return result

    def get_document(self, doc_id: str) -> DocMeta | None:
        """Get document metadata by ID.

        Args:
            doc_id: Document ID to retrieve.

        Returns:
            Document metadata or None if not found.
        """
        return self._doc_meta_map.get(doc_id)

    def get_documents(self, doc_ids: set[str]) -> list[DocMeta]:
        """Get multiple documents by IDs.

        Args:
            doc_ids: Set of document IDs to retrieve.

        Returns:
            List of document metadata.
        """
        return [self._doc_meta_map[doc_id] for doc_id in doc_ids if doc_id in self._doc_meta_map]


class LawTitleValidator:
    """Law title validation engine."""

    def __init__(
        self,
        dynamo_client: DynamoDBClient,
        promulgators: list[str],
        table_name: str = "documents",
        index_name: str = "core_term-release_date_index"
    ) -> None:
        """Initialize the law title validator.

        Args:
            dynamo_client: DynamoDB client for querying documents.
            promulgators: List of promulgator keywords for tokenization.
            table_name: DynamoDB table name.
            index_name: DynamoDB index name for core term queries.
        """
        self._dynamo_client = dynamo_client
        self._tokenizer = LawTitleTokenizer(promulgators)
        self._table_name = table_name
        self._index_name = index_name
        self._index = MultiDimensionalIndex()

    def validate(self, law_title_entity: Entity) -> ValidationResult:
        """Validate a law title entity and return the best matching document.

        Args:
            law_title_entity: Law title entity to validate.

        Returns:
            Validation result containing the best match or None.
        """
        try:
            # Step 1: Extract core term, prefixes, suffixes from input
            input_token_span = self._extract_tokens_from_entity(law_title_entity)
            if not input_token_span:
                return ValidationResult(
                    doc_meta=None,
                    confidence_score=0.0,
                    matched_attributes={},
                    search_metadata={"error": "Failed to extract tokens from input"}
                )

            # Step 2: Query DynamoDB for documents with matching core term
            core_term = input_token_span.core.text
            doc_meta_list = self._query_documents_by_core_term(core_term)

            if not doc_meta_list:
                return ValidationResult(
                    doc_meta=None,
                    confidence_score=0.0,
                    matched_attributes={},
                    search_metadata={"core_term": core_term, "documents_found": 0}
                )

            # Step 3: Build multi-dimensional index for the retrieved documents
            self._build_index_for_documents(doc_meta_list)

            # Step 4: Perform multi-dimensional search
            search_results = self._perform_multi_dimensional_search(
                input_token_span,
                law_title_entity
            )

            # Step 5: Rank and select the best match
            return self._select_best_match(search_results, doc_meta_list)

        except Exception as e:
            logger.exception("Error during law title validation")
            return ValidationResult(
                doc_meta=None,
                confidence_score=0.0,
                matched_attributes={},
                search_metadata={"error": str(e)}
            )

    def _extract_tokens_from_entity(self, entity: Entity) -> TokenSpan | None:
        """Extract tokens from a law title entity.

        Args:
            entity: Law title entity to extract tokens from.

        Returns:
            Token span or None if extraction fails.
        """
        try:
            return self._tokenizer.tokenize(entity.text)
        except Exception:
            logger.exception("Failed to extract tokens from entity")
            return None

    def _query_documents_by_core_term(self, core_term: str) -> list[DocMeta]:
        """Query DynamoDB for documents with matching core term.

        Args:
            core_term: Core term to search for.

        Returns:
            List of matching document metadata.
        """
        try:
            return self._dynamo_client.query(
                table_name=self._table_name,
                index=self._index_name,
                pk=core_term
            )
        except Exception:
            logger.exception("Failed to query documents by core term")
            return []

    def _build_index_for_documents(self, doc_meta_list: list[DocMeta]) -> None:
        """Build multi-dimensional index for the given documents.

        Args:
            doc_meta_list: List of document metadata to index.
        """
        # Clear existing index
        self._index = MultiDimensionalIndex()

        for doc_meta in doc_meta_list:
            # Tokenize the document title
            try:
                token_span = self._tokenizer.tokenize(doc_meta.title)
                self._index.add_tokenized_document(doc_meta, token_span)
            except Exception as e:
                logger.warning(f"Failed to tokenize document '{doc_meta.title}': {e}")
                # Add document without tokenization
                self._index.add_document(doc_meta)

    def _perform_multi_dimensional_search(
        self,
        input_token_span: TokenSpan,
        law_title_entity: Entity
    ) -> set[str]:
        """Perform multi-dimensional search using the index.

        Args:
            input_token_span: Tokenized input title.
            law_title_entity: Original law title entity.

        Returns:
            Set of matching document IDs.
        """
        search_results: set[str] = set()

        # Extract search terms
        input_prefixes = [token.text for token in input_token_span.prefixes]
        input_suffixes = [token.text for token in input_token_span.suffixes]

        # Get attributes from the entity
        entity_attrs = self._extract_attributes_from_entity(law_title_entity)

        # Search by prefixes
        if input_prefixes:
            prefix_results = self._index.search_by_prefixes(input_prefixes)
            if not search_results:
                search_results = prefix_results
            else:
                search_results &= prefix_results

        # Search by suffixes
        if input_suffixes:
            suffix_results = self._index.search_by_suffixes(input_suffixes)
            if not search_results:
                search_results = suffix_results
            else:
                search_results &= suffix_results

        # Search by promulgators from entity attributes
        if entity_attrs.get('promulgators'):
            promulgator_results = self._index.search_by_promulgators(
                entity_attrs['promulgators']
            )
            if not search_results:
                search_results = promulgator_results
            else:
                search_results &= promulgator_results

        # Search by dates if available
        if entity_attrs.get('release_date') or entity_attrs.get('effective_date'):
            date_results = self._index.search_by_date_range(
                release_date_start=entity_attrs.get('release_date'),
                effective_date_start=entity_attrs.get('effective_date')
            )
            if not search_results:
                search_results = date_results
            else:
                search_results &= date_results

        return search_results

    def _extract_attributes_from_entity(self, entity: Entity) -> dict[str, Any]:
        """Extract attributes from a law title entity.

        Args:
            entity: Law title entity to extract attributes from.

        Returns:
            Dictionary of extracted attributes.
        """
        attrs: dict[str, Any] = {}

        # Extract attributes from entity.attrs
        for attr in entity.attrs:
            if attr.entity_type.value == 'PROMULGATOR':
                if 'promulgators' not in attrs:
                    attrs['promulgators'] = []
                attrs['promulgators'].append(attr.text)
            elif attr.entity_type.value == 'DATE':
                if 'release_date' not in attrs:
                    attrs['release_date'] = attr.text
            elif attr.entity_type.value == 'ISSUE_NO':
                attrs['issue_no'] = attr.text

        return attrs

    def _select_best_match(
        self,
        search_results: set[str],
        doc_meta_list: list[DocMeta]
    ) -> ValidationResult:
        """Select the best match from search results.

        Args:
            search_results: Set of matching document IDs.
            doc_meta_list: List of all document metadata.

        Returns:
            Validation result with the best match.
        """
        if not search_results:
            return ValidationResult(
                doc_meta=None,
                confidence_score=0.0,
                matched_attributes={},
                search_metadata={"matches_found": 0}
            )

        # Get matching documents
        matching_docs = [doc for doc in doc_meta_list if doc.doc_id in search_results]

        if not matching_docs:
            return ValidationResult(
                doc_meta=None,
                confidence_score=0.0,
                matched_attributes={},
                search_metadata={"matches_found": 0}
            )

        # Sort by release date (descending) and select the first one
        matching_docs.sort(key=lambda x: x.release_date, reverse=True)
        best_match = matching_docs[0]

        # Calculate confidence score based on number of matches
        confidence_score = 1.0 / len(matching_docs) if len(matching_docs) > 1 else 1.0

        return ValidationResult(
            doc_meta=best_match,
            confidence_score=confidence_score,
            matched_attributes={
                "total_matches": len(matching_docs),
                "release_date": best_match.release_date,
                "effective_date": best_match.effective_date,
                "promulgators": best_match.promulgators
            },
            search_metadata={
                "matches_found": len(matching_docs),
                "selected_doc_id": best_match.doc_id
            }
        )
