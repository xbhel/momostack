import logging
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from linkgen.awsclients.dynamodb import DynamoDBWrapper
from linkgen.models import DocMeta, Entity, TokenSpan
from linkgen.tokenizer import LawTitleTokenizer, NestedLawTitleTokenizer, Tokenizer

__author__ = "xbhel"
__email__ = "xbhel@outlook.com"

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))

_dynamo_client = DynamoDBWrapper.us_east1_client()


@dataclass
class ValidationResult:
    """
    Represents the result of a validation process, encapsulating score and match details.

    Attributes:
        doc_meta: The matched document metadata, or None if no match found.
        confidence_score: Confidence score between 0.0 and 1.0 indicating match quality.
        matched_attributes: Dictionary of attributes that were matched during validation.
        search_metadata: Additional metadata about the search process.
    """

    doc_meta: DocMeta | None
    confidence_score: float
    matched_attributes: dict[str, Any]
    search_metadata: dict[str, Any]


class Validator(ABC):
    """
    Abstract base class for entities that perform validation.
    """

    @abstractmethod
    def validate(self, entity: Entity) -> ValidationResult:
        """
        Validate an entity and return a ValidationResult.
        """
        raise NotImplementedError


IndexName = Literal[
    "prefix_index",
    "suffix_index",
    "date_index",
    "version_index",
    "promulgator_index",
    "scope_index",
    "empty_prefix_index",
    "empty_suffix_index",
]


class InvertedIndex:
    """
    An efficient inverted index for document searching and retrieval.

    This class maintains multiple inverted indexes for different document attributes
    and provides fast intersection-based search capabilities.
    """

    def __init__(self) -> None:
        """Initialize the inverted index with empty data structures."""
        self._document_by_doc_id: dict[str, DocMeta] = {}
        self._inverted_indexes: dict[IndexName, dict[str, set[str]]] = {}

    def search_by_index(
        self,
        index_name: IndexName,
        keys: list[str],
        union: bool = False,
    ) -> set[str]:
        """
        Search for documents using an inverted index.
        Default is intersection search.

        Args:
        - index_name: The name of the index to search.
        - keys: List of keys to search for (intersection of all keys).
        - union: Whether to perform a union or intersection search.


        Returns:
            Set of document IDs that match all the provided keys.
        """
        if not keys:
            return set()

        inverted_index = self._inverted_indexes.get(index_name)
        if not inverted_index:
            return set()

        result = inverted_index.get(keys[0], set()).copy()
        if union:
            for key in keys[1:]:
                result |= inverted_index.get(key, set())
        else:
            for key in keys[1:]:
                result &= inverted_index.get(key, set())
        return result

    def get_document(self, doc_id: str) -> DocMeta | None:
        """Get a document by its ID."""
        return self._document_by_doc_id.get(doc_id)

    def get_documents(self, doc_ids: set[str]) -> list[DocMeta]:
        """Get multiple documents by their IDs."""
        return [
            self._document_by_doc_id[doc_id]
            for doc_id in doc_ids
            if doc_id in self._document_by_doc_id
        ]

    def add_tokenized_document(self, doc_meta: DocMeta, token_span: TokenSpan) -> None:
        """
        Add a tokenized document to the index.

        Args:
            doc_meta: Document metadata to index.
            token_span: Tokenized document title.
        """
        try:
            # Update document by doc_id
            self._document_by_doc_id[doc_meta.doc_id] = doc_meta
            logger.debug(f"Added document {doc_meta.doc_id} to index")

            # Update inverted index
            keys_by_index_name: dict[IndexName, list[str]] = {
                "prefix_index": token_span.text_prefixes,
                "suffix_index": token_span.text_suffixes,
                "version_index": [doc_meta.issue_no],
                "promulgator_index": doc_meta.promulgators,
                "scope_index": [doc_meta.effective_scope],
                "date_index": [doc_meta.release_date, doc_meta.effective_date],
            }

            # Handle empty prefixes/suffixes
            if not token_span.prefixes:
                keys_by_index_name["empty_prefix_index"] = [token_span.core_term]

            if not token_span.suffixes:
                keys_by_index_name["empty_suffix_index"] = [token_span.core_term]

            # Update all relevant indexes
            for index_name, keys in keys_by_index_name.items():
                if keys:  # Only update if there are keys to add
                    self._update_inverted_index(index_name, keys, doc_meta.doc_id)
        except Exception:
            logger.exception(f"Failed to add document {doc_meta.doc_id} to index")
            raise

    def _update_inverted_index(
        self, index_name: IndexName, keys: list[str], value: str
    ) -> None:
        """
        Update an inverted index with new key-value mappings.
        """
        inverted_index = self._inverted_indexes.get(index_name)
        if inverted_index is None:
            inverted_index = defaultdict(set)
            self._inverted_indexes[index_name] = inverted_index

        for key in keys:
            if key:  # Only add non-empty keys
                inverted_index[key].add(value)


