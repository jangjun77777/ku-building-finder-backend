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
    for k in keys:
        if k in row and row[k]:
            return str(row[k]).strip()
    return ""


def normalize(s: str | None) -> str:
    return str(s or "").strip().lower()


def load_buildings(csv_path: str) -> List[Building]:
    buildings: List[Building] = []

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            buildings.append(
                Building(
                    campus_kr=safe_get(row, "캠퍼스", "Campus(KR)", "Campus KR"),
                    campus_en=safe_get(row, "Campus", "Campus(EN)", "Campus EN"),
                    name_kr=safe_get(row, "건물명", "Building name(KR)", "Building Name(KR)"),
                    map_link=safe_get(row, "Naver map link", "Naver Map Link").strip('"'),
                    nickname=safe_get(row, "Abbreviations (Nicknames)", "Nickname", "Nicknames"),
                    name_en=safe_get(row, "Building Name", "Building Name(EN)", "Building Name EN"),
                    code=safe_get(
                        row,
                         "건물코드 (Building Code)",
                         "건물코드(Building Code)",
                         "건물코드\n (Building Code)",
                         "Building Code",
                         "Code",
                    ),
                )
            )

    return buildings


def find_building_local(query: str, buildings: List[Building]) -> Optional[Building]:
    q = normalize(query)
    if not q:
        return None

    # 1. 건물 코드 정확 일치
    for b in buildings:
        if b.code and q == normalize(b.code):
            return b

    # 2. 닉네임 검색
    for b in buildings:
        if not b.nickname:
            continue

        nicknames = [n.strip() for n in b.nickname.split(",")]

        for n in nicknames:
            n_norm = normalize(n)
            if q == n_norm or q in n_norm:
                return b

    # 3. 영어명 검색
    for b in buildings:
        if b.name_en and q in normalize(b.name_en):
            return b

    # 4. 한국어명 검색
    q_no_space = q.replace(" ", "")

    for b in buildings:
        name_kr_no_space = normalize(b.name_kr).replace(" ", "")

        if b.name_kr and q_no_space in name_kr_no_space:
            return b

    return None
