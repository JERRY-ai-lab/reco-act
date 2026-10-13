"""public API 계약(OpenAPI) 스냅샷 테스트.

규칙(01-plan 7장): 기존 경로·스키마는 그대로 두고 추가만 허용한다.
이미 설치된 모바일 앱이 기존 형식을 쓰므로, 스냅샷에 있는 operation이나 component가
바뀌거나 없어지면 실패한다. 추가된 항목은 경고만 낸다.
의도한 변경이면 `pytest --update-openapi-snapshot`으로 스냅샷을 다시 만들고 diff를 리뷰한다.
"""
import copy
import json
import warnings
from pathlib import Path
from typing import List, Tuple

SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "openapi_public.json"


def diff_openapi(snapshot: dict, current: dict) -> Tuple[List[str], List[str]]:
    """스냅샷 대비 (problems, additions)를 돌려준다. problems가 비어 있어야 계약이 유지된 것이다."""
    problems: List[str] = []
    additions: List[str] = []

    # openapi 버전, info 등 paths·components 밖의 최상위 항목은 그대로여야 한다.
    for key in sorted((set(snapshot) | set(current)) - {"paths", "components"}):
        if snapshot.get(key) != current.get(key):
            problems.append(f"changed: {key}")

    snap_paths = snapshot.get("paths", {})
    cur_paths = current.get("paths", {})
    for path, operations in snap_paths.items():
        for method, operation in operations.items():
            cur_operation = cur_paths.get(path, {}).get(method)
            if cur_operation is None:
                problems.append(f"removed: {method.upper()} {path}")
            elif cur_operation != operation:
                problems.append(f"changed: {method.upper()} {path}")
    for path, operations in cur_paths.items():
        for method in operations:
            if method not in snap_paths.get(path, {}):
                additions.append(f"added: {method.upper()} {path}")

    # schemas, securitySchemes 등 component 종류별로 비교한다.
    snap_components = snapshot.get("components", {})
    cur_components = current.get("components", {})
    for section in sorted(set(snap_components) | set(cur_components)):
        snap_items = snap_components.get(section, {})
        cur_items = cur_components.get(section, {})
        for name, item in snap_items.items():
            if name not in cur_items:
                problems.append(f"removed: {section}.{name}")
            elif cur_items[name] != item:
                problems.append(f"changed: {section}.{name}")
        for name in cur_items:
            if name not in snap_items:
                additions.append(f"added: {section}.{name}")

    return problems, additions


def test_public_openapi_matches_snapshot(request):
    from main import app
    from utils.config import APP_PROFILE

    assert APP_PROFILE == "public"  # 스냅샷은 APP_PROFILE 미설정(=public) 기준이다

    # 스냅샷 파일과 같은 형태(JSON 타입)로 맞춰서 비교한다.
    current = json.loads(json.dumps(app.openapi()))

    if request.config.getoption("--update-openapi-snapshot"):
        SNAPSHOT_PATH.parent.mkdir(exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return

    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    problems, additions = diff_openapi(snapshot, current)
    if additions:
        warnings.warn("OpenAPI에 추가된 항목이 있다(스냅샷 갱신 필요):\n" + "\n".join(additions))
    assert not problems, (
        "public API 계약이 바뀌었다:\n" + "\n".join(problems)
        + "\n의도한 변경이면 `pytest --update-openapi-snapshot`으로 스냅샷을 갱신하고 diff를 리뷰한다."
    )


# ==================== diff_openapi 단위 테스트 ====================

_BASE = {
    "openapi": "3.1.0",
    "info": {"title": "t", "version": "1"},
    "paths": {"/a": {"get": {"responses": {"200": {"description": "ok"}}}}},
    "components": {"schemas": {"A": {"properties": {"x": {"type": "string"}}}}},
}


def _current() -> dict:
    return copy.deepcopy(_BASE)


def test_diff_identical():
    assert diff_openapi(_BASE, _current()) == ([], [])


def test_diff_removed_operation():
    current = _current()
    del current["paths"]["/a"]
    assert diff_openapi(_BASE, current) == (["removed: GET /a"], [])


def test_diff_changed_response():
    current = _current()
    current["paths"]["/a"]["get"]["responses"]["201"] = {"description": "created"}
    assert diff_openapi(_BASE, current) == (["changed: GET /a"], [])


def test_diff_changed_schema_field():
    # 기존 스키마에 필드를 더하는 것도 변경으로 본다(명시적으로 스냅샷을 갱신해야 함).
    current = _current()
    current["components"]["schemas"]["A"]["properties"]["y"] = {"type": "integer"}
    assert diff_openapi(_BASE, current) == (["changed: schemas.A"], [])


def test_diff_changed_info():
    current = _current()
    current["info"]["version"] = "2"
    assert diff_openapi(_BASE, current) == (["changed: info"], [])


def test_diff_additions_are_not_problems():
    current = _current()
    current["paths"]["/a"]["post"] = {"responses": {"200": {"description": "ok"}}}
    current["paths"]["/b"] = {"get": {"responses": {"200": {"description": "ok"}}}}
    current["components"]["schemas"]["B"] = {"properties": {}}
    problems, additions = diff_openapi(_BASE, current)
    assert problems == []
    assert sorted(additions) == ["added: GET /b", "added: POST /a", "added: schemas.B"]
