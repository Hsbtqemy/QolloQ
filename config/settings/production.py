from decouple import config as _cfg

from .base import *  # noqa: F401, F403

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Connexions DB persistantes (évite une reconnexion par requête)
DATABASES["default"]["CONN_MAX_AGE"] = 60  # noqa: F405

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# Mettre à False tant que le site tourne sans HTTPS ; passer à True une fois le SSL en place
SESSION_COOKIE_SECURE = _cfg("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = _cfg("CSRF_COOKIE_SECURE", default=True, cast=bool)
# SECURE_SSL_REDIRECT = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
