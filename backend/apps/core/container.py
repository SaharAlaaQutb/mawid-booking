from django.conf import settings

from apps.core.application.health import HealthProbe, HealthService
from apps.core.infrastructure.probes import DatabaseProbe, RedisProbe


def build_health_service() -> HealthService:
    probes: list[HealthProbe] = [DatabaseProbe()]
    redis_url: str = settings.REDIS_URL
    if redis_url:
        probes.append(RedisProbe(redis_url))
    return HealthService(probes)
