from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("pypdf is required to generate linkage data") from exc


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
DATA_DIR = PUBLIC_DIR / "data"
TABLE_DIR = PUBLIC_DIR / "数据表合集" / "linkage"
SOURCE_ROOT = Path("D:/jingju")
PDF_PREFIXES = ["01004001", "01012004", "01040005", "02008006", "04008002"]

THEMES = [
    {
        "id": "theme_power",
        "name": "权谋斗争",
        "keywords": ["权", "谋", "朝", "帝", "王", "臣", "篡", "诏", "宫", "相", "奸", "政"],
    },
    {
        "id": "theme_loyalty",
        "name": "忠义家国",
        "keywords": ["忠", "义", "国", "汉", "宋", "君", "臣", "报国", "节", "护驾"],
    },
    {
        "id": "theme_war",
        "name": "战争征伐",
        "keywords": ["兵", "战", "杀", "军", "将", "营", "阵", "刀", "枪", "攻", "征"],
    },
    {
        "id": "theme_family",
        "name": "家庭伦理",
        "keywords": ["父", "母", "夫人", "小姐", "夫妻", "儿", "女", "家", "亲", "兄", "妹"],
    },
    {
        "id": "theme_love",
        "name": "婚恋情缘",
        "keywords": ["婚", "姻", "缘", "情", "爱", "小姐", "公子", "夫妻", "拜堂", "私订"],
    },
    {
        "id": "theme_chivalry",
        "name": "复仇侠义",
        "keywords": ["仇", "侠", "义", "救", "杀", "贼", "山寨", "英雄", "报仇", "冤"],
    },
    {
        "id": "theme_trial",
        "name": "公案审判",
        "keywords": ["案", "审", "告", "冤", "官", "县", "堂", "拿", "问", "判"],
    },
    {
        "id": "theme_fate",
        "name": "神怪因果",
        "keywords": ["仙", "神", "佛", "梦", "魂", "妖", "怪", "庙", "因果", "显灵"],
    },
    {
        "id": "theme_comedy",
        "name": "市井滑稽",
        "keywords": ["笑", "丑", "和尚", "胡闹", "酒", "店", "闹", "骗", "趣"],
    },
    {
        "id": "theme_women",
        "name": "女性命运",
        "keywords": ["女", "旦", "夫人", "小姐", "妃", "后", "莲", "凤", "妹", "妻"],
    },
]

TITLE_THEME_BOOSTS = {
    "逍遥津": {"theme_power": 60, "theme_loyalty": 36, "theme_war": 18, "theme_women": 12},
    "莲花湖": {"theme_chivalry": 60, "theme_loyalty": 20, "theme_trial": 16, "theme_comedy": 8},
    "万花船": {"theme_love": 60, "theme_women": 32, "theme_family": 18, "theme_fate": 12},
    "北汉王": {"theme_power": 60, "theme_loyalty": 32, "theme_women": 18, "theme_war": 14},
    "十三妹": {"theme_chivalry": 65, "theme_women": 32, "theme_love": 25, "theme_trial": 18},
}

TITLE_THEME_PRIORITY = {
    "逍遥津": ["theme_power", "theme_loyalty", "theme_war", "theme_women"],
    "莲花湖": ["theme_chivalry", "theme_trial", "theme_loyalty", "theme_comedy"],
    "万花船": ["theme_love", "theme_women", "theme_family", "theme_comedy"],
    "北汉王": ["theme_power", "theme_loyalty", "theme_war", "theme_women"],
    "十三妹": ["theme_chivalry", "theme_women", "theme_love", "theme_trial"],
}

TRADE_THEME_HINTS = {
    "小生": ["theme_love", "theme_loyalty", "theme_power"],
    "生": ["theme_loyalty", "theme_chivalry", "theme_power"],
    "老生": ["theme_loyalty", "theme_power", "theme_family"],
    "娃娃生": ["theme_family", "theme_loyalty"],
    "旦": ["theme_women", "theme_love", "theme_family"],
    "花旦": ["theme_love", "theme_women", "theme_comedy"],
    "二旦": ["theme_women", "theme_family"],
    "老旦": ["theme_family", "theme_women"],
    "彩旦": ["theme_comedy", "theme_women"],
    "净": ["theme_power", "theme_war", "theme_chivalry"],
    "丑": ["theme_comedy", "theme_trial", "theme_chivalry"],
    "付": ["theme_comedy", "theme_trial"],
}

RELATION_LABELS = {
    "alliance": "同场协作",
    "command": "差遣统属",
    "conflict": "冲突对峙",
    "info": "传信谋划",
    "kinship": "亲缘牵连",
    "romance": "情缘牵连",
    "power": "权力牵制",
    "support": "扶助照应",
}

RELATION_TYPE_OVERRIDES: dict[str, dict[frozenset[str], str]] = {
    "逍遥津": {
        frozenset(("华歆", "曹操")): "power",
        frozenset(("司马懿", "曹操")): "power",
        frozenset(("曹操", "汉献帝")): "power",
        frozenset(("张辽", "汉献帝")): "support",
    },
    "莲花湖": {
        frozenset(("秦尤", "咎士雄")): "alliance",
        frozenset(("咎士雄", "崔通")): "alliance",
        frozenset(("杨香武", "胜英")): "command",
        frozenset(("胜英", "黄三泰")): "command",
        frozenset(("李刚", "杨香武")): "alliance",
        frozenset(("武万年", "黄三泰")): "alliance",
        frozenset(("李志龙", "武万年")): "alliance",
        frozenset(("杨俊", "黄三泰")): "alliance",
        frozenset(("杨俊", "武万年")): "alliance",
        frozenset(("和尚", "韩秀")): "info",
        frozenset(("韩秀", "高大鹏")): "command",
        frozenset(("韩秀", "韩韬英")): "kinship",
        frozenset(("小桃", "韩秀")): "support",
        frozenset(("胡闹", "荀攸")): "alliance",
    },
    "万花船": {
        frozenset(("张夫人", "张济")): "kinship",
        frozenset(("张小莲", "张济")): "kinship",
        frozenset(("甘习文", "甘氏")): "kinship",
        frozenset(("张小莲", "甘习文")): "romance",
        frozenset(("张小莲", "蔡炳")): "conflict",
        frozenset(("甘习文", "观音")): "support",
        frozenset(("店家", "观音")): "support",
    },
    "北汉王": {
        frozenset(("刘承佑", "苏逢吉")): "power",
        frozenset(("刘承佑", "王章")): "command",
        frozenset(("刘承佑", "孟业")): "command",
        frozenset(("史彦超", "郭彦威")): "alliance",
        frozenset(("史彦超", "韩通")): "alliance",
        frozenset(("王朴", "韩通")): "alliance",
        frozenset(("柴荣", "王朴")): "command",
        frozenset(("柴荣", "韩通")): "command",
        frozenset(("史彦超", "柴荣")): "alliance",
        frozenset(("刘承佑", "苏妃")): "kinship",
        frozenset(("苏夫人", "苏妃")): "kinship",
        frozenset(("刘承佑", "高庆")): "command",
        frozenset(("王福", "高庆")): "alliance",
        frozenset(("王福", "赵普")): "info",
    },
    "十三妹": {
        frozenset(("白脸狼", "黄傻狗")): "alliance",
        frozenset(("张妈妈", "张金凤")): "kinship",
        frozenset(("张金凤", "赛西施")): "support",
        frozenset(("华忠", "黄傻狗")): "command",
        frozenset(("何玉凤", "安骥")): "support",
        frozenset(("何玉凤", "张乐世")): "support",
        frozenset(("何玉凤", "张金凤")): "support",
    },
}

