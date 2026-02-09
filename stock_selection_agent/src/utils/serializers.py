"""
Dataclass 직렬화 유틸리티

dataclass 객체를 JSON 직렬화 가능한 dict로 변환
"""

from dataclasses import is_dataclass, fields
from datetime import datetime, date
from enum import Enum
from typing import Any, Optional


def dataclass_to_dict(obj: Any) -> Any:
    """
    Dataclass 객체를 dict로 변환 (중첩 구조 지원)

    Args:
        obj: 변환할 객체 (dataclass, list, dict, 기본 타입 등)

    Returns:
        JSON 직렬화 가능한 형태로 변환된 객체
    """
    if obj is None:
        return None

    # Dataclass인 경우
    if is_dataclass(obj) and not isinstance(obj, type):
        result = {}
        for field in fields(obj):
            value = getattr(obj, field.name)
            result[field.name] = dataclass_to_dict(value)
        return result

    # Dict인 경우
    if isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}

    # List/Tuple인 경우
    if isinstance(obj, (list, tuple)):
        return [dataclass_to_dict(item) for item in obj]

    # Enum인 경우
    if isinstance(obj, Enum):
        return obj.value

    # datetime/date인 경우
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()

    # 기본 타입 (int, float, str, bool)
    if isinstance(obj, (int, float, str, bool)):
        return obj

    # 그 외의 경우 문자열로 변환 시도
    try:
        return str(obj)
    except Exception:
        return None


def format_currency(value: Optional[int], unit: str = "원") -> str:
    """숫자를 통화 형식으로 포맷"""
    if value is None:
        return "N/A"
    return f"{value:,}{unit}"


def format_percentage(value: Optional[float], decimal: int = 1) -> str:
    """숫자를 백분율 형식으로 포맷"""
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimal}f}%"
