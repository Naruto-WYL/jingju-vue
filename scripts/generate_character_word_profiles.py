from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
LINKAGE_PATH = ROOT / "public" / "data" / "linkage_plays.json"
OUTPUT_PATH = ROOT / "src" / "components" / "leftBottom" / "characterWordProfiles.js"
PDF_DIR = Path("D:/jingju/数据")

PDF_NAMES = {
    "01004001": "01004001_逍遥津.pdf",
    "01012004": "01012004_莲花湖.pdf",
    "01040005": "01040005_万花船.pdf",
    "02008006": "02008006_北汉王.pdf",
    "04008002": "04008002_十三妹.pdf",
}

SEMANTIC_TERMS = {
    "权力政治": ["权谋", "专权", "篡位", "夺位", "权臣", "谋反", "朝政", "奸谋", "江山"],
    "家国忠义": ["忠义", "忠臣", "报国", "护国", "家国", "社稷", "君臣", "忧国", "忠心"],
    "战争行动": ["征战", "战场", "兴兵", "领兵", "兵马", "将军", "武艺", "交锋", "厮杀"],
    "女性处境": ["皇后", "夫人", "小姐", "女儿", "闺房", "贞烈", "女流", "命苦"],
    "侠义复仇": ["报仇", "复仇", "侠义", "豪侠", "绿林", "义气", "英雄", "除害"],
    "公案法理": ["审问", "公堂", "官司", "冤枉", "告状", "拿问", "法度"],
    "婚恋姻缘": ["姻缘", "婚姻", "夫妻", "相会", "定亲", "拜堂", "爱慕", "情缘"],
    "家庭伦理": ["父子", "母女", "夫妻", "兄弟", "孝顺", "家门", "骨肉", "亲情"],
    "市井喜剧": ["诙谐", "取笑", "胡闹", "玩笑", "店家", "市井", "滑稽", "打诨"],
    "谋略行动": ["计策", "谋划", "商议", "主意", "设计", "探听", "传信"],
    "武力行动": ["武艺", "勇猛", "交战", "厮杀", "刀枪", "拳棒", "英勇"],
    "悲剧情绪": ["伤心", "悲痛", "落泪", "痛哭", "含恨", "悲伤"],
    "威权行动": ["威严", "大胆", "放肆", "拿下", "斩首", "有罪", "发怒"],
    "忠贞品格": ["忠贞", "守节", "贞烈", "不屈", "至死", "忠心"],
    "机变行动": ["机敏", "聪明", "识破", "随机", "巧计", "乔装"],
    "救助行为": ["搭救", "相助", "救命", "成全", "宽恕"],
    "奸谋冲突": ["奸贼", "奸臣", "诡计", "暗害", "行刺", "陷害"],
    "科举功名": ["赶考", "功名", "文章", "书生", "状元", "金榜"],
    "乔装奇缘": ["乔装", "女装", "媒婆", "使女", "撮合", "观音"],
}


def extract_pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def split_character_text(text: str, character_names: list[str]) -> dict[str, str]:
    result: dict[str, list[str]] = defaultdict(list)
    current: list[str] = []
    pending: list[str] = []
    names = set(character_names)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.endswith("、") and line[:-1] in names:
            pending.append(line[:-1])
            continue

        if "（" in line:
            prefix, remainder = line.split("（", 1)
            speakers = pending + re.split(r"[、，,]\s*", prefix.strip())
            pending = []
            speakers = [speaker for speaker in speakers if speaker in names]

            if not speakers:
                current = []
                continue

            current = speakers
            content = remainder.split("）", 1)[1].strip() if "）" in remainder else ""
            if content:
                for speaker in current:
                    result[speaker].append(content)
            continue

        pending = []
        if current and not line.startswith(("中国京剧戏考", "http://", "【", "注释", "情节", "主要角色")):
            for speaker in current:
                result[speaker].append(line)

    return {name: "".join(parts) for name, parts in result.items()}


def semantic_scores(text: str) -> list[tuple[str, float, list[tuple[str, int]]]]:
    rows: list[tuple[str, float, list[tuple[str, int]]]] = []
    for label, terms in SEMANTIC_TERMS.items():
        matches = [(term, text.count(term)) for term in terms if text.count(term)]
        score = sum(count for _, count in matches)
        if score:
            rows.append((label, float(score), sorted(matches, key=lambda item: (-item[1], item[0]))))
    return sorted(rows, key=lambda item: (-item[1], item[0]))


