from django.db import connection
from redis import Redis
from redis.exceptions import RedisError


class DatabaseProbe:
    name = "database"

    def check(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()


class RedisProbe:
    name = "redis"

    def __init__(self, url: str, timeout: float = 2.0) -> None:
        self._client = Redis.from_url(url, socket_timeout=timeout, socket_connect_timeout=timeout)

    def check(self) -> None:
        try:
            if not self._client.ping():
                raise RedisError("Redis ping failed")
        except RedisError as exc:
            raise RuntimeError("Redis is unavailable") from exc
