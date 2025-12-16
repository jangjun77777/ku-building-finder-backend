import csv
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Building:
    campus_kr: str
    campus_en: str
    name_kr: str
    map_link: str
    nickname: str
    name_en: str
    code: str


def safe_get(row: dict, *keys: str) -> str:
    """
    CSV 컬럼명이 조금씩 달라도 안전하게 값을 가져오기 위한 함수
    """
    for k in keys:
        if k in row and row[k]:
            return str(row[k]).strip()
    return ""


def load_buildings(csv_path: str) -> List[Building]:
    buildings: List[Building] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            buildings.append(
                Building(
                    campus_kr=safe_get(row, "캠퍼스", "Campus(KR)", "Campus KR"),
                    campus_en=safe_get(row, "Campus", "Campus(EN)", "Campus EN"),
                    name_kr=safe_get(row, "건물명", "Building name(KR)", "Building Name(KR)"),
                    name_en=safe_get(row, "Building Name", "Building Name(EN)", "Building Name EN"),
                    nickname=safe_get(row, "Abbreviations (Nicknames)", "Nickname", "Nicknames"),
                    map_link=safe_get(row, "Naver map link", "Naver Map Link").strip('"'),
                    code=safe_get(
                        row,
                        "건물코드 (Building Code)",
                        "건물코드\n (Building Code)",
                        "Building Code",
                        "Code",
                    ),
                )
            )

    return buildings


def normalize(s: str) -> str:
    return s.strip().lower()


def find_building_local(query: str, buildings: List[Building]) -> Optional[Building]:
    """
    검색 우선순위:
    1) Building Code (정확 일치)
    2) Nickname / Abbreviation (여러 개 대응)
    3) English Name (부분 일치)
    4) Korean Name (공백 무시 부분 일치)
    """
    q = normalize(query)
    if not q:
        return None

    # 1) 코드 (정확 일치)
    for b in buildings:
        if b.code and q == normalize(b.code):
            return b

    # 2) 별명 / 약어 (여러 개 처리)
    for b in buildings:
        if not b.nickname:
            continue
        nicknames = [n.strip() for n in b.nickname.split(",")]
        for n in nicknames:
            n_norm = normalize(n)
            if q == n_norm or q in n_norm:
                return b

    # 3) 영어 이름 (부분 일치)
    for b in buildings:
        if b.name_en and q in normalize(b.name_en):
            return b

    # 4) 한국어 이름 (공백 제거 후 비교)
    for b in buildings:
        if b.name_kr:
            if q.replace(" ", "") in normalize(b.name_kr).replace(" ", ""):
                return b

    return None
