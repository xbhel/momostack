import logging
from typing import TYPE_CHECKING, Any

from linkgen import validator
from linkgen.models import Entity, EntityType
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
                "DocMetaMapping.json"
            )
            return iter(doc_meta_list)

    validator._dynamo_client = cast("DynamoDBWrapper", MockDynamoDBClient())  # noqa: SLF001

    law_title_validator = validator.LawTitleValidator(
        {
            "中国人民银行": "中国人民银行",
            "中国注册会计师协会": "中国注册会计师协会",
            "上海证券交易所": "上海证券交易所",
            "上交所": "上海证券交易所",
            "深圳证券交易所": "深圳证券交易所",
            "深交所": "深圳证券交易所",
        }
    )

    law_title_validator.validate(
        Entity(
            text="深圳证券交易所章程",
            start=0,
            end=10,
            entity_type=EntityType.LAW_TITLE,
            attrs=[
                Entity(
                    text="2018",
                    start=0,
                    end=10,
                    entity_type=EntityType.DATE,
                ),
            ],
        ),
        {
            "doc_id": "law_004",
            "doc_type": "Legislation",
            "release_date": None,
        },
    )