def merge_pairs(pairs: list[tuple[str, float]], limit: int = 26) -> list[list[object]]:
    merged: dict[str, float] = {}
    for text, weight in pairs:
        text = str(text or "").strip()
        if not text:
            continue
        text = text[:8]
        merged[text] = max(merged.get(text, 0), float(weight))
    return [
        [text, round(weight, 2)]
        for text, weight in sorted(merged.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def main() -> None:
    data = json.loads(LINKAGE_PATH.read_text(encoding="utf-8"))
    plays = {play["play_id"]: play for play in data["plays"]}
    character_texts: dict[str, str] = {}

    for play_id, pdf_name in PDF_NAMES.items():
        play = plays[play_id]
        text = extract_pdf_text(PDF_DIR / pdf_name)
        by_name = split_character_text(text, [character["name"] for character in play["characters"]])
        for character in play["characters"]:
            character_texts[character["character_id"]] = by_name.get(character["name"], "")

    profiles: dict[str, dict[str, object]] = {}

    for play in data["plays"]:
        theme_names = {theme["theme_id"]: theme["theme"] for theme in play.get("themes", [])}
        for character in play.get("characters", []):
            character_id = character["character_id"]
            text = character_texts.get(character_id, "")
            pairs: list[tuple[str, float]] = [
                (character["name"], 15),
                (character.get("role_level_label") or "角色", 10),
            ]

            pairs.append((f"出场{int(character.get('scene_count') or 0)}场", 8.2))
            if int(character.get("speech_count") or 0) >= 30:
                pairs.append(("台词密集", 8.5))
            elif int(character.get("speech_count") or 0) >= 12:
                pairs.append(("对白推进", 7.2))
            if float(character.get("importance") or 0) >= 0.62:
                pairs.append(("关系核心", 8.8))
            elif float(character.get("importance") or 0) >= 0.38:
                pairs.append(("主要推动", 7.5))

            for index, (label, score, matches) in enumerate(semantic_scores(text)[:6]):
                if score >= 2:
                    pairs.append((label, max(5.2, 9.4 - index * 0.55)))
                for term_index, (term, count) in enumerate(matches[:2]):
                    pairs.append((term, max(4.5, 7.6 - index * 0.35 - term_index * 0.45 + min(count, 3) * 0.2)))

            for index, theme_id in enumerate(character.get("linked_theme_ids", [])[:3]):
                pairs.append((theme_names.get(theme_id, ""), 9 - index * 0.6))

            relations = sorted(
                (
                    relation
                    for relation in play.get("relations", [])
                    if character_id in (relation.get("source_character_id"), relation.get("target_character_id"))
                ),
                key=lambda relation: float(relation.get("weight") or 0),
                reverse=True,
            )[:4]
            for index, relation in enumerate(relations):
                other_name = (
                    relation.get("target")
                    if relation.get("source_character_id") == character_id
                    else relation.get("source")
                )
                pairs.append((relation.get("relation_label") or relation.get("relation_type"), 8 - index * 0.5))
                pairs.append((other_name, 7.5 - index * 0.5))

            scene_ids = set(character.get("scene_ids") or [])
            scenes = [scene for scene in play.get("scenes", []) if scene.get("scene_id") in scene_ids]
            stages = Counter(scene.get("stage_type") for scene in scenes if scene.get("stage_type"))
            conflicts = Counter(scene.get("conflict_type") for scene in scenes if scene.get("conflict_type"))
            for index, (stage, _) in enumerate(stages.most_common(2)):
                pairs.append((stage, 6.4 - index * 0.5))
            for index, (conflict, _) in enumerate(conflicts.most_common(2)):
                pairs.append((conflict, 6.8 - index * 0.5))

            profiles[character_id] = {
                "playId": play["play_id"],
                "name": character["name"],
                "trade": character.get("standard_trade") or character.get("trade") or "",
                "textLength": len(text),
                "words": merge_pairs(pairs),
            }

    output = (
        "// Generated from the five supplied Jingju PDFs. Do not edit by hand.\n"
        f"export const characterWordProfiles = {json.dumps(profiles, ensure_ascii=False, indent=2)}\n"
    )
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Wrote {len(profiles)} character profiles to {OUTPUT_PATH}")
    print(f"Characters with extracted speech: {sum(bool(text) for text in character_texts.values())}/{len(character_texts)}")


if __name__ == "__main__":
    main()