class LawTitleValidator(Validator):
    """
    Validator for law title entities using tokenization and document matching.

    This validator uses multiple tokenization strategies to match law titles
    against a document database, providing confidence scores and match details.
    """

    def __init__(self, promulgators: list[str]) -> None:
        """
        Initialize the law validator.

        Args:
            promulgators: List of promulgator names to use for tokenization.
        """
        self._promulgators = set(promulgators)
        self._strict_tokenizer = LawTitleTokenizer(promulgators, strict=True)
        self._nested_tokenizer = NestedLawTitleTokenizer(promulgators)
        self._strict_nested_tokenizer = NestedLawTitleTokenizer(
            promulgators, strict=True
        )

    def validate(self, entity: Entity) -> ValidationResult:
        # Extract core term from entity
        core_term = self._get_core_term_from_entity(entity)

        # Query DynamoDB for documents with matching core term
        doc_meta_list = self._query_documents_by_core_term(core_term)

        # Extract token span from entity
        token_span, is_nested_entity = self._get_token_span_from_entity(entity)

        # Build multi-dimensional index for the retrieved documents
        inverted_index = self._build_inverted_index(
            doc_meta_list, token_span, is_nested_entity
        )

        # Step 4: Perform multi-dimensional search
        search_results = self._perform_multi_dimensional_search(
            inverted_index, token_span, allow_missing_prefix=True
        )

        # Step 5: Rank and select the best match

        return ValidationResult(
            doc_meta=None,
            confidence_score=0.0,
            matched_attributes={},
            search_metadata={},
        )

    def _perform_multi_dimensional_search(
        self,
        inverted_index: InvertedIndex,
        token_span: TokenSpan,
        allow_missing_prefix: bool = True,
    ) -> set[str]:
        """
        Perform multi-dimensional search.
        """
        if token_span.prefixes:
            result = inverted_index.search_by_index(
                "prefix_index", token_span.text_prefixes
            )
        else:
            empty_prefix_result = inverted_index.search_by_index(
                "empty_prefix_index", [token_span.core_term]
            )
            common_prefix_result = inverted_index.search_by_index(
                "prefix_index", ["中华人民共和国", "关于"], union=True
            )
            result = empty_prefix_result | common_prefix_result
            if allow_missing_prefix and not result:
                result = inverted_index.search_by_index(
                    "scope_index", ["country"]
                )
        return result

    def _build_inverted_index(
        self,
        doc_meta_list: list[DocMeta],
        token_span: TokenSpan,
        is_nested_entity: bool,
    ) -> InvertedIndex:
        """
        Query documents that match the entity's core term.
        """
        count = 0
        inverted_index = InvertedIndex()
        for doc_meta in doc_meta_list:
            tokenizer = self._get_document_tokenizer(
                doc_meta,
                is_nested_entity,
            )
            doc_token_span = tokenizer.tokenize(doc_meta.title)
            if doc_token_span.core_term == token_span.core_term:
                inverted_index.add_tokenized_document(doc_meta, token_span)
                count += 1

        logger.info(
            f"Found {count} strict matches out of {len(doc_meta_list)} candidates "
            f"for core term {token_span.core_term}"
        )
        return inverted_index

    def _get_document_tokenizer(
        self, doc_meta: DocMeta, is_nested_entity: bool
    ) -> Tokenizer:
        """
        Get the appropriate tokenizer for the document.
        """
        # If the entity is not nested and the document is a country law
        # then we need to use the strict nested tokenizer
        if not is_nested_entity and doc_meta.effective_scope == "country":
            new_promulgators = set(doc_meta.promulgators) - self._promulgators
            if new_promulgators:
                return NestedLawTitleTokenizer(
                    self._promulgators | new_promulgators, strict=True
                )

        # If the entity is nested or the document is not a country law
        # then we need to use the strict tokenizer
        return self._strict_tokenizer

    def _query_documents_by_core_term(self, core_term: str) -> list[DocMeta]:
        """
        Query documents from DynamoDB by core term.
        """
        doc_meta_iterator = _dynamo_client.query(
            TableName="doc_meta",
            IndexName="core_term-release_date_index",
            KeyConditionExpression="core_term = :core_term",
            ExpressionAttributeValues={":core_term": core_term},
        )
        return [DocMeta(**doc_meta) for doc_meta in doc_meta_iterator]

    def _get_token_span_from_entity(self, entity: Entity) -> tuple[TokenSpan, bool]:
        token_span = self._strict_nested_tokenizer.tokenize(entity.text)
        is_nested_entity = token_span.nested
        # Use the strict non-nested tokenizer if the entity is nested
        if is_nested_entity:
            token_span = self._strict_tokenizer.tokenize(entity.text)
        return token_span, is_nested_entity

    def _get_core_term_from_entity(self, entity: Entity) -> str:
        """
        Get the core term from an entity using the non-strict nested tokenizer.
        """
        return self._nested_tokenizer.tokenize(entity.text).core_term
