# buildings.py
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


def get_col(row, *names):
    """여러 후보 컬럼명을 순서대로 탐색해서 가장 먼저 발견되는 값을 반환"""
    for n in names:
        if n in row and row[n]:
            return row[n].strip().replace('"', '')
    return ""


def load_buildings(csv_path: str) -> List[Building]:
    buildings: List[Building] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            buildings.append(
                Building(
                    campus_kr=get_col(row, "Campus(KR)", "캠퍼스(KR)"),
                    campus_en=get_col(row, "Campus(EN)", "캠퍼스(EN)"),
                    name_kr=get_col(row, "Building name(KR)", "Building Name(KR)", "건물명(KR)", "Building name (KR)"),
                    map_link=get_col(row, "Naver map link", "Map link", "지도링크", "Naver Map link"),
                    nickname=get_col(row, "Abbreviations (Nicknames)", "Nickname", "Nicknames", "별칭"),
                    name_en=get_col(row, "Building Name(EN)", "Building name(EN)", "Name(EN)", "영문명"),
                    code=get_col(row, "Building Code", "Code", "Building code"),
                )
            )
    return buildings


def normalize(s: str) -> str:
    return s.strip().lower()


def find_building_local(query: str, buildings: List[Building]) -> Optional[Building]:
    q = normalize(query)
    if not q:
        return None

    for b in buildings:
        if b.code and q == normalize(b.code):
            return b

    for b in buildings:
        if b.nickname and q in normalize(b.nickname):
            return b

    for b in buildings:
        if b.name_en and q in normalize(b.name_en):
            return b

    for b in buildings:
        if b.name_kr and q in normalize(b.name_kr):
            return b

    return None
