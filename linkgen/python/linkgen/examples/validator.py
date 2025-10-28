import logging
from typing import TYPE_CHECKING, Any

from linkgen import searcher
from linkgen.models import DocMeta, EntityDTO, EntityType
from linkgen.utils import io_util

if TYPE_CHECKING:
    from linkgen.awsclients.dynamodb import DynamoDBWrapper

if __name__ == "__main__":
    from collections.abc import Iterator
    from typing import cast

    logging.basicConfig(level=logging.INFO)

    # mock the dynamo client
    class MockDynamoDBClient:
        def query(self, *_: Any, **__: Any) -> Iterator[dict[str, Any]]:
            doc_meta_list: list[dict[str, Any]] = io_util.load_resource_json(
                "doc_meta_list.json"
            )
            return iter(doc_meta_list)

    searcher._dynamo_client = cast("DynamoDBWrapper", MockDynamoDBClient())  # noqa: SLF001

    metadata = DocMeta(
        doc_id="doc_001",
        doc_type="Legislation",
        doc_url="https://example.com/doc_001",
        title="xxx",
        core_term="xxx",
        status="1",
        created_at=1641081600,
        updated_at=1641081600,
        release_date=1641340800,
        version="",
        version_timestamp=1641081600,
        promulgators=[],
        effective_status="",
        effective_scope="",
        effective_date=1641081600,
    )
    result = searcher.search(
        EntityDTO(
            text="深圳证券交易所章程",
            entity_type=EntityType.LAW_TITLE,
            attrs={EntityType.DATE: {"2018"}},
        ),
        metadata,
    )
    print(result)