STAGE_TYPES = ["开端", "发展", "转折", "高潮", "结局"]
ROLE_LEVEL_LABELS = {
    "core": "核心人物",
    "major": "主要人物",
    "minor": "次要人物",
}
GRAPH_MIN_RELATIONS = 8
GRAPH_MAX_RELATIONS = 18


@dataclass
class Role:
    name: str
    trade: str
    order: int


SUPPLEMENTAL_ROLES_BY_TITLE: dict[str, list[tuple[str, str]]] = {
    "莲花湖": [
        ("黄三泰", "武生"),
        ("杨香武", "武生"),
        ("武万年", "武生"),
        ("崔通", "武生"),
        ("秦尤", "武生"),
        ("咎士雄", "武生"),
        ("李刚", "武生"),
        ("李志龙", "武生"),
        ("杨俊", "武生"),
        ("韩韬英", "武旦"),
        ("小桃", "花旦"),
        ("高大鹏", "净"),
        ("李豹", "武生"),
    ],
    "万花船": [
        ("观音", "旦"),
        ("甘氏", "老旦"),
        ("店家", "丑"),
    ],
    "北汉王": [
        ("郭彦威", "老生"),
        ("王朴", "末"),
        ("史彦超", "武生"),
        ("柴荣", "小生"),
        ("韩通", "净"),
        ("孟业", "末"),
        ("杨邠", "老生"),
        ("王章", "末"),
        ("苏夫人", "老旦"),
        ("慕容彦超", "净"),
        ("高庆", "丑"),
        ("王福", "丑"),
        ("张端", "末"),
        ("赵普", "老生"),
    ],
}


def stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def find_pdfs() -> list[Path]:
    if not SOURCE_ROOT.exists():
        raise SystemExit(f"Source directory not found: {SOURCE_ROOT}")
    candidates = list(SOURCE_ROOT.rglob("*.pdf"))
    results: list[Path] = []
    for prefix in PDF_PREFIXES:
        match = next((path for path in candidates if path.name.startswith(prefix)), None)
        if match is None:
            raise SystemExit(f"PDF with prefix {prefix} was not found under {SOURCE_ROOT}")
        results.append(match)
    return results


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return normalize_text("\n".join(pages))


def parse_title(text: str, fallback: str) -> str:
    match = re.search(r"《([^》]+)》", text)
    return match.group(1).strip() if match else fallback


def parse_roles(text: str) -> list[Role]:
    role_block_match = re.search(r"主要角色\s*(.*?)(?:情节|注释|【第一场】)", text, flags=re.S)
    if role_block_match:
        block = role_block_match.group(1)
    else:
        block = "\n".join(text.splitlines()[:80])

    roles: list[Role] = []
    seen: set[str] = set()
    pattern = re.compile(r"^([^：:\n]{1,12})[：:]\s*([^\n，。；;、\s]{1,8})", flags=re.M)
    for match in pattern.finditer(block):
        name = clean_name(match.group(1))
        trade = normalize_trade(match.group(2))
        if not name or name in seen or is_metadata_name(name):
            continue
        if trade not in TRADE_THEME_HINTS and not any(key in trade for key in ["生", "旦", "净", "丑", "付"]):
            continue
        seen.add(name)
        roles.append(Role(name=name, trade=trade, order=len(roles) + 1))
    return roles


def augment_roles(title: str, roles: list[Role], text: str) -> list[Role]:
    supplemented = list(roles)
    seen = {role.name for role in supplemented}
    for name, trade in SUPPLEMENTAL_ROLES_BY_TITLE.get(title, []):
        if name in seen or name not in text:
            continue
        supplemented.append(Role(name=name, trade=normalize_trade(trade), order=len(supplemented) + 1))
        seen.add(name)
    return supplemented


