import logging
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

from linkgen.awsclients.dynamodb import DynamoDBWrapper
from linkgen.config import config
from linkgen.models import DocMeta, Entity, EntityType, TokenSpan
from linkgen.tokenizer import (
    LawTitleTokenizer,
    NestedLawTitleTokenizer,
    NoOpTokenizer,
    Tokenizer,
)
from linkgen.utils import text_util

__author__ = "xbhel"
__email__ = "xbhel@outlook.com"

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))

_dynamo_client = DynamoDBWrapper.us_east1_client()


@dataclass
class ValidationResult:
    """
    Represents the result of a validation process, encapsulating score and match details

    Attributes:
        doc_meta: The matched document metadata, or None if no match found.
        confidence_score: Confidence score between 0.0 and 1.0 indicating match quality.
        matched_attributes: Dictionary of attributes that were matched during validation
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
    def validate(self, entity: Entity, metadata: dict[str, Any]) -> ValidationResult:
        """
        Validate an entity and return a ValidationResult.

        Args:
        - entity: The entity to validate.
        - metadata: The metadata of the current document to use for validation.

        Returns:
            ValidationResult: The result of the validation.
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
    "inner_empty_prefix_index",
]
IndexKey = str | int | bool | float


class MultiDimensionalInvertedIndex:
    """
    An efficient inverted index for document searching and retrieval.

    This class maintains multiple inverted indexes for different document attributes
    and provides fast search capabilities.
    """

    _convert_to_fullname_indexes = {"prefix_index", "promulgator_index"}

    def __init__(self, promulgator_mapping: dict[str, str]) -> None:
        """Initialize the inverted index with empty data structures."""
        self._document_by_doc_id: dict[str, DocMeta] = {}
        self._inverted_indexes: dict[IndexName, dict[IndexKey, set[str]]] = {}
        self._promulgator_mapping = promulgator_mapping

    def __len__(self) -> int:
        """Get the number of documents in the index."""
        return len(self._document_by_doc_id)

    def search_by_index(
        self,
        index_name: IndexName,
        keys: Iterable[IndexKey],
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
        if not keys or not (index := self._inverted_indexes.get(index_name)):
            return set()

        if index_name in self._convert_to_fullname_indexes:
            keys = self._convert_to_fullname(keys)

        result: set[str] = set()

        # union search
        if union:
            for key in keys:
                result |= index.get(key, set())
            return result

        # intersection search
        for idx, key in enumerate(keys):
            values = index.get(key, set())
            if idx == 0:
                result = values.copy()
            else:
                result &= values
            if not result:
                break

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
            doc_id = doc_meta.doc_id
            self._document_by_doc_id[doc_id] = doc_meta
            logger.debug(
                "Added doc %r with token span %s to index.",
                doc_id,
                token_span.to_simple_json(),
            )

            date_index_keys = list(self._unpack_date(doc_meta.release_date))
            if doc_meta.effective_date:
                date_index_keys.extend(self._unpack_date(doc_meta.effective_date))

            # Update inverted index
            keys_by_index_name: dict[IndexName, Iterable[IndexKey]] = {
                "date_index": date_index_keys,
                "version_index": [doc_meta.version],
                "suffix_index": token_span.text_suffixes,
                "prefix_index": self._convert_to_fullname(token_span.text_prefixes),
                "promulgator_index": self._convert_to_fullname(doc_meta.promulgators),
            }

            if doc_meta.effective_scope:
                keys_by_index_name["scope_index"] = [doc_meta.effective_scope]

            if not token_span.prefixes:
                keys_by_index_name["empty_prefix_index"] = [token_span.core_term]

            if inner := token_span.inner:
                keys_by_index_name["inner_empty_prefix_index"] = [inner.core_term]

            # Update all relevant indexes
            for index_name, keys in keys_by_index_name.items():
                if keys:  # Only update if there are keys to add
                    self._update_inverted_index(index_name, keys, doc_meta.doc_id)
        except Exception:
            logger.exception(f"Failed to add doc '{doc_id}: {doc_meta.title}' to index")
            raise

    def _update_inverted_index(
        self, index_name: IndexName, keys: Iterable[IndexKey], value: str
    ) -> None:
        """
        Update an inverted index with new key-value mappings.
        """
        inverted_index = self._inverted_indexes.get(index_name)
        if inverted_index is None:
            inverted_index = defaultdict(set)
            self._inverted_indexes[index_name] = inverted_index

        for key in keys:
            inverted_index[key].add(value)

    def _convert_to_fullname(self, prefixes: Iterable[IndexKey]) -> list[str]:
        return [self._promulgator_mapping.get(str(x), str(x)) for x in prefixes]

    @staticmethod
    def _unpack_date(epoch_seconds: int) -> list[str]:
        year, month, day = text_util.unpack_date(epoch_seconds)
        return [f"{year}{month:02d}{day:02d}", f"{year}{month:02d}", f"{year}"]


class LawTitleValidator(Validator):
    """
    Validator for law title entities using tokenization and document matching.

    This validator uses multiple tokenization strategies to match law titles
    against a document database, providing confidence scores and match details.
    """

    _country_scope: str = config["country_scope"]
    _about_chinese: str = config["about_chinese"]
    _common_prefixes: tuple[str] = config["common_prefixes"]
    _ineffective_status = frozenset(config["ineffective_status"])

    def __init__(self, promulgator_mapping: dict[str, str]) -> None:
        """
        Initialize the law validator.

        Args:
            promulgators: List of promulgator names to use for tokenization.
        """
        promulgators = list(promulgator_mapping)
        self._promulgator_mapping = promulgator_mapping
        self._promulgators = set(promulgator_mapping)

        # initialize tokenizers
        self._no_op_tokenizer = NoOpTokenizer()
        self._nested_tokenizer = NestedLawTitleTokenizer(promulgators)
        self._strict_tokenizer = LawTitleTokenizer(
            [*promulgators, self._about_chinese],
            strict=True,
            last_only_prefixes=[self._about_chinese],
        )
        self._strict_nested_tokenizer = NestedLawTitleTokenizer(
            promulgators, strict=True
        )

    def validate(self, entity: Entity, metadata: dict[str, Any]) -> ValidationResult:
        # Step 1: Extract core term and attributes from entity
        core_term = self._extract_core_term_from_entity(entity)
        attributes = self._extract_attributes_from_entity(entity)
        logger.info(
            "Validating entity %r with core term %r and attributes %r",
            entity.text,
            core_term,
            attributes,
        )

        # Step 2: Query DynamoDB for documents with matching core term
        doc_meta_list = self._query_documents_by_core_term(core_term, metadata)

        # Step 3: Extract token span from entity with strict mode
        token_span, is_nested_entity = self._extract_token_span_from_entity(entity)
        logger.info(
            "Tokenized %r entity %r with in strict mode to token span: %r",
            "nested" if is_nested_entity else "non-nested",
            entity.text,
            token_span.to_simple_json(),
        )

        # Step 4: Build multi-dimensional index for the retrieved documents
        inverted_index = self._build_multi_dim_inverted_index(
            doc_meta_list, token_span, is_nested_entity
        )

        # Step 5: Perform multi-dimensional search
        search_results = self._perform_multi_dimensional_search(
            token_span, attributes, inverted_index
        )

        print(f"Search results: {search_results}")

        # Step 6: Rank and select the best match

        return ValidationResult(
            doc_meta=None,
            confidence_score=0.0,
            matched_attributes={},
            search_metadata={},
        )

    def _perform_multi_dimensional_search(
        self,
        token_span: TokenSpan,
        attributes: dict[EntityType, set[str]],
        inverted_index: MultiDimensionalInvertedIndex,
    ) -> set[str]:
        """
        Perform multi-dimensional search.
        """
        # Step1: Search by prefixes.
        matched_doc_ids = self._search_by_prefixes(
            token_span, attributes, inverted_index
        )

        # Step2: Further filter by suffixes.
        if matched_doc_ids and token_span.suffixes:
            matched_doc_ids &= inverted_index.search_by_index(
                "suffix_index", token_span.text_suffixes
            )

        # Step3: Further filter by attributes.
        if matched_doc_ids and attributes:
            matched_doc_ids &= self._search_by_attributes(attributes, inverted_index)

        return matched_doc_ids

    def _search_by_prefixes(
        self,
        token_span: TokenSpan,
        attributes: dict[EntityType, set[str]],
        index: MultiDimensionalInvertedIndex,
    ) -> set[str]:
        """
        Search by prefix-related signals.
        """
        # Step1: If the token span has prefixes, search by prefixes.
        if token_span.prefixes:
            return index.search_by_index("prefix_index", token_span.text_prefixes)

        # Step2: If the token span has no prefixes,
        # union the empty prefix index and the common prefix index,
        # And union the promulgator index if there are promulgators in the attributes.
        core_term = token_span.core_term
        candidates: set[str] = set()
        non_prefix_specs: dict[IndexName, tuple[Iterable[str], bool]] = {
            "empty_prefix_index": ([core_term], False),
            "prefix_index": (self._common_prefixes, True),
        }
        if promulgators := attributes.get(EntityType.PROMULGATOR):
            non_prefix_specs["promulgator_index"] = (promulgators, False)
        for index_name, (keys, union) in non_prefix_specs.items():
            candidates |= index.search_by_index(index_name, keys, union)
        if candidates:
            return candidates

        # Step3: If the candidates are empty, search by country scope only.
        if countryed := index.search_by_index("scope_index", [self._country_scope]):
            nested_candidates = index.search_by_index(
                "inner_empty_prefix_index", [True]
            )
            about_prefixes = index.search_by_index(
                "prefix_index", [self._about_chinese]
            )
            countryed &= nested_candidates | about_prefixes
        return countryed

    def _search_by_attributes(
        self,
        attributes: dict[EntityType, set[str]],
        index: MultiDimensionalInvertedIndex,
    ) -> set[str]:
        """
        Search by attributes.
        """
        index_attribute_map: dict[IndexName, Iterable[str] | None] = {
            "date_index": attributes.get(EntityType.DATE),
            "version_index": attributes.get(EntityType.ISSUE_NO),
            "promulgator_index": attributes.get(EntityType.PROMULGATOR),
        }
        candidates: set[str] = set()
        for index_name, attr_values in index_attribute_map.items():
            if attr_values:
                candidates |= index.search_by_index(index_name, attr_values)
        return candidates

    def _build_multi_dim_inverted_index(
        self,
        doc_meta_list: list[DocMeta],
        token_span: TokenSpan,
        is_nested_entity: bool,
    ) -> MultiDimensionalInvertedIndex:
        """
        Build a multi-dimensional inverted index for the documents.
        """
        inverted_index = MultiDimensionalInvertedIndex(self._promulgator_mapping)
        for doc_meta in doc_meta_list:
            doc_token_span = self._extract_token_span_from_document(
                doc_meta, is_nested_entity
            )
            if doc_token_span.core_term == token_span.core_term:
                inverted_index.add_tokenized_document(doc_meta, doc_token_span)

        logger.info(
            f"Found {len(inverted_index)} strict matches out of "
            f"{len(doc_meta_list)} candidates for core term '{token_span.core_term}'"
        )
        return inverted_index

    def _is_valid_document(self, doc_meta: DocMeta, metadata: dict[str, Any]) -> bool:
        doc_type = metadata["doc_type"]
        current_doc_id = metadata["doc_id"]
        release_date = metadata["release_date"]

        is_future_released = _is_after(doc_meta.release_date, release_date)
        if is_future_released:
            logger.info(
                f"Ignored document {doc_meta.doc_id} "
                f"because it is future released compared to current {current_doc_id}"
            )
            return False

        if doc_type in {"Case", "Administrative Penalty"}:
            is_future_effective = _is_after(doc_meta.effective_date, release_date)
            is_ineffective_status = (
                doc_meta.effective_status in self._ineffective_status
            )
            if is_future_effective or is_ineffective_status:
                logger.info(
                    f"Ignored document {doc_meta.doc_id} "
                    f"because it is not effective compared to current {current_doc_id}"
                )
                return False

        return True

    def _extract_token_span_from_document(
        self, doc_meta: DocMeta, is_nested_entity: bool
    ) -> TokenSpan:
        tokenizer = self._get_document_tokenizer(doc_meta, is_nested_entity)
        logger.debug(
            f"Tokenized doc '{doc_meta.doc_id}: {doc_meta.title}' by "
            f"{tokenizer.__class__.__name__}",
        )
        return tokenizer.tokenize(doc_meta.title)

    def _extract_token_span_from_entity(self, entity: Entity) -> tuple[TokenSpan, bool]:
        token_span = self._strict_nested_tokenizer.tokenize(entity.text)
        is_nested_entity = token_span.nested
        # if the entity is nested, use the outer token span
        if token_span.outer:
            token_span = token_span.outer
        return token_span, is_nested_entity

    def _extract_attributes_from_entity(
        self, entity: Entity
    ) -> dict[EntityType, set[str]]:
        """
        Extract attributes from an entity.
        """
        attrs: dict[EntityType, set[str]] = defaultdict(set)
        for attr in entity.attrs:
            attrs[attr.entity_type].add(attr.text)
        return attrs

    def _extract_core_term_from_entity(self, entity: Entity) -> str:
        """
        Extract the core term from an entity using the non-strict nested tokenizer.
        """
        return self._nested_tokenizer.tokenize(entity.text).core_term

    def _get_document_tokenizer(
        self, doc_meta: DocMeta, is_nested_entity: bool
    ) -> Tokenizer:
        """
        Get the appropriate tokenizer for the document.
        """
        # if the document is not a legislation, we don't need to tokenize it
        # such as Practice guidelines
        if doc_meta.doc_type != "Legislation":
            return self._no_op_tokenizer

        # if the entity is nested or the document is not a country law
        # then we need to use the strict tokenizer
        # 关于发布《贵州省xxx》的通知 -> effective_scope = '贵州省'
        # MOST DOCUMENT FALL INTO THIS CATEGORY
        if is_nested_entity or doc_meta.effective_scope != self._country_scope:
            return self._strict_tokenizer

        # If the entity is not nested and the document is a country law
        # then we need to use the strict nested tokenizer
        new_promulgators = set(doc_meta.promulgators) - self._promulgators
        # create a new tokenizer if there are new promulgators
        if new_promulgators:
            return NestedLawTitleTokenizer(
                self._promulgators | new_promulgators, strict=True
            )
        return self._strict_nested_tokenizer

    def _query_documents_by_core_term(
        self, core_term: str, metadata: dict[str, Any]
    ) -> list[DocMeta]:
        """
        Query documents from DynamoDB by core term.
        """
        doc_meta_iterator = _dynamo_client.query(
            TableName="doc_meta",
            IndexName="core_term-release_date-index",
            KeyConditionExpression="#core_term = :core_term",
            FilterExpression="contains(#type, :doc_type) and #status = :status",
            ExpressionAttributeValues={
                ":status": {"N": "1"},
                ":core_term": {"S": core_term},
                ":doc_type": {"S": "Legislation"},
            },
            ExpressionAttributeNames={
                "#core_term": "core_term",
                "#type": "doc_type",
                "#status": "status",
            },
        )
        doc_meta_list = [DocMeta(**doc_meta) for doc_meta in doc_meta_iterator]
        return [x for x in doc_meta_list if self._is_valid_document(x, metadata)]


def _is_after(
    epoch_seconds: int | None,
    date_string: str | None,
    none_value: str = "0000-00-00",
) -> bool:
    if epoch_seconds and date_string and date_string != none_value:
        return epoch_seconds > text_util.as_shanghai_epoch_seconds(date_string)
    return False
