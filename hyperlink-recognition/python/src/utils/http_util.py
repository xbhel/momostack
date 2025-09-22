from __future__ import annotations

from typing import Any, ClassVar

from urllib3 import PoolManager, Retry, Timeout

from exceptions import RetryableException


class HttpClient:
    _instance: ClassVar[HttpClient]
    _pool: ClassVar[PoolManager]
    _default_retry_policy = Retry(
        total=5,
        backoff_factor=0.5,
        raise_on_status=False,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=("HEAD", "GET", "DELETE", "POST", "PUT"),
    )

    def __new__(
        cls, max_connection: int = 5, retry_policy: Retry | None = None
    ) -> HttpClient:
        if cls._instance is not None:
            return cls._instance

        instance = super().__new__(cls)
        if retry_policy is None:
            retry_policy = cls._default_retry_policy

        cls._pool = PoolManager(
            num_pools=max(max_connection, 1),
            retries=retry_policy,
            block=True,
            timeout=Timeout(connect=2.0, read=30.0),
        )
        cls._instance = instance
        return instance

    @property
    def pool(self) -> PoolManager:
        return self._pool

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        fields: dict[str, Any] | None = None,
        body: bytes | str | None = None,
        raise_on_status: bool = True,
        **kwargs: Any,
    ) -> Any:
        # Type ignore is used here because urllib3.PoolManager.request is untyped
        response = self._pool.request(  # type: ignore  # noqa: PGH003
            method, url, fields=fields, headers=headers, body=body, **kwargs
        )

        status_code = response.status
        if not (200 <= status_code < 300) and raise_on_status:
            description = (
                f"Request failed for {method} {url} with"
                f"status: {status_code} and error: {response.data}"
            )
            if status_code == 429 or status_code >= 500:
                raise RetryableException(description)

            raise RuntimeError(description)

        return response