def clean_name(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^[·\s\d]+", "", value)
    value = re.sub(r"[（(].*?[）)]", "", value)
    return value.strip()


def is_metadata_name(name: str) -> bool:
    return name in {"主要角色", "情节", "注释", "根据"} or "整理" in name or "录入" in name


def normalize_trade(trade: str) -> str:
    trade = clean_name(trade)
    aliases = {
        "付": "丑",
        "副": "丑",
        "贴旦": "旦",
        "武旦": "旦",
    }
    return aliases.get(trade, trade)


STANDARD_TRADES = ["老生", "丑", "武生", "小生", "净", "旦", "外", "正旦", "末", "武将", "老旦", "花旦", "青衣"]


def standard_trade(trade: str) -> str:
    value = clean_name(trade)
    if not value:
        return ""
    if value in STANDARD_TRADES:
        return value
    aliases = {
        "生": "老生",
        "娃娃生": "小生",
        "武旦": "旦",
        "贴旦": "旦",
        "二旦": "旦",
        "彩旦": "花旦",
        "花衫": "花旦",
        "付": "丑",
        "副": "丑",
    }
    if value in aliases:
        return aliases[value]
    contains = [
        ("老生", "老生"),
        ("小生", "小生"),
        ("武生", "武生"),
        ("老旦", "老旦"),
        ("花旦", "花旦"),
        ("青衣", "青衣"),
        ("正旦", "正旦"),
        ("旦", "旦"),
        ("净", "净"),
        ("丑", "丑"),
        ("末", "末"),
        ("外", "外"),
    ]
    for keyword, mapped in contains:
        if keyword in value:
            return mapped
    return value


def major_trade(trade: str) -> str:
    trade = standard_trade(trade) or trade
    if "旦" in trade or trade == "青衣":
        return "旦"
    if "净" in trade:
        return "净"
    if "丑" in trade or trade == "付":
        return "丑"
    if "生" in trade:
        return "生"
    return trade


def split_scenes(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(r"【第([一二三四五六七八九十百零〇\d]+)场】")
    matches = list(pattern.finditer(text))
    if not matches:
        return [{"scene_no": 1, "scene_label": "第一场", "text": text}]

    scenes: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        scene_no = chinese_number_to_int(match.group(1)) or index + 1
        scene_text = normalize_text(text[start:end])
        scenes.append(
            {
                "scene_no": scene_no,
                "scene_label": f"第{match.group(1)}场",
                "text": scene_text,
            }
        )
    return scenes


def chinese_number_to_int(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if value == "十":
        return 10
    if "十" in value:
        left, _, right = value.partition("十")
        tens = digits.get(left, 1) if left else 1
        ones = digits.get(right, 0) if right else 0
        return tens * 10 + ones
    return digits.get(value)


def count_speaker_lines(scene_text: str, roles: list[Role]) -> Counter[str]:
    counts: Counter[str] = Counter()
    role_names = sorted((role.name for role in roles), key=len, reverse=True)
    for raw_line in scene_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for name in role_names:
            if line.startswith(name) and len(line) > len(name):
                counts[name] += 1
                break
    return counts


def scene_activity(scene_text: str, roles: list[Role]) -> dict[str, dict[str, int]]:
    speaker_counts = count_speaker_lines(scene_text, roles)
    activity: dict[str, dict[str, int]] = {}
    for role in roles:
        mentions = len(re.findall(re.escape(role.name), scene_text))
        speeches = speaker_counts[role.name]
        if mentions or speeches:
            activity[role.name] = {
                "mentions": mentions,
                "speeches": speeches,
                "text_length": speeches * 30 + mentions * 8,
            }
    return activity


def estimate_conflict(scene_text: str) -> float:
    keywords = ["杀", "战", "打", "怒", "拿", "仇", "斩", "逼", "哭", "骂", "奸", "逃", "争"]
    score = sum(scene_text.count(word) for word in keywords)
    return min(1.0, score / 18)


def estimate_emotion(scene_text: str) -> float:
    keywords = ["哭", "悲", "喜", "怒", "恨", "爱", "情", "叹", "笑", "怕", "惊"]
    score = sum(scene_text.count(word) for word in keywords)
    return min(1.0, score / 14)


def classify_conflict_type(scene_text: str) -> str:
    if any(word in scene_text for word in ["兵", "战", "军", "杀", "阵"]):
        return "军事冲突"
    if any(word in scene_text for word in ["帝", "王", "臣", "诏", "宫", "相"]):
        return "权力冲突"
    if any(word in scene_text for word in ["仇", "冤", "救", "盗", "寨"]):
        return "侠义冲突"
    if any(word in scene_text for word in ["父", "母", "夫妻", "小姐", "夫人"]):
        return "伦理冲突"
    return "情节推进"


def summarize_scene(scene_text: str, active_names: list[str]) -> str:
    cleaned = re.sub(r"[（(].*?[）)]", "", scene_text)
    cleaned = re.sub(r"\s+", "", cleaned)
    first_sentence = re.split(r"[。！？；]", cleaned)[0][:42]
    if first_sentence:
        return first_sentence
    if active_names:
        return "、".join(active_names[:4]) + "同场推动情节"
    return "场次承接剧情发展"


def infer_relation_type(source: Role, target: Role, title: str, scene_text: str) -> str:
    pair_text = source.name + target.name
    combined = pair_text + scene_text[:320]
    override = RELATION_TYPE_OVERRIDES.get(title, {}).get(frozenset((source.name, target.name)))
    if override:
        return override
    if "观音" in pair_text:
        return "support"
    if any(word in combined for word in ["杀", "战", "仇", "拿", "打", "骂", "奸"]):
        return "conflict"
    if any(word in combined for word in ["传", "报", "信", "书", "计", "谋", "献", "说", "告", "探"]):
        return "info"
    if any(word in combined for word in ["命", "令", "差", "遣", "派", "军", "将", "统", "率", "诏"]):
        return "command"
    if any(word in combined for word in ["助", "救", "护", "随", "侍", "扶", "保", "接应", "托付"]):
        return "support"
    if any(word in combined for word in ["父子", "母子", "父女", "母女", "兄弟", "姐妹", "夫人", "父", "母", "兄", "妹"]):
        return "kinship"
    if any(word in combined for word in ["夫妻", "夫", "妻", "小姐", "公子", "情", "婚", "姻"]):
        if major_trade(source.trade) != major_trade(target.trade):
            return "romance"
    if any(word in combined for word in ["帝", "王", "臣", "相", "宫", "朝"]) or title in {"逍遥津", "北汉王"}:
        return "power"
    return "alliance"


def build_theme_scores(title: str, text: str, roles: list[Role]) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    evidence: dict[str, str] = {}
    role_text = "".join(role.name + role.trade for role in roles)
    for theme in THEMES:
        count = sum(text.count(keyword) for keyword in theme["keywords"])
        role_count = sum(role_text.count(keyword) for keyword in theme["keywords"])
        score = count + role_count * 1.5
        score += TITLE_THEME_BOOSTS.get(title, {}).get(theme["id"], 0)
        scores[theme["id"]] = score
        evidence_word = next((keyword for keyword in theme["keywords"] if keyword in text or keyword in role_text), "")
        evidence[theme["id"]] = evidence_word

    theme_by_id = {theme["id"]: theme for theme in THEMES}
    priority_ids = TITLE_THEME_PRIORITY.get(title, [])
    if priority_ids:
        priority = [theme_by_id[theme_id] for theme_id in priority_ids if theme_id in theme_by_id]
        remaining = [theme for theme in THEMES if theme["id"] not in priority_ids]
        ranked = priority + sorted(remaining, key=lambda item: scores[item["id"]], reverse=True)
    else:
        ranked = sorted(THEMES, key=lambda item: scores[item["id"]], reverse=True)
    top_score_sum = sum(max(scores[item["id"]], 1) for item in ranked[:4]) or 1
    rows = []
    for rank, theme in enumerate(ranked[:4], start=1):
        score = max(scores[theme["id"]], 1)
        rows.append(
            {
                "theme_id": theme["id"],
                "theme": theme["name"],
                "score": round(score, 2),
                "share": round(score / top_score_sum, 4),
                "rank": rank,
                "evidence": evidence[theme["id"]] or "题材倾向",
            }
        )
    return rows


def character_theme_ids(trade: str, play_themes: list[dict[str, Any]]) -> list[str]:
    theme_ids = [theme["theme_id"] for theme in play_themes]
    standard = standard_trade(trade)
    hints = TRADE_THEME_HINTS.get(standard, TRADE_THEME_HINTS.get(trade, TRADE_THEME_HINTS.get(major_trade(standard or trade), [])))
    linked = [theme_id for theme_id in hints if theme_id in theme_ids]
    if linked:
        return linked[:2]
    return theme_ids[:1]


def score_role_for_level(character: dict[str, Any]) -> tuple[float, int, int, int]:
    return (
        float(character.get("importance", 0)),
        int(character.get("scene_count", 0)),
        int(character.get("speech_count", 0)),
        -int(character.get("role_order", 999)),
    )


def assign_role_levels(characters: list[dict[str, Any]]) -> None:
    ordered = sorted(characters, key=score_role_for_level, reverse=True)
    count = len(ordered)
    if not count:
        return

    core_count = 1 if count <= 5 else 2 if count <= 18 else 3
    major_count = min(max(2, math.ceil(count * 0.26)), max(0, count - core_count))

    for index, character in enumerate(ordered):
        if index < core_count:
            level = "core"
        elif index < core_count + major_count:
            level = "major"
        else:
            level = "minor"

        character["role_level"] = level
        character["role_level_label"] = ROLE_LEVEL_LABELS[level]
        character["network_rank"] = index + 1


def relation_character_ids(relation: dict[str, Any]) -> tuple[str, str]:
    return relation["source_character_id"], relation["target_character_id"]


def relation_score(relation: dict[str, Any], character_by_id: dict[str, dict[str, Any]]) -> float:
    source_id, target_id = relation_character_ids(relation)
    source = character_by_id.get(source_id, {})
    target = character_by_id.get(target_id, {})
    level_rank = {"core": 3, "major": 2, "minor": 1}
    source_rank = level_rank.get(source.get("role_level"), 1)
    target_rank = level_rank.get(target.get("role_level"), 1)
    importance = float(source.get("importance", 0)) + float(target.get("importance", 0))
    type_bonus = 0.8 if relation.get("relation_type") in {"power", "conflict", "romance", "kinship"} else 0.3
    return float(relation.get("weight", 0)) + (source_rank + target_rank) * 1.35 + importance * 3 + type_bonus


def relation_cap(character: dict[str, Any], character_count: int) -> int:
    level = character.get("role_level")
    if level == "core":
        return 7 if character_count >= 14 else 5
    if level == "major":
        return 3
    return 1


def target_relation_count(character_count: int, relation_count: int) -> int:
    if character_count <= 1:
        return 0
    if relation_count <= character_count:
        return relation_count
    target = character_count if character_count <= 10 else character_count + 1
    return min(relation_count, GRAPH_MAX_RELATIONS, target)


def graph_components(character_ids: set[str], selected: list[dict[str, Any]]) -> list[set[str]]:
    adjacency: dict[str, set[str]] = {character_id: set() for character_id in character_ids}
    for relation in selected:
        source_id, target_id = relation_character_ids(relation)
        if source_id in adjacency and target_id in adjacency:
            adjacency[source_id].add(target_id)
            adjacency[target_id].add(source_id)

    components: list[set[str]] = []
    visited: set[str] = set()
    for character_id in character_ids:
        if character_id in visited:
            continue
        stack = [character_id]
        visited.add(character_id)
        component: set[str] = set()
        while stack:
            current = stack.pop()
            component.add(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    return components


def compress_relation_weights(relations: list[dict[str, Any]]) -> None:
    if not relations:
        return
    max_weight = max(float(relation.get("weight", 0)) for relation in relations) or 1
    for rank, relation in enumerate(sorted(relations, key=lambda row: float(row.get("weight", 0)), reverse=True), start=1):
        relation["weight"] = round(1.2 + 5.2 * (float(relation.get("weight", 0)) / max_weight), 2)
        relation["relation_rank"] = rank


def scene_no_from_scene_id(scene_id: str) -> int:
    match = re.search(r"_scene_(\d+)$", scene_id)
    return int(match.group(1)) if match else 1


def best_character_in_component(component: set[str], character_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return max((character_by_id[character_id] for character_id in component), key=score_role_for_level)


def make_structural_relation(source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    play_id = source["play_id"]
    scene_ids = sorted({source.get("primary_scene_id", ""), target.get("primary_scene_id", "")} - {""})
    first_scene_no = min((scene_no_from_scene_id(scene_id) for scene_id in scene_ids), default=1)
    last_scene_no = max((scene_no_from_scene_id(scene_id) for scene_id in scene_ids), default=first_scene_no)
    weight = 1.4 + (float(source.get("importance", 0)) + float(target.get("importance", 0))) * 2.2

    return {
        "relation_id": stable_id("rel", play_id, source["name"], target["name"], "structural"),
        "play_id": play_id,
        "source_character_id": source["character_id"],
        "target_character_id": target["character_id"],
        "source": source["name"],
        "target": target["name"],
        "source_trade": source["trade"],
        "target_trade": target["trade"],
        "source_raw_trade": source.get("raw_trade", ""),
        "target_raw_trade": target.get("raw_trade", ""),
        "source_standard_trade": source["standard_trade"],
        "target_standard_trade": target["standard_trade"],
        "relation_type": "support",
        "relation_label": RELATION_LABELS["support"],
        "relation_desc": f"{source['name']}与{target['name']}作为《{play_id}》人物网络的结构桥接，形成扶助照应关系",
        "weight": round(weight, 2),
        "scene_ids": scene_ids,
        "first_scene_no": first_scene_no,
        "last_scene_no": last_scene_no,
        "evidence": "根据人物重要度与网络连通性补充结构关系",
    }


def optimize_relation_rows(relation_rows: list[dict[str, Any]], characters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not relation_rows:
        return []

    character_by_id = {character["character_id"]: character for character in characters}
    ordered_characters = sorted(characters, key=score_role_for_level, reverse=True)
    candidate_rows = [
        relation
        for relation in relation_rows
        if relation["source_character_id"] in character_by_id and relation["target_character_id"] in character_by_id
    ]
    if not ordered_characters:
        return []

    target_count = target_relation_count(len(characters), len(candidate_rows))
    sorted_candidates = sorted(candidate_rows, key=lambda relation: relation_score(relation, character_by_id), reverse=True)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    degrees: Counter[str] = Counter()

    def add_relation(relation: dict[str, Any], *, allow_over_cap: bool = False) -> bool:
        relation_id = relation["relation_id"]
        if relation_id in selected_ids:
            return False
        source_id, target_id = relation_character_ids(relation)
        if not allow_over_cap:
            if degrees[source_id] >= relation_cap(character_by_id[source_id], len(characters)):
                return False
            if degrees[target_id] >= relation_cap(character_by_id[target_id], len(characters)):
                return False
        selected.append(relation)
        selected_ids.add(relation_id)
        degrees[source_id] += 1
        degrees[target_id] += 1
        return True

    def relation_backbone_score(relation: dict[str, Any], character_id: str, connected_ids: set[str]) -> float:
        source_id, target_id = relation_character_ids(relation)
        other_id = target_id if source_id == character_id else source_id
        other = character_by_id.get(other_id, {})
        own = character_by_id.get(character_id, {})
        other_cap = relation_cap(other, len(characters))
        own_cap = relation_cap(own, len(characters))
        over_cap_penalty = 10 if degrees[other_id] >= other_cap or degrees[character_id] >= own_cap else 0
        connected_bonus = 2 if other_id in connected_ids else 0
        return relation_score(relation, character_by_id) + connected_bonus - degrees[other_id] * 3.2 - over_cap_penalty

    def candidate_relations_for(character_id: str, connected_ids: set[str]) -> list[dict[str, Any]]:
        incident_to_connected = [
            relation
            for relation in sorted_candidates
            if relation["relation_id"] not in selected_ids
            and character_id in relation_character_ids(relation)
            and (not connected_ids or any(endpoint in connected_ids for endpoint in relation_character_ids(relation) if endpoint != character_id))
        ]
        if incident_to_connected:
            return sorted(
                incident_to_connected,
                key=lambda relation: relation_backbone_score(relation, character_id, connected_ids),
                reverse=True,
            )

        incident = [
            relation
            for relation in sorted_candidates
            if relation["relation_id"] not in selected_ids and character_id in relation_character_ids(relation)
        ]
        return sorted(incident, key=lambda relation: relation_backbone_score(relation, character_id, connected_ids), reverse=True)

    connected_ids: set[str] = {ordered_characters[0]["character_id"]}
    for character in ordered_characters[1:]:
        character_id = character["character_id"]
        relation = None
        candidates = candidate_relations_for(character_id, connected_ids)
        for candidate in candidates:
            if add_relation(candidate):
                relation = candidate
                break
        if relation is None and candidates:
            relation = candidates[0]
            add_relation(relation, allow_over_cap=True)
        if relation is None:
            anchor = best_character_in_component(connected_ids, character_by_id)
            relation = make_structural_relation(anchor, character)
            sorted_candidates.append(relation)
            candidate_rows.append(relation)
            add_relation(relation, allow_over_cap=True)
        connected_ids.update(relation_character_ids(relation))

    priority_levels = {"core", "major"}
    for relation in sorted_candidates:
        if len(selected) >= target_count:
            break
        source = character_by_id[relation["source_character_id"]]
        target = character_by_id[relation["target_character_id"]]
        if source["role_level"] not in priority_levels and target["role_level"] not in priority_levels:
            continue
        if source["role_level"] == "minor" and degrees[source["character_id"]] >= 1:
            continue
        if target["role_level"] == "minor" and degrees[target["character_id"]] >= 1:
            continue
        add_relation(relation)

    graph_ids = {
        character["character_id"]
        for character in characters
    }
    while True:
        components = graph_components(graph_ids, selected)
        if len(components) <= 1:
            break
        component_index = {character_id: index for index, component in enumerate(components) for character_id in component}
        bridge = next(
            (
                relation
                for relation in sorted_candidates
                if component_index.get(relation["source_character_id"]) != component_index.get(relation["target_character_id"])
                and relation["relation_id"] not in selected_ids
            ),
            None,
        )
        if not bridge:
            main_component = max(components, key=len)
            other_component = max((component for component in components if component is not main_component), key=len)
            source = best_character_in_component(main_component, character_by_id)
            target = best_character_in_component(other_component, character_by_id)
            bridge = make_structural_relation(source, target)
            sorted_candidates.append(bridge)
            candidate_rows.append(bridge)
        add_relation(bridge, allow_over_cap=True)
        if len(selected) >= max(target_count, len(characters) - 1) + 3:
            break

    for relation in selected:
        source = character_by_id[relation["source_character_id"]]
        target = character_by_id[relation["target_character_id"]]
        relation["source_level"] = source["role_level"]
        relation["target_level"] = target["role_level"]
        relation["source_level_label"] = source["role_level_label"]
        relation["target_level_label"] = target["role_level_label"]

    compress_relation_weights(selected)
    return sorted(selected, key=lambda row: (row["first_scene_no"], row["relation_rank"], row["source"], row["target"]))


def curve_from_values(values: list[float]) -> list[float]:
    if not values:
        return []
    maximum = max(values) or 1
    return [round(value / maximum, 4) for value in values]


def top_stage_type(index: int, count: int, peak_index: int) -> str:
    if count <= 1:
        return "开端"
    if index == 0:
        return "开端"
    if index == count - 1:
        return "结局"
    if index == peak_index:
        return "高潮"
    if index < peak_index:
        return "发展"
    return "转折"


def narrative_type_from_themes(theme_ids: list[str]) -> tuple[str, str]:
    if "theme_power" in theme_ids:
        return "power-loop", "权力博弈型"
    if "theme_chivalry" in theme_ids:
        return "chivalry-loop", "侠义伸张型"
    if "theme_love" in theme_ids:
        return "romance-loop", "情缘流转型"
    return "family-loop", "伦理承转型"


def evolution_type_from_curve(curve: list[float]) -> tuple[str, str]:
    if not curve:
        return "steady", "平稳推进"
    peak = max(range(len(curve)), key=curve.__getitem__)
    if peak >= len(curve) * 0.65:
        return "late-peak", "后段爆发"
    if peak <= len(curve) * 0.35:
        return "early-peak", "前段激化"
    return "mid-peak", "中段转折"


def generate_play(path: Path) -> dict[str, Any]:
    text = read_pdf(path)
    title = parse_title(text, path.stem.split("_", 1)[-1])
    play_id = path.stem.split("_", 1)[0]
    roles = augment_roles(title, parse_roles(text), text)
    if not roles:
        raise SystemExit(f"No roles parsed from {path}")

    play_themes = build_theme_scores(title, text, roles)
    scenes_raw = split_scenes(text)
    role_by_name = {role.name: role for role in roles}

    character_stats = {
        role.name: {
            "scene_count": 0,
            "speech_count": 0,
            "mention_count": 0,
            "text_length": 0,
            "scene_ids": [],
            "primary_scene_id": "",
        }
        for role in roles
    }

    scene_rows: list[dict[str, Any]] = []
    relation_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    conflict_values: list[float] = []

    for scene_index, raw_scene in enumerate(scenes_raw):
        scene_id = f"{play_id}_scene_{scene_index + 1:02d}"
        activity = scene_activity(raw_scene["text"], roles)
        active_names = sorted(
            activity,
            key=lambda name: (activity[name]["speeches"], activity[name]["mentions"], -role_by_name[name].order),
            reverse=True,
        )
        active_character_ids = [stable_id("char", play_id, name) for name in active_names]

        for name, stat in activity.items():
            character_stats[name]["scene_count"] += 1
            character_stats[name]["speech_count"] += stat["speeches"]
            character_stats[name]["mention_count"] += stat["mentions"]
            character_stats[name]["text_length"] += stat["text_length"]
            character_stats[name]["scene_ids"].append(scene_id)

        conflict = estimate_conflict(raw_scene["text"])
        emotion = estimate_emotion(raw_scene["text"])
        relation_strength = min(1.0, len(active_names) / max(len(roles), 1) + conflict * 0.35)
        density = min(1.0, len(active_names) / max(len(roles), 1))
        plot_strength = min(1.0, 0.25 + density * 0.35 + conflict * 0.25 + emotion * 0.15)
        conflict_values.append(conflict + relation_strength + plot_strength)

        scene_rows.append(
            {
                "scene_id": scene_id,
                "play_id": play_id,
                "scene_no": raw_scene["scene_no"],
                "scene_label": raw_scene["scene_label"],
                "summary": summarize_scene(raw_scene["text"], active_names),
                "character_ids": active_character_ids,
                "character_names": active_names,
                "relation_ids": [],
                "metrics": {
                    "performance_density": round(density, 4),
                    "role_activity": round(min(1.0, sum(item["speeches"] + item["mentions"] for item in activity.values()) / 80), 4),
                    "conflict_strength": round(conflict, 4),
                    "relation_change_strength": round(relation_strength, 4),
                    "emotion_strength": round(emotion, 4),
                    "plot_strength": round(plot_strength, 4),
                },
                "conflict_type": classify_conflict_type(raw_scene["text"]),
                "raw_text_excerpt": raw_scene["text"][:220],
            }
        )

        for i, source_name in enumerate(active_names):
            for target_name in active_names[i + 1 :]:
                source_role = role_by_name[source_name]
                target_role = role_by_name[target_name]
                names = tuple(sorted([source_name, target_name]))
                key = names
                relation_type = infer_relation_type(source_role, target_role, title, raw_scene["text"])
                if key not in relation_pairs:
                    relation_pairs[key] = {
                        "source_name": names[0],
                        "target_name": names[1],
                        "relation_types": Counter(),
                        "weight": 0,
                        "scene_ids": [],
                        "first_scene_no": raw_scene["scene_no"],
                        "last_scene_no": raw_scene["scene_no"],
                        "evidence": summarize_scene(raw_scene["text"], list(names))[:60],
                    }
                relation_pairs[key]["relation_types"][relation_type] += 1
                relation_pairs[key]["weight"] += 1 + conflict
                relation_pairs[key]["scene_ids"].append(scene_id)
                relation_pairs[key]["last_scene_no"] = raw_scene["scene_no"]

    peak_index = max(range(len(conflict_values)), key=conflict_values.__getitem__) if conflict_values else 0
    relation_rows: list[dict[str, Any]] = []
    for pair, relation in relation_pairs.items():
        source = role_by_name[relation["source_name"]]
        target = role_by_name[relation["target_name"]]
        source_standard = standard_trade(source.trade)
        target_standard = standard_trade(target.trade)
        relation_type = relation["relation_types"].most_common(1)[0][0]
        relation_id = stable_id("rel", play_id, relation["source_name"], relation["target_name"])
        relation_rows.append(
            {
                "relation_id": relation_id,
                "play_id": play_id,
                "source_character_id": stable_id("char", play_id, relation["source_name"]),
                "target_character_id": stable_id("char", play_id, relation["target_name"]),
                "source": relation["source_name"],
                "target": relation["target_name"],
                "source_trade": source_standard,
                "target_trade": target_standard,
                "source_raw_trade": "" if source.trade == source_standard else source.trade,
                "target_raw_trade": "" if target.trade == target_standard else target.trade,
                "source_standard_trade": source_standard,
                "target_standard_trade": target_standard,
                "relation_type": relation_type,
                "relation_label": RELATION_LABELS.get(relation_type, "同场关系"),
                "relation_desc": f"{relation['source_name']}与{relation['target_name']}在{len(set(relation['scene_ids']))}场中形成{RELATION_LABELS.get(relation_type, '同场关系')}",
                "weight": round(relation["weight"], 2),
                "scene_ids": sorted(set(relation["scene_ids"])),
                "first_scene_no": relation["first_scene_no"],
                "last_scene_no": relation["last_scene_no"],
                "evidence": relation["evidence"],
            }
        )

    for index, scene in enumerate(scene_rows):
        scene["stage_type"] = top_stage_type(index, len(scene_rows), peak_index)

    for role in roles:
        stats = character_stats[role.name]
        if stats["scene_ids"]:
            scene_counter = Counter(stats["scene_ids"])
            stats["primary_scene_id"] = scene_counter.most_common(1)[0][0]

    max_importance = max(
        (
            character_stats[role.name]["speech_count"] * 2
            + character_stats[role.name]["mention_count"]
            + character_stats[role.name]["scene_count"] * 3
            for role in roles
        ),
        default=1,
    )

    characters: list[dict[str, Any]] = []
    for role in roles:
        stats = character_stats[role.name]
        normalized_trade = standard_trade(role.trade)
        importance_raw = (
            stats["speech_count"] * 2
            + stats["mention_count"]
            + stats["scene_count"] * 3
            + max(0, 8 - role.order)
        )
        linked_theme_ids = character_theme_ids(role.trade, play_themes)
        characters.append(
            {
                "character_id": stable_id("char", play_id, role.name),
                "play_id": play_id,
                "name": role.name,
                "trade": normalized_trade,
                "raw_trade": "" if role.trade == normalized_trade else role.trade,
                "standard_trade": normalized_trade,
                "major_trade": major_trade(normalized_trade),
                "role_order": role.order,
                "scene_count": stats["scene_count"],
                "speech_count": stats["speech_count"],
                "mention_count": stats["mention_count"],
                "text_length": stats["text_length"],
                "importance": round(min(1.0, importance_raw / max_importance), 4),
                "scene_ids": stats["scene_ids"],
                "primary_scene_id": stats["primary_scene_id"],
                "linked_theme_ids": linked_theme_ids,
                "linked_themes": [theme["theme"] for theme in play_themes if theme["theme_id"] in linked_theme_ids],
            }
        )

    assign_role_levels(characters)
    relation_rows = optimize_relation_rows(relation_rows, characters)

    relation_by_scene: dict[str, list[str]] = defaultdict(list)
    for relation in relation_rows:
        for scene_id in relation["scene_ids"]:
            relation_by_scene[scene_id].append(relation["relation_id"])

    for scene in scene_rows:
        scene["relation_ids"] = relation_by_scene.get(scene["scene_id"], [])

    curve_values = [
        scene["metrics"]["plot_strength"] + scene["metrics"]["conflict_strength"] + scene["metrics"]["relation_change_strength"]
        for scene in scene_rows
    ]
    narrative_curve = curve_from_values(curve_values)
    evolution_curve = curve_from_values(
        [scene["metrics"]["emotion_strength"] + scene["metrics"]["role_activity"] for scene in scene_rows]
    )
    theme_ids = [theme["theme_id"] for theme in play_themes]
    narrative_id, narrative_name = narrative_type_from_themes(theme_ids)
    evolution_id, evolution_name = evolution_type_from_curve(narrative_curve)
    flow_id = stable_id("flow", narrative_id, "-".join(theme_ids[:2]), evolution_id)

    top_relations = sorted(relation_rows, key=lambda row: row["weight"], reverse=True)[:5]
    center_role = max(characters, key=lambda item: item["importance"]) if characters else None

    return {
        "play_id": play_id,
        "title": title,
        "source_file": str(path),
        "summary": infer_play_summary(title, play_themes, characters),
        "flow_id": flow_id,
        "themes": play_themes,
        "characters": characters,
        "relations": relation_rows,
        "scenes": scene_rows,
        "narrative": {
            "mode_id": narrative_id,
            "mode_name": narrative_name,
            "curve": narrative_curve,
            "evolution_id": evolution_id,
            "evolution_name": evolution_name,
            "evolution_curve": evolution_curve,
            "peak_scene_id": scene_rows[peak_index]["scene_id"] if scene_rows else "",
            "peak_intensity": round(max(narrative_curve), 4) if narrative_curve else 0,
        },
        "network": {
            "role_count": len(characters),
            "relation_count": len(relation_rows),
            "density": round((2 * len(relation_rows)) / max(len(characters) * (len(characters) - 1), 1), 4),
            "center_role": center_role["name"] if center_role else "",
        },
        "top_relations": top_relations,
    }


def infer_play_summary(title: str, themes: list[dict[str, Any]], characters: list[dict[str, Any]]) -> str:
    theme_names = "、".join(theme["theme"] for theme in themes[:3])
    core_names = "、".join(character["name"] for character in sorted(characters, key=lambda item: item["importance"], reverse=True)[:3])
    return f"《{title}》以{theme_names}为主要组合，围绕{core_names}等人物推进剧情。"


def build_role_rows(plays: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for play in plays:
        max_scene_count = max((character["scene_count"] for character in play["characters"]), default=1)
        max_speech_count = max((character["speech_count"] for character in play["characters"]), default=1)
        for character in play["characters"]:
            scene_ratio = character["scene_count"] / max(max_scene_count, 1)
            speech_ratio = character["speech_count"] / max(max_speech_count, 1)
            rows.append(
                {
                    "play_id": play["play_id"],
                    "character_id": character["character_id"],
                    "script_name": play["title"],
                    "role_name": character["name"],
                    "trade": character["trade"],
                    "raw_trade": character.get("raw_trade", ""),
                    "standard_trade": character["standard_trade"],
                    "major_trade": character["major_trade"],
                    "role_level": character["role_level"],
                    "role_level_label": character["role_level_label"],
                    "character_type": character["role_level_label"],
                    "total_scenes": len(play["scenes"]),
                    "appearance_scenes": character["scene_count"],
                    "appearance_ratio": round(scene_ratio, 4),
                    "stage_span": round(character["scene_count"] / max(len(play["scenes"]), 1), 4),
                    "centrality": character["importance"],
                    "role_text_length": character["text_length"],
                    "lyric_density": round(speech_ratio, 4),
                    "emotion_intensity": round(min(1, character["importance"] * 0.72 + speech_ratio * 0.28), 4),
                    "action_intensity": round(min(1, scene_ratio * 0.55 + character["importance"] * 0.45), 4),
                    "relation_strength": round(min(1, relation_strength_for_character(play, character["character_id"])), 4),
                    "primary_scene_id": character["primary_scene_id"],
                    "linked_theme_ids": "|".join(character["linked_theme_ids"]),
                }
            )
    return rows


def relation_strength_for_character(play: dict[str, Any], character_id: str) -> float:
    weight = 0.0
    for relation in play["relations"]:
        if character_id in {relation["source_character_id"], relation["target_character_id"]}:
            weight += relation["weight"]
    max_weight = max((relation["weight"] for relation in play["relations"]), default=1)
    return weight / max(max_weight * 3, 1)


def build_trade_patterns(role_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in role_rows:
        grouped[(row["script_name"], row["standard_trade"] or row["trade"])].append(row)

    patterns: list[dict[str, Any]] = []
    for (script_name, trade), rows in grouped.items():
        play_id = rows[0]["play_id"]
        patterns.append(
            {
                "play_id": play_id,
                "script_name": script_name,
                "trade": trade,
                "raw_trades": "|".join(sorted({row.get("raw_trade") or row["trade"] for row in rows if row.get("raw_trade") or row["trade"]})),
                "role_count": len(rows),
                "avg_importance": round(sum(row["centrality"] for row in rows) / len(rows), 4),
                "avg_presence": round(sum(row["appearance_ratio"] for row in rows) / len(rows), 4),
                "avg_relation": round(sum(row["relation_strength"] for row in rows) / len(rows), 4),
                "character_ids": "|".join(row["character_id"] for row in rows),
            }
        )
    return patterns


def build_flow_dataset(plays: list[dict[str, Any]]) -> dict[str, Any]:
    flow_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for play in plays:
        flow_groups[play["flow_id"]].append(play)

    flows: list[dict[str, Any]] = []
    for flow_id, group in flow_groups.items():
        representative = group[0]
        themes = representative["themes"]
        narrative = representative["narrative"]
        curve_len = max(len(play["narrative"]["curve"]) for play in group)
        narrative_curve = average_curves([play["narrative"]["curve"] for play in group], curve_len)
        evolution_curve = average_curves([play["narrative"]["evolution_curve"] for play in group], curve_len)
        flows.append(
            {
                "id": flow_id,
                "relationType": dominant_relation_label(group),
                "themeCombo": " + ".join(theme["theme"] for theme in themes[:2]),
                "narrativeType": narrative["mode_name"],
                "evolutionType": narrative["evolution_name"],
                "count": len(group),
                "scripts": [play["play_id"] for play in group],
                "narrativeCurve": narrative_curve,
                "evolutionCurve": evolution_curve,
                "representativePlayId": representative["play_id"],
            }
        )

    scripts = []
    for play in plays:
        themes = play["themes"]
        top_pair = play["top_relations"][0] if play["top_relations"] else None
        scripts.append(
            {
                "id": play["play_id"],
                "title": play["title"],
                "period": "传统京剧",
                "path": play["source_file"],
                "relationType": dominant_relation_label([play]),
                "themeCombo": " + ".join(theme["theme"] for theme in themes[:2]),
                "mainTheme": themes[0]["theme"] if themes else "",
                "subThemes": [theme["theme"] for theme in themes[1:]],
                "narrativeType": play["narrative"]["mode_name"],
                "narrativeCurve": play["narrative"]["curve"],
                "evolutionType": play["narrative"]["evolution_name"],
                "evolutionCurve": play["narrative"]["evolution_curve"],
                "topPair": f"{top_pair['source']} - {top_pair['target']}" if top_pair else "",
                "topRelations": [
                    {
                        "pair": f"{relation['source']} - {relation['target']}",
                        "type": relation["relation_label"],
                        "weight": relation["weight"],
                    }
                    for relation in play["top_relations"][:5]
                ],
                "sceneCount": len(play["scenes"]),
                "network": play["network"],
                "stageEvents": [
                    {
                        "stage": scene["stage_type"],
                        "scene": scene["scene_label"],
                        "summary": scene["summary"],
                        "intensity": scene["metrics"]["plot_strength"],
                    }
                    for scene in play["scenes"]
                ],
                "relationEvidence": [relation["evidence"] for relation in play["top_relations"][:3]],
                "themeEvidence": [theme["evidence"] for theme in themes],
                "detailTags": [theme["theme"] for theme in themes] + [play["narrative"]["mode_name"]],
            }
        )

    return {
        "summary": {
            "scriptCount": len(plays),
            "flowCount": len(flows),
            "source": "five-script linkage dataset",
        },
        "flows": sorted(flows, key=lambda item: item["count"], reverse=True),
        "scripts": scripts,
    }


def average_curves(curves: list[list[float]], length: int) -> list[float]:
    if length <= 0:
        return []
    values = []
    for index in range(length):
        samples = []
        for curve in curves:
            if not curve:
                continue
            src_index = min(len(curve) - 1, round(index * (len(curve) - 1) / max(length - 1, 1)))
            samples.append(curve[src_index])
        values.append(round(sum(samples) / max(len(samples), 1), 4))
    return values


def dominant_relation_label(plays: list[dict[str, Any]]) -> str:
    counter: Counter[str] = Counter()
    for play in plays:
        for relation in play["relations"]:
            counter[relation["relation_label"]] += relation["weight"]
    return counter.most_common(1)[0][0] if counter else "同场协作"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: serialize_csv_value(row.get(field, "")) for field in fieldnames})


def serialize_csv_value(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def build_csv_tables(plays: list[dict[str, Any]], role_rows: list[dict[str, Any]], trade_patterns: list[dict[str, Any]], flow_dataset: dict[str, Any]) -> None:
    play_rows = [
        {
            "play_id": play["play_id"],
            "title": play["title"],
            "source_file": play["source_file"],
            "flow_id": play["flow_id"],
            "summary": play["summary"],
            "scene_count": len(play["scenes"]),
            "character_count": len(play["characters"]),
            "relation_count": len(play["relations"]),
            "main_theme_id": play["themes"][0]["theme_id"] if play["themes"] else "",
            "main_theme": play["themes"][0]["theme"] if play["themes"] else "",
            "narrative_mode": play["narrative"]["mode_name"],
            "evolution_mode": play["narrative"]["evolution_name"],
            "center_role": play["network"]["center_role"],
        }
        for play in plays
    ]
    write_csv(
        TABLE_DIR / "plays.csv",
        play_rows,
        [
            "play_id",
            "title",
            "source_file",
            "flow_id",
            "summary",
            "scene_count",
            "character_count",
            "relation_count",
            "main_theme_id",
            "main_theme",
            "narrative_mode",
            "evolution_mode",
            "center_role",
        ],
    )

    character_rows = [character for play in plays for character in play["characters"]]
    write_csv(
        TABLE_DIR / "characters.csv",
        character_rows,
        [
            "character_id",
            "play_id",
            "name",
            "trade",
            "raw_trade",
            "standard_trade",
            "major_trade",
            "role_level",
            "role_level_label",
            "network_rank",
            "role_order",
            "scene_count",
            "speech_count",
            "mention_count",
            "text_length",
            "importance",
            "scene_ids",
            "primary_scene_id",
            "linked_theme_ids",
            "linked_themes",
        ],
    )

    relation_rows = [relation for play in plays for relation in play["relations"]]
    write_csv(
        TABLE_DIR / "relations.csv",
        relation_rows,
        [
            "relation_id",
            "play_id",
            "source_character_id",
            "target_character_id",
            "source",
            "target",
            "source_trade",
            "target_trade",
            "source_raw_trade",
            "target_raw_trade",
            "source_standard_trade",
            "target_standard_trade",
            "source_level",
            "target_level",
            "source_level_label",
            "target_level_label",
            "relation_type",
            "relation_label",
            "relation_desc",
            "weight",
            "relation_rank",
            "scene_ids",
            "first_scene_no",
            "last_scene_no",
            "evidence",
        ],
    )

    theme_rows = []
    for play in plays:
        for theme in play["themes"]:
            theme_rows.append({"play_id": play["play_id"], **theme})
    write_csv(TABLE_DIR / "play_themes.csv", theme_rows, ["play_id", "theme_id", "theme", "score", "share", "rank", "evidence"])

    scene_rows = []
    scene_character_rows = []
    scene_relation_rows = []
    for play in plays:
        for scene in play["scenes"]:
            scene_rows.append(
                {
                    "scene_id": scene["scene_id"],
                    "play_id": scene["play_id"],
                    "scene_no": scene["scene_no"],
                    "scene_label": scene["scene_label"],
                    "stage_type": scene["stage_type"],
                    "conflict_type": scene["conflict_type"],
                    "summary": scene["summary"],
                    "character_ids": scene["character_ids"],
                    "relation_ids": scene["relation_ids"],
                    **scene["metrics"],
                }
            )
            for character_id, name in zip(scene["character_ids"], scene["character_names"]):
                scene_character_rows.append(
                    {
                        "scene_id": scene["scene_id"],
                        "play_id": scene["play_id"],
                        "character_id": character_id,
                        "character_name": name,
                    }
                )
            for relation_id in scene["relation_ids"]:
                scene_relation_rows.append(
                    {
                        "scene_id": scene["scene_id"],
                        "play_id": scene["play_id"],
                        "relation_id": relation_id,
                    }
                )
    write_csv(
        TABLE_DIR / "scenes.csv",
        scene_rows,
        [
            "scene_id",
            "play_id",
            "scene_no",
            "scene_label",
            "stage_type",
            "conflict_type",
            "summary",
            "character_ids",
            "relation_ids",
            "performance_density",
            "role_activity",
            "conflict_strength",
            "relation_change_strength",
            "emotion_strength",
            "plot_strength",
        ],
    )
    write_csv(TABLE_DIR / "scene_characters.csv", scene_character_rows, ["scene_id", "play_id", "character_id", "character_name"])
    write_csv(TABLE_DIR / "scene_relations.csv", scene_relation_rows, ["scene_id", "play_id", "relation_id"])
    write_csv(
        TABLE_DIR / "role_trade_metrics.csv",
        role_rows,
        [
            "play_id",
            "character_id",
            "script_name",
            "role_name",
            "trade",
            "raw_trade",
            "standard_trade",
            "major_trade",
            "role_level",
            "role_level_label",
            "character_type",
            "total_scenes",
            "appearance_scenes",
            "appearance_ratio",
            "stage_span",
            "centrality",
            "role_text_length",
            "lyric_density",
            "emotion_intensity",
            "action_intensity",
            "relation_strength",
            "primary_scene_id",
            "linked_theme_ids",
        ],
    )
    write_csv(
        TABLE_DIR / "trade_patterns.csv",
        trade_patterns,
        ["play_id", "script_name", "trade", "raw_trades", "role_count", "avg_importance", "avg_presence", "avg_relation", "character_ids"],
    )
    write_csv(
        TABLE_DIR / "main_flows.csv",
        flow_dataset["flows"],
        [
            "id",
            "relationType",
            "themeCombo",
            "narrativeType",
            "evolutionType",
            "count",
            "scripts",
            "narrativeCurve",
            "evolutionCurve",
            "representativePlayId",
        ],
    )
    flow_play_rows = []
    for flow in flow_dataset["flows"]:
        for play_id in flow["scripts"]:
            flow_play_rows.append({"flow_id": flow["id"], "play_id": play_id})
    write_csv(TABLE_DIR / "main_flow_plays.csv", flow_play_rows, ["flow_id", "play_id"])


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    pdfs = find_pdfs()
    plays = [generate_play(path) for path in pdfs]
    role_rows = build_role_rows(plays)
    trade_patterns = build_trade_patterns(role_rows)
    flow_dataset = build_flow_dataset(plays)

    linkage_dataset = {
        "version": "2026-06-16",
        "source": "PDF auto extraction with manually seeded theme taxonomy",
        "plays": plays,
        "roleRows": role_rows,
        "tradeVectorPatterns": trade_patterns,
        "mainFlows": flow_dataset["flows"],
        "schema": {
            "keyFields": {
                "play_id": "剧本唯一编号，来自 PDF 文件名前缀",
                "character_id": "人物唯一编号，由 play_id 与角色名稳定生成",
                "relation_id": "人物关系唯一编号，由 play_id 与人物对稳定生成",
                "scene_id": "场次唯一编号，由 play_id 与场序生成",
                "theme_id": "主题唯一编号，来自固定主题词表",
                "flow_id": "主视图闭环类型唯一编号，由叙事模式、主题组合和演化类型生成",
            }
        },
    }

    write_json(DATA_DIR / "linkage_plays.json", linkage_dataset)
    write_json(DATA_DIR / "loop_data_linkage.json", flow_dataset)
    build_csv_tables(plays, role_rows, trade_patterns, flow_dataset)

    print(f"Generated {len(plays)} plays")
    print(f"JSON: {DATA_DIR / 'linkage_plays.json'}")
    print(f"Tables: {TABLE_DIR}")


if __name__ == "__main__":
    main()
