from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / 'backend'
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault('SECRET_KEY', 'openapi-export-secret-key-1234567890')
os.environ.setdefault('OPENVIKING_ROOT_API_KEY', 'ov-openapi-export-key-1234567890')
os.environ.setdefault('OPENAI_API_KEY', 'openapi-export-openai-key')
os.environ.setdefault('DATABASE_URL', f"sqlite:///{(REPO_ROOT / 'data' / 'openapi-export.db').as_posix()}")
os.environ.setdefault('INITIAL_ADMIN_USERNAME', '')
os.environ.setdefault('INITIAL_ADMIN_PASSWORD', '')

from app.main import app  # noqa: E402
from app.schemas.chat import (  # noqa: E402
    ChatChunkSseEventResponse,
    ChatErrorSseEventResponse,
    ChatFinalSseEventResponse,
    ChatStreamEventResponse,
    ChatWorkflowSseEventResponse,
)


def _merge_schema_components(openapi_schema: dict[str, Any], name: str, schema_fragment: dict[str, Any]) -> None:
    components = openapi_schema.setdefault('components', {}).setdefault('schemas', {})
    defs = schema_fragment.pop('$defs', {})
    for def_name, def_schema in defs.items():
        components.setdefault(def_name, def_schema)
    components[name] = schema_fragment


def _inject_manual_components(openapi_schema: dict[str, Any]) -> None:
    _merge_schema_components(
        openapi_schema,
        'ChatWorkflowSseEventResponse',
        ChatWorkflowSseEventResponse.model_json_schema(ref_template='#/components/schemas/{model}'),
    )
    _merge_schema_components(
        openapi_schema,
        'ChatChunkSseEventResponse',
        ChatChunkSseEventResponse.model_json_schema(ref_template='#/components/schemas/{model}'),
    )
    _merge_schema_components(
        openapi_schema,
        'ChatErrorSseEventResponse',
        ChatErrorSseEventResponse.model_json_schema(ref_template='#/components/schemas/{model}'),
    )
    _merge_schema_components(
        openapi_schema,
        'ChatFinalSseEventResponse',
        ChatFinalSseEventResponse.model_json_schema(ref_template='#/components/schemas/{model}'),
    )
    _merge_schema_components(
        openapi_schema,
        'ChatStreamEventResponse',
        TypeAdapter(ChatStreamEventResponse).json_schema(ref_template='#/components/schemas/{model}'),
    )


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / 'frontend' / 'src' / 'api' / 'generated' / 'openapi.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    _inject_manual_components(schema)
    out_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'Wrote OpenAPI schema to {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
