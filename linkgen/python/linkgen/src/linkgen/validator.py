from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Literal, override

from linkgen.awsclients.dynamodb import DynamoDBWrapper
from linkgen.models import DocMeta, Entity, TokenSpan
from linkgen.tokenizer import LawTitleTokenizer, NestedLawTitleTokenizer

_dynamo_client = DynamoDBWrapper.us_east1_client()

IndexName = Literal[
    "prefix_index",
    "suffix_index",
    "release_date_index",
    "effective_date_index",
    "issue_no_index",
    "promulgator_index",
    "normalized_text_index",
]


class ValidationResult:
    doc_meta: DocMeta | None
    confidence_score: float
    matched_attributes: dict[str, Any]
    search_metadata: dict[str, Any]


class Validator(ABC):
    @abstractmethod
    def validate(self, entity: Entity) -> ValidationResult:
        raise NotImplementedError


class MultiDimInvertedIndex:
    def __init__(self) -> None:
        self._doc_meta_by_doc_id: dict[str, DocMeta] = {}
        self._inverted_indexes: dict[str, dict[str, set[str]]] = {}

    def search_by_index(self, index_name: IndexName, keys: list[str]) -> set[str]:
        if not keys:
            return set()

        inverted_index = self._inverted_indexes.get(index_name)
        if inverted_index is None:
            return set()

        # Start with documents matching the first prefix
        result = inverted_index.get(keys[0], set()).copy()
        # Intersect with documents matching subsequent prefixes
        for key in keys[1:]:
            result &= inverted_index.get(key, set())

        return result

    def get_document(self, doc_id: str) -> DocMeta | None:
        """Get document metadata by ID."""
        return self._doc_meta_by_doc_id.get(doc_id)

    def get_documents(self, doc_ids: set[str]) -> list[DocMeta]:
        """Get multiple documents by IDs."""
        return [
            self._doc_meta_by_doc_id[doc_id]
            for doc_id in doc_ids
            if doc_id in self._doc_meta_by_doc_id
        ]

    def add_tokenized_document(self, doc_meta: DocMeta, token_span: TokenSpan) -> None:
        """Add a tokenized document to the index.

        Args:
            doc_meta: Document metadata to index.
            token_span: Tokenized document title.
        """
        doc_id = doc_meta.doc_id

        # Update doc_meta_by_doc_id
        self._doc_meta_by_doc_id[doc_id] = doc_meta

        # Update indexes
        index_keys_by_index_name = {
            "issue_no_index": [doc_meta.issue_no],
            "promulgator_index": doc_meta.promulgators,
            "release_date_index": [doc_meta.release_date],
            "effective_date_index": [doc_meta.effective_date],
            "suffix_index": [x.text for x in token_span.suffixes],
            "prefix_index": [x.text for x in token_span.prefixes],
            "normalized_text_index": [token_span.normalized_text],
        }

        for index_name, keys in index_keys_by_index_name.items():
            self._update_index(index_name, keys, doc_id)

    def _update_index(self, index_name: str, index_keys: list[str], value: str) -> None:
        inverted_index = self._inverted_indexes.get(index_name)

        if inverted_index is None:
            inverted_index = defaultdict(set)
            self._inverted_indexes[index_name] = inverted_index

        for key in index_keys:
            inverted_index[key].add(value)


class LawTitleValidator(Validator):
    def __init__(self, promulgators: list[str]) -> None:
        self._promulgators = promulgators
        self._nested_tokenizer = NestedLawTitleTokenizer(promulgators)
        self._strict_tokenizer = LawTitleTokenizer(promulgators, strict=True)
        self._strict_nested_tokenizer = NestedLawTitleTokenizer(
            promulgators, strict=True
        )

    @override
    def validate(self, entity: Entity) -> ValidationResult:
        # Extract core term from input using non-strict tokenizer
        token_span = self._nested_tokenizer.tokenize(entity.text)
        # Query DynamoDB for documents with matching core term
        doc_meta_list = self._query_documents(token_span.core.text)

        strict_token_span = self._strict_nested_tokenizer.tokenize(entity.text)

        # Build multi-dimensional index for the retrieved documents
        inverted_index = self._build_inverted_index(doc_meta_list, strict_token_span)
        print(inverted_index)

        # Step 4: Perform multi-dimensional search

        # Step 5: Rank and select the best match

        return ValidationResult()

    def _extract_core_term(self, entity: Entity) -> str:
        token_span = self._nested_tokenizer.tokenize(entity.text)
        return token_span.core.text

    def _query_documents(self, core_term: str) -> list[DocMeta]:
        doc_meta_iterator = _dynamo_client.query(
            TableName="doc_meta",
            IndexName="core_term-release_date_index",
            KeyConditionExpression="core_term = :core_term",
            ExpressionAttributeValues={":core_term": core_term},
        )
        return [DocMeta(**doc_meta) for doc_meta in doc_meta_iterator]

    def _build_inverted_index(
        self,
        doc_meta_list: list[DocMeta],
        strict_token_span: TokenSpan,
    ) -> MultiDimInvertedIndex:
        inverted_index = MultiDimInvertedIndex()
        core_term = strict_token_span.core.text

        for doc_meta in doc_meta_list:
            tokenizer = self._get_document_tokenizer(doc_meta)
            doc_token_span = tokenizer.tokenize(doc_meta.title)
            if doc_token_span.core.text == core_term:
                inverted_index.add_tokenized_document(doc_meta, doc_token_span)

        return inverted_index

    def _get_document_tokenizer(self, doc_meta: DocMeta) -> LawTitleTokenizer:
        if doc_meta.effective_scope == "country":
            sources = doc_meta.promulgators
            if any(x not in self._promulgators for x in sources):
                return NestedLawTitleTokenizer(
                    self._promulgators + sources, strict=True
                )

        return self._strict_tokenizer
