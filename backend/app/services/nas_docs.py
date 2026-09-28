"""
app/services/nas_docs.py — NAS 납품문서 폴더 연동 (읽기 전용)

백엔드 컨테이너에 마운트된 사내 문서 공유폴더를 탐색한다.
구조: {년도}/{업무구분}/{고객사}/{월}/{프로젝트 폴더}/

1단계에서는 경로를 '조립'하지 않고 PO 번호로 '검색'한다.
폴더명 규칙이 건마다 달라(날짜 접두, POXXXXXX, 표기 차이) 규칙을 가정하면
기존 폴더를 찾지 못하기 때문이다. 한 번 찾은 경로는 projects.nas_path 에 기억한다.

보안: 모든 경로는 DOCS_ROOT 하위인지 확인한 뒤에만 접근한다 (경로 탈출 차단).
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 컨테이너에 마운트된 문서 루트. 마운트하지 않으면 기능 전체가 비활성화된다.
DOCS_ROOT = Path(os.getenv("DOCS_ROOT", "/mnt/docs"))

# 목록에서 감출 파일 — 윈도우/엑셀이 만드는 부산물
_HIDDEN_EXACT = {"thumbs.db", "desktop.ini", ".ds_store"}
_HIDDEN_PREFIX = ("~$", ".")

# 검색 깊이: {년도}/{업무구분}/{고객사}/{월}/{프로젝트} = 5단계
_PROJECT_DEPTH = 5


def is_enabled() -> bool:
    """문서 폴더가 실제로 마운트되어 있는지."""
    try:
        return DOCS_ROOT.is_dir()
    except OSError:
        return False


def _resolved_root() -> Path:
    """
    심볼릭 링크·매핑 드라이브가 풀린 실제 루트.
    개별 경로는 resolve() 를 거치므로, 상대경로를 만들 때도 같은 기준을 써야 한다.
    (예: 윈도우에서 Z:\\ 는 \\\\192.168.0.22\\... 로 풀린다)
    """
    return DOCS_ROOT.resolve()


def _to_relative(path: Path) -> str:
    """DOCS_ROOT 기준 상대경로 문자열 (항상 / 구분자)."""
    return str(path.resolve().relative_to(_resolved_root())).replace("\\", "/")


def _is_hidden(name: str) -> bool:
    low = name.lower()
    return low in _HIDDEN_EXACT or low.startswith(_HIDDEN_PREFIX)


def safe_join(relative: str) -> Path:
    """
    DOCS_ROOT 기준 상대경로를 안전하게 결합한다.
    '..' 등으로 루트를 벗어나려는 경로는 거부한다.
    """
    candidate = (DOCS_ROOT / (relative or "")).resolve()
    root = _resolved_root()
    if candidate != root and root not in candidate.parents:
        raise ValueError("허용되지 않은 경로입니다.")
    return candidate


def resolve_within(base_relative: str, sub_relative: str | None) -> str:
    """
    base_relative 폴더 '안쪽'으로만 이동을 허용하고, 결과 상대경로를 돌려준다.
    루트 하위인지만 보면 '..' 로 다른 프로젝트 폴더를 훑을 수 있으므로,
    프로젝트 폴더 기준으로도 한 번 더 가둔다.
    """
    base = safe_join(base_relative)
    target = safe_join(f"{base_relative}/{sub_relative}" if sub_relative else base_relative)
    if target != base and base not in target.parents:
        raise ValueError("허용되지 않은 경로입니다.")
    return _to_relative(target)


def _normalize(text: str) -> str:
    """PO 번호 비교용 정규화 — 대소문자·구분자 무시."""
    return re.sub(r"[^A-Za-z0-9]", "", text or "").upper()


def find_project_folder(
    po_number: str, *, max_scan: int = 20000, max_years: int | None = None
) -> str | None:
    """
    PO 번호가 폴더명에 포함된 프로젝트 폴더를 찾아 DOCS_ROOT 기준 상대경로를 반환한다.
    최근 연도부터 훑어 최신 건을 빨리 찾는다. 없으면 None.

    max_years 를 주면 최근 N개 연도만 훑는다. 화면을 열 때마다 도는 자동 탐색은
    '못 찾는 경우'가 가장 느리므로(전 연도 전수 조사) 범위를 좁히고,
    사용자가 명시적으로 '다시 찾기'를 누를 때만 전체를 훑는다.
    """
    if not is_enabled() or not po_number:
        return None

    target = _normalize(po_number)
    # 'POXXXXXX' 처럼 실제 번호가 없는 값으로는 검색하지 않는다 (엉뚱한 폴더에 붙는다)
    if not target or "XXXX" in target:
        return None

    scanned = 0
    try:
        years = sorted(
            (d for d in DOCS_ROOT.iterdir() if d.is_dir() and not _is_hidden(d.name)),
            key=lambda d: d.name,
            reverse=True,
        )
    except OSError:
        logger.exception("문서 루트 조회 실패")
        return None

    if max_years:
        years = years[:max_years]

    for year in years:
        for dirpath, dirnames, _filenames in os.walk(year):
            depth = len(Path(dirpath).relative_to(DOCS_ROOT).parts)
            # 프로젝트 폴더보다 더 깊이 들어가지 않는다
            if depth >= _PROJECT_DEPTH:
                dirnames[:] = []
                continue
            for name in dirnames:
                scanned += 1
                if scanned > max_scan:
                    logger.warning("문서 폴더 검색 상한 도달 (po_number=%s)", po_number)
                    return None
                if target in _normalize(name):
                    return _to_relative(Path(dirpath) / name)
    return None


def list_folder(relative: str) -> list[dict]:
    """
    폴더 내용을 목록으로 반환한다 (폴더 먼저, 그다음 파일 — 각각 이름순).
    상대경로는 항상 DOCS_ROOT 기준이다.
    """
    target = safe_join(relative)
    if not target.is_dir():
        raise FileNotFoundError("폴더를 찾을 수 없습니다.")

    entries: list[dict] = []
    for entry in target.iterdir():
        if _is_hidden(entry.name):
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        is_dir = entry.is_dir()
        entries.append({
            "name": entry.name,
            "path": _to_relative(entry),
            "is_dir": is_dir,
            "size": 0 if is_dir else stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return entries


def read_file(relative: str) -> tuple[bytes, str]:
    """파일 내용과 이름을 반환한다."""
    target = safe_join(relative)
    if not target.is_file():
        raise FileNotFoundError("파일을 찾을 수 없습니다.")
    return target.read_bytes(), target.name
