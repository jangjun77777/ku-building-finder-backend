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


def load_buildings(csv_path: str) -> List[Building]:
    """
    CSV 파일에서 건물 정보를 읽어서 Building 객체 리스트로 반환.
    CSV 컬럼 이름은 네가 준 것에 맞춰져 있음:
    Campus(KR), Campus(EN), Building name(KR),
    Naver map link, Abbreviations (Nicknames),
    Building Name(EN), Building Code
    """
    buildings: List[Building] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            buildings.append(
                Building(
                    campus_kr=row.get("Campus(KR)", "").strip(),
                    campus_en=row.get("Campus(EN)", "").strip(),
                    name_kr=row.get("Building name(KR)", "").strip(),
                    map_link=row.get("Naver map link", "").strip().strip('"'),
                    nickname=row.get("Abbreviations (Nicknames)", "").strip(),
                    name_en=row.get("Building Name(EN)", "").strip(),
                    code=str(row.get("Building Code", "")).strip(),
                )
            )
    return buildings


def normalize(s: str) -> str:
    return s.strip().lower()


def find_building_local(query: str, buildings: List[Building]) -> Optional[Building]:
    """
    유저가 입력한 query를 기준으로
    - Building Code(정확일치)
    - 별명/약어 (부분일치)
    - 영어 이름 (부분일치)
    - 한국어 이름 (부분일치)
    순서로 검색해서 가장 먼저 매칭되는 건물을 반환.
    """
    q = normalize(query)
    if not q:
        return None

    # 1) 코드(정확 일치)
    for b in buildings:
        if b.code and q == normalize(b.code):
            return b

    # 2) 별명 / 약어
    for b in buildings:
        if b.nickname and q in normalize(b.nickname):
            return b

    # 3) 영어 이름
    for b in buildings:
        if b.name_en and q in normalize(b.name_en):
            return b

    # 4) 한국어 이름
    for b in buildings:
        if b.name_kr and q in normalize(b.name_kr):
            return b

    return None
