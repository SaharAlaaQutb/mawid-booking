from drf_spectacular.extensions import OpenApiAuthenticationExtension


class LocaleAwareJWTAuthExtension(OpenApiAuthenticationExtension):
    target_class = "apps.core.presentation.authentication.LocaleAwareJWTAuthentication"
    name = "LocaleAwareJWTAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Bearer token issued by /api/auth/token/.",
        }
