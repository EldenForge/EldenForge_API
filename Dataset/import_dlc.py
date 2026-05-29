#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import Elden Ring DLC (Shadow of the Erdtree) items into the EldenForge target CSVs.

STDLIB ONLY. Run with: py import_dlc.py  (Python 3.14, Windows)

For each category, read the scrap CSV, keep only rows with dlc == '1', map to the
exact target schema, download the item image locally (self-host), and merge into the
target CSV WITHOUT touching base-game rows.

Idempotent: rows whose id starts with "sote-" are dropped from the target before the
new DLC rows are appended, so the script can be re-run safely.
"""

import csv
import ast
import re
import json
import urllib.request
import os
from pathlib import Path
import time

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRAP_DIR = Path(r"c:/Users/lcour/Desktop/PROJETS/EldenForge/EldenForge_API/Dataset/eldenringScrap")
TARGET_DIR = Path(r"c:/Users/lcour/Desktop/PROJETS/EldenForge/EldenForge_API/Dataset")
IMAGES_ROOT = Path(r"c:/Users/lcour/Desktop/PROJETS/EldenForge/EldenForge_WEB/static/items")

# csv field size can be large because of the upgrades files
csv.field_size_limit(10 * 1024 * 1024)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_csv(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_dict_string(raw):
    """Parse a scrap dict-string like "{'Phy': '125 ', 'Mag': '- '}" into a dict.

    Values are stripped. Returns {} on failure / empty input.
    """
    if raw is None:
        return {}
    raw = raw.strip()
    if not raw:
        return {}
    try:
        obj = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return {}
    # some scrap columns are a list-of-one-dict
    if isinstance(obj, list):
        obj = obj[0] if obj and isinstance(obj[0], dict) else {}
    if not isinstance(obj, dict):
        return {}
    out = {}
    for k, v in obj.items():
        kk = k.strip() if isinstance(k, str) else k
        vv = v.strip() if isinstance(v, str) else v
        out[kk] = vv
    return out


def is_absent(v):
    """True if a scrap value represents 'no value' ('-' / '' / None)."""
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s == "-"


def to_int(v, default=0):
    if is_absent(v):
        return default
    s = str(v).strip()
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return default


def to_float(v, default=0.0):
    if is_absent(v):
        return default
    s = str(v).strip()
    try:
        return float(s)
    except ValueError:
        return default


def to_num(v):
    """int if integral else float; for damage-reduction amounts (88 or 58.58)."""
    f = to_float(v, 0.0)
    if f == int(f):
        return int(f)
    return f


# ---------------------------------------------------------------------------
# Image download (self-host)
# ---------------------------------------------------------------------------
IMG_OK = 0
IMG_FAIL = 0
IMG_FAIL_URLS = []


def download_image(url, cat, item_id):
    """Download `url` into IMAGES_ROOT/<cat>/<item_id>.<ext>.

    Returns the relative front path "/items/<cat>/<filename>" on success, else "".
    Caches: skips download if the file already exists.
    """
    global IMG_OK, IMG_FAIL
    url = (url or "").strip()
    if not url:
        IMG_FAIL += 1
        IMG_FAIL_URLS.append("(empty url) " + str(item_id))
        return ""

    # deduce extension from the URL
    ext = ".png"
    m = re.search(r"\.([a-zA-Z0-9]{2,4})(?:\?|$)", url.split("/")[-1])
    if m:
        candidate = "." + m.group(1).lower()
        if candidate in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            ext = candidate

    filename = f"{item_id}{ext}"
    cat_dir = IMAGES_ROOT / cat
    cat_dir.mkdir(parents=True, exist_ok=True)
    dest = cat_dir / filename
    rel = f"/items/{cat}/{filename}"

    if dest.exists() and dest.stat().st_size > 0:
        IMG_OK += 1
        return rel

    headers = {"User-Agent": "Mozilla/5.0"}
    last_err = None
    for attempt in range(2):  # 1 try + 1 retry
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            if not data:
                raise ValueError("empty body")
            with open(dest, "wb") as fh:
                fh.write(data)
            IMG_OK += 1
            return rel
        except Exception as e:  # noqa: BLE001 - we must not crash on any download error
            last_err = e
            if attempt == 0:
                time.sleep(1.0)

    IMG_FAIL += 1
    IMG_FAIL_URLS.append(f"{url}  ({type(last_err).__name__}: {last_err})")
    # clean up a possible partial file
    try:
        if dest.exists() and dest.stat().st_size == 0:
            dest.unlink()
    except OSError:
        pass
    return ""


# ---------------------------------------------------------------------------
# Field builders
# ---------------------------------------------------------------------------
ATTACK_MAP = [("Phy", "Phy"), ("Mag", "Mag"), ("Fir", "Fire"), ("Lit", "Ligt"), ("Hol", "Holy")]
DEFENCE_MAP = [("Phy", "Phy"), ("Mag", "Mag"), ("Fir", "Fire"), ("Lit", "Ligt"), ("Hol", "Holy"), ("Bst", "Boost")]
SCALING_KEYS = ["Str", "Dex", "Int", "Fai", "Arc"]


def build_attack(attack_power_dict):
    """weapons/shields attack from `attack power` dict; always append Crit:100."""
    out = []
    for src, dst in ATTACK_MAP:
        out.append({"name": dst, "amount": to_int(attack_power_dict.get(src), 0)})
    out.append({"name": "Crit", "amount": 100})
    return out


def build_defence_shield(damage_reduction_dict):
    out = []
    for src, dst in DEFENCE_MAP:
        out.append({"name": dst, "amount": to_num(damage_reduction_dict.get(src))})
    return out


def build_scales_with(stat_scaling_dict):
    out = []
    for k in SCALING_KEYS:
        v = stat_scaling_dict.get(k)
        if not is_absent(v):
            out.append({"name": k, "scaling": str(v).strip()})
    return out


def build_required_attributes(requirements_raw):
    d = parse_dict_string(requirements_raw)
    out = []
    for k, v in d.items():
        out.append({"name": k, "amount": to_int(v, 0)})
    return out


# ---------------------------------------------------------------------------
# Upgrades lookup (base = +0 row, i.e. upgrade without a '+')
# ---------------------------------------------------------------------------

def build_upgrades_lookup(path, name_col):
    """Return {item_name: base_upgrade_row}. Base = first row whose upgrade has no '+'."""
    lookup = {}
    with open(path, "r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get(name_col) or "").strip()
            if not name or name in lookup:
                continue
            upgrade = (row.get("upgrade") or "").strip()
            if "+" not in upgrade:
                lookup[name] = row
    return lookup


# ---------------------------------------------------------------------------
# Category processors -> each returns list of mapped target rows (dicts)
# ---------------------------------------------------------------------------

def process_weaponlike(cat, scrap_file, upgrades_file, upgrades_name_col, include_defence):
    """Shared logic for weapons and shields."""
    rows = read_csv(SCRAP_DIR / scrap_file)
    dlc = [r for r in rows if (r.get("dlc") or "").strip() == "1"]
    upgrades = build_upgrades_lookup(SCRAP_DIR / upgrades_file, upgrades_name_col)

    out = []
    for r in dlc:
        item_id = f"sote-{cat}-{r['id']}"
        base = upgrades.get(r["name"].strip())
        if base:
            attack = build_attack(parse_dict_string(base.get("attack power")))
            scales = build_scales_with(parse_dict_string(base.get("stat scaling")))
            if include_defence:
                defence = build_defence_shield(parse_dict_string(base.get("damage reduction (%)")))
            else:
                defence = []
        else:
            attack = [{"name": "Crit", "amount": 100}]
            scales = []
            defence = []

        image = download_image(r.get("image"), cat, item_id)
        out.append({
            "id": item_id,
            "name": r.get("name", "").strip(),
            "image": image,
            "description": r.get("description", ""),
            "attack": str(attack),
            "defence": str(defence),
            "scalesWith": str(scales),
            "requiredAttributes": str(build_required_attributes(r.get("requirements"))),
            "category": r.get("category", "").strip(),
            "weight": to_float(r.get("weight"), 0.0),
        })
    return out


ARMOR_TYPE_MAP = {
    "helm": "Helm",
    "chest armor": "Chest Armor",
    "gauntlets": "Gauntlets",
    "leg armor": "Leg Armor",
}
DMGNEG_MAP = [
    ("Phy", "Phy"), ("VS Str.", "Strike"), ("VS Sla.", "Slash"), ("VS Pie.", "Pierce"),
    ("Mag", "Magic"), ("Fir", "Fire"), ("Lit", "Ligt"), ("Hol", "Holy"),
]
RESIST_MAP = [
    ("Imm.", "Immunity"), ("Rob.", "Robustness"), ("Foc.", "Focus"),
    ("Vit.", "Vitality"), ("Poi.", "Poise"),
]


def process_armors():
    cat = "armors"
    rows = read_csv(SCRAP_DIR / "armors.csv")
    dlc = [r for r in rows if (r.get("dlc") or "").strip() == "1"]
    out = []
    for r in dlc:
        item_id = f"sote-{cat}-{r['id']}"
        category = ARMOR_TYPE_MAP.get((r.get("type") or "").strip().lower(), (r.get("type") or "").strip())

        dn = parse_dict_string(r.get("damage negation"))
        dmg = [{"name": dst, "amount": to_num(dn.get(src))} for src, dst in DMGNEG_MAP if src in dn]
        # keep order/coverage even if absent? spec maps present keys; include mapped ones present
        rs = parse_dict_string(r.get("resistance"))
        res = [{"name": dst, "amount": to_int(rs.get(src), 0)} for src, dst in RESIST_MAP if src in rs]

        image = download_image(r.get("image"), cat, item_id)
        out.append({
            "id": item_id,
            "name": r.get("name", "").strip(),
            "image": image,
            "description": r.get("description", ""),
            "category": category,
            "dmgNegation": str(dmg),
            "resistance": str(res),
            "weight": to_float(r.get("weight"), 0.0),
        })
    return out


def process_talismans():
    cat = "talismans"
    rows = read_csv(SCRAP_DIR / "talismans.csv")
    dlc = [r for r in rows if (r.get("dlc") or "").strip() == "1"]
    out = []
    for r in dlc:
        item_id = f"sote-{cat}-{r['id']}"
        image = download_image(r.get("image"), cat, item_id)
        out.append({
            "id": item_id,
            "name": r.get("name", "").strip(),
            "image": image,
            "description": r.get("description", ""),
            "effect": r.get("effect", ""),
        })
    return out


def process_spell(cat, scrap_file, spell_type):
    rows = read_csv(SCRAP_DIR / scrap_file)
    dlc = [r for r in rows if (r.get("dlc") or "").strip() == "1"]
    out = []
    for r in dlc:
        item_id = f"sote-{cat}-{r['id']}"
        requires = [
            {"name": "Intelligence", "amount": to_int(r.get("INT"), 0)},
            {"name": "Faith", "amount": to_int(r.get("FAI"), 0)},
            {"name": "Arcane", "amount": to_int(r.get("ARC"), 0)},
        ]
        image = download_image(r.get("image"), cat, item_id)
        out.append({
            "id": item_id,
            "name": r.get("name", "").strip(),
            "image": image,
            "description": r.get("description", ""),
            "type": spell_type,
            "cost": to_int(r.get("FP"), 0),
            "slots": to_int(r.get("slot"), 0),
            "effects": r.get("effect", ""),
            "requires": str(requires),
        })
    return out


def process_spirits():
    cat = "spirits"
    rows = read_csv(SCRAP_DIR / "spiritAshes.csv")
    dlc = [r for r in rows if (r.get("dlc") or "").strip() == "1"]
    out = []
    for r in dlc:
        item_id = f"sote-{cat}-{r['id']}"
        image = download_image(r.get("image"), cat, item_id)
        out.append({
            "id": item_id,
            "name": r.get("name", "").strip(),
            "image": image,
            "description": r.get("description", ""),
            "fpCost": to_int(r.get("FP cost"), to_int(r.get("FP cost"))),
            "hpCost": to_int(r.get("HP cost"), to_int(r.get("HP cost"))),
            "effect": r.get("effect", ""),
        })
    return out


# ---------------------------------------------------------------------------
# Merge into target CSV (idempotent on "sote-" ids)
# ---------------------------------------------------------------------------

def merge_into_target(target_name, new_rows):
    """Drop existing sote- rows, keep base rows, append new_rows, rewrite. Returns (base_count, dlc_count, total)."""
    path = TARGET_DIR / target_name
    existing = read_csv(path)
    header = list(existing[0].keys()) if existing else None
    if header is None:
        # read header directly if file empty of rows
        with open(path, "r", encoding="utf-8", newline="") as fh:
            header = next(csv.reader(fh))

    base_rows = [r for r in existing if not str(r.get("id", "")).startswith("sote-")]
    base_count = len(base_rows)

    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        for r in base_rows:
            writer.writerow([r.get(col, "") for col in header])
        for r in new_rows:
            writer.writerow([r.get(col, "") for col in header])

    return base_count, len(new_rows), base_count + len(new_rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== EldenForge DLC import (Shadow of the Erdtree) ===\n")

    results = {}  # target_name -> (base, dlc, total)
    examples = {}

    # weapons
    weapons = process_weaponlike("weapons", "weapons.csv", "weapons_upgrades.csv", "weapon name", include_defence=False)
    results["weapons.csv"] = merge_into_target("weapons.csv", weapons)
    for w in weapons:
        if w["name"] == "Milady":
            examples["weapon (Milady)"] = w

    # shields  (note: upgrades name column is 'shield name')
    shields = process_weaponlike("shields", "shields.csv", "shields_upgrades.csv", "shield name", include_defence=True)
    results["shields.csv"] = merge_into_target("shields.csv", shields)

    # armors
    armors = process_armors()
    results["armors.csv"] = merge_into_target("armors.csv", armors)
    if armors:
        examples["armor"] = armors[0]

    # talismans
    talismans = process_talismans()
    results["talismans.csv"] = merge_into_target("talismans.csv", talismans)

    # sorceries / incantations
    sorceries = process_spell("sorceries", "sorceries.csv", "Sorceries")
    results["sorceries.csv"] = merge_into_target("sorceries.csv", sorceries)
    incantations = process_spell("incantations", "incantations.csv", "Incantations")
    results["incantations.csv"] = merge_into_target("incantations.csv", incantations)

    # spirits
    spirits = process_spirits()
    results["spirits.csv"] = merge_into_target("spirits.csv", spirits)

    # ----- Validation report -----
    print("--- Counts per category (base / DLC added / new total) ---")
    for name in ["weapons.csv", "shields.csv", "armors.csv", "talismans.csv",
                 "sorceries.csv", "incantations.csv", "spirits.csv"]:
        b, d, t = results[name]
        print(f"  {name:<18} base={b:<5} dlc=+{d:<4} total={t}")

    total_imgs = IMG_OK + IMG_FAIL
    rate = (IMG_OK / total_imgs * 100) if total_imgs else 0.0
    print(f"\n--- Images ---")
    print(f"  OK={IMG_OK}  FAIL={IMG_FAIL}  (success {rate:.1f}% of {total_imgs})")
    if IMG_FAIL_URLS:
        print("  Sample failed URLs:")
        for u in IMG_FAIL_URLS[:5]:
            print("    -", u)

    print("\n--- Example mapped rows ---")
    for label in ("weapon (Milady)", "armor"):
        if label in examples:
            print(f"\n  [{label}]")
            print("   ", json.dumps(examples[label], ensure_ascii=False))

    print("\nDone.")


if __name__ == "__main__":
    main()
