import os
import sys

from .common import *

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.mysql"),
        "NAME": os.environ.get("DB_NAME", "edx_notes_api"),
        "USER": os.environ.get("DB_USER", "notes001"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "secret"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "connect_timeout": int(os.environ.get("CONN_MAX_AGE", 0)),
        },
    }
}

DEFAULT_NOTES_PAGE_SIZE = 10

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"level": "DEBUG", "class": "logging.StreamHandler", "stream": sys.stderr}
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "elasticsearch.trace": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}

ELASTICSEARCH_DSL = {"default": {"hosts": os.environ.get("ELASTICSEARCH_URL", "localhost:9200")}}
ELASTICSEARCH_INDEX_NAMES = {"notesapi.v1.search_indexes.documents.note": "notes_index_test"}

JWT_AUTH = {}
