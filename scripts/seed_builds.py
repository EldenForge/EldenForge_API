#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insere des builds fictifs dans la base eldenforge_dev pour les screenshots.

Run depuis EldenForge_API/ : py scripts/seed_builds.py

Idempotent : nettoie d'abord les users seed_* existants puis reinsere tout.
Utilisation :
  - Lance ce script pour populer la base
  - Puis lance uvicorn main:app --reload --port 8000
  - Puis lance npm run dev cote WEB
  - Prends les screenshots sur http://localhost:5173
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from argon2 import PasswordHasher
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Base
from models.user import User
from models.build import Build
from models.build_like import BuildLike


# ── DB ──
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERREUR : DATABASE_URL absent (.env manquant ?)")
    sys.exit(1)


# ── Datasets ──
DS_DIR = Path(__file__).parent.parent / "Dataset"

def load_ds(name):
    return pd.read_csv(DS_DIR / f"{name}.csv")

def find_id(df, name_substring):
    """Renvoie le premier item dont le nom contient la sous-chaine."""
    matches = df[df["name"].str.lower().str.contains(name_substring.lower(), na=False, regex=False)]
    if matches.empty:
        print(f"WARN : {name_substring} non trouve")
        return None
    return str(matches.iloc[0]["id"])


def find_ash_by_name(df, name_substring):
    """Ashes ont 'Ash Of War: ' en prefix, cherche apres."""
    matches = df[df["name"].str.lower().str.contains(name_substring.lower(), na=False, regex=False)]
    if matches.empty:
        return None
    return str(matches.iloc[0]["id"])


print("Chargement des datasets...")
weapons = load_ds("weapons")
shields = load_ds("shields")
armors = load_ds("armors")
talismans = load_ds("talismans")
sorceries = load_ds("sorceries")
incantations = load_ds("incantations")
spirits = load_ds("spirits")
ashes = load_ds("ashes")
ammos = load_ds("ammos")


# ── Items shortcuts ──
UCHIGATANA = find_id(weapons, "Uchigatana")
RIVERS_OF_BLOOD = find_id(weapons, "Rivers of Blood")
COLOSSAL = find_id(weapons, "Ruins Greatsword") or find_id(weapons, "Greatsword")
STAR_FIST = find_id(weapons, "Star Fist") or find_id(weapons, "Iron Ball")
MOONVEIL = find_id(weapons, "Moonveil")
GHIZA = find_id(weapons, "Ghiza") or find_id(weapons, "Wheel")
BLASPHEMOUS_BLADE = find_id(weapons, "Blasphemous Blade") or find_id(weapons, "Blasphemous")
ERDTREE_BOW = find_id(weapons, "Erdtree Bow") or find_id(weapons, "Bow")
ASTRO_STAFF = find_id(weapons, "Astrologer") or find_id(weapons, "Staff")
ERDTREE_SEAL = find_id(weapons, "Erdtree Seal") or find_id(weapons, "Seal")

FINGERPRINT_SHIELD = find_id(shields, "Fingerprint") or find_id(shields, "Greatshield")
BRASS_SHIELD = find_id(shields, "Brass Shield") or find_id(shields, "Kite Shield")

# Armor par slot (chercher par category)
def armor_by_cat(cat, name_sub=None):
    df = armors[armors["category"] == cat]
    if name_sub:
        m = df[df["name"].str.lower().str.contains(name_sub.lower(), na=False, regex=False)]
        if not m.empty:
            return str(m.iloc[0]["id"])
    if not df.empty:
        return str(df.iloc[0]["id"])
    return None

HEAD_SAMURAI = armor_by_cat("Helm", "Land of Reeds")
CHEST_SAMURAI = armor_by_cat("Chest Armor", "Land of Reeds")
HANDS_SAMURAI = armor_by_cat("Gauntlets", "Land of Reeds")
LEGS_SAMURAI = armor_by_cat("Leg Armor", "Land of Reeds")

HEAD_ASTRO = armor_by_cat("Helm", "Astrologer")
CHEST_ASTRO = armor_by_cat("Chest Armor", "Astrologer")
HANDS_ASTRO = armor_by_cat("Gauntlets", "Astrologer")
LEGS_ASTRO = armor_by_cat("Leg Armor", "Astrologer")

HEAD_LIONEL = armor_by_cat("Helm", "Lionel")
CHEST_LIONEL = armor_by_cat("Chest Armor", "Lionel")
HANDS_LIONEL = armor_by_cat("Gauntlets", "Lionel")
LEGS_LIONEL = armor_by_cat("Leg Armor", "Lionel")

HEAD_ZAMOR = armor_by_cat("Helm", "Zamor")
CHEST_ZAMOR = armor_by_cat("Chest Armor", "Zamor")
HANDS_ZAMOR = armor_by_cat("Gauntlets", "Zamor")
LEGS_ZAMOR = armor_by_cat("Leg Armor", "Zamor")

# Talismans
TAL_RADAGON = find_id(talismans, "Radagon Icon")
TAL_LORD_BLOOD = find_id(talismans, "Lord of Blood")
TAL_ERDTREE_FAVOR = find_id(talismans, "Erdtree's Favor")
TAL_GRAVEN_MASS = find_id(talismans, "Graven-Mass")
TAL_MAGIC_SCORPION = find_id(talismans, "Magic Scorpion")
TAL_GREEN_TURTLE = find_id(talismans, "Green Turtle")
TAL_STARSCOURGE = find_id(talismans, "Starscourge Heirloom")
TAL_MILLICENT = find_id(talismans, "Millicent")

# Sorts
SORC_COMET = find_id(sorceries, "Comet ") or find_id(sorceries, "Comet")
SORC_COMET_AZUR = find_id(sorceries, "Comet Azur")
SORC_ROCK_SLING = find_id(sorceries, "Rock Sling")
SORC_GLINTSTONE = find_id(sorceries, "Glintstone Pebble")

INC_GOLDEN_VOW = find_id(incantations, "Golden Vow")
INC_FLAME_GRANT = find_id(incantations, "Flame, Grant Me Strength")
INC_LIGHTNING_SPEAR = find_id(incantations, "Lightning Spear")
INC_ROTTEN_BREATH = find_id(incantations, "Rotten Breath")
INC_BLACK_FLAME = find_id(incantations, "Black Flame ") or find_id(incantations, "Black Flame")

# Esprits
SPI_MIMIC = find_id(spirits, "Mimic Tear")
SPI_TICHE = find_id(spirits, "Black Knife Tiche")
SPI_JELLYFISH = find_id(spirits, "Lone Wolf")  # fallback

# Ashes of war
ASH_BLOODY_SLASH = find_ash_by_name(ashes, "Bloody Slash")
ASH_UNSHEATHE = find_ash_by_name(ashes, "Unsheathe")
ASH_LIONS_CLAW = find_ash_by_name(ashes, "Lion's Claw") or find_ash_by_name(ashes, "Lion")
ASH_HOARFROST = find_ash_by_name(ashes, "Hoarfrost")
ASH_GLINTSTONE = find_ash_by_name(ashes, "Glintstone Pebble")


# ── Users seed ──
SEED_USERS = [
    ("Tarnished_42", "seed42@example.local", "PasswordSeed42!"),
    ("StarCaster", "star@example.local", "PasswordSeed42!"),
    ("Goldmask", "gold@example.local", "PasswordSeed42!"),
    ("Mohg_Lord", "mohg@example.local", "PasswordSeed42!"),
    ("BeastClaw", "beast@example.local", "PasswordSeed42!"),
    ("PoisonRose", "poison@example.local", "PasswordSeed42!"),
    ("MelinaFinger", "melina@example.local", "PasswordSeed42!"),
    ("Ranni_Witch", "ranni@example.local", "PasswordSeed42!"),
]


def stats(vig=10, mnd=10, end=10, str_=10, dex=10, int_=10, fai=10, arc=10):
    return {"vigor": vig, "mind": mnd, "endurance": end, "strength": str_,
            "dexterity": dex, "intelligence": int_, "faith": fai, "arcane": arc}

def empty_armor():
    return {"head": None, "chest": None, "hands": None, "legs": None}

def empty_weapons():
    return {"right": None, "left": None,
            "rightSecondary": [None, None], "leftSecondary": [None, None]}

def empty_ashes():
    return {"right": None, "left": None,
            "rightSecondary": [None, None], "leftSecondary": [None, None]}

def loadout(name, s, armor, weapons, ashes_, talismans_, spells, spirit, guide):
    return {
        "name": name,
        "stats": s,
        "armor": armor,
        "talismans": talismans_ + [None] * (4 - len(talismans_)),
        "weapons": weapons,
        "ashes": ashes_,
        "ammos": {"arrows": [None, None], "bolts": [None, None]},
        "spells": spells + [None] * (10 - len(spells)),
        "spirit": spirit,
        "guide": guide,
    }


def build_data(loadouts, active=0):
    return {"v": 2, "loadouts": loadouts, "activeIndex": active}


# ── Builds fictifs ──
BUILDS = [
    # (author_pseudo, name, description, intent, tags, is_public, data, forked_from_idx)
    ("Tarnished_42", "Bleed Samurai Uchigatana",
     "Build sanguine classique au katana, focalise dexterite et arcane pour maximiser les procs de saignement.",
     "pve", ["Bleed", "Dexterity"], True,
     build_data([loadout("Main", stats(vig=45, end=25, str_=16, dex=50, arc=45),
                         {"head": HEAD_SAMURAI, "chest": CHEST_SAMURAI,
                          "hands": HANDS_SAMURAI, "legs": LEGS_SAMURAI},
                         {"right": UCHIGATANA, "left": None,
                          "rightSecondary": [RIVERS_OF_BLOOD, None],
                          "leftSecondary": [None, None]},
                         {"right": ASH_BLOODY_SLASH, "left": None,
                          "rightSecondary": [ASH_UNSHEATHE, None],
                          "leftSecondary": [None, None]},
                         [TAL_LORD_BLOOD, TAL_MILLICENT, TAL_ERDTREE_FAVOR],
                         [], SPI_MIMIC,
                         "## Strategie\n\nCe build repose sur le [Uchigatana] avec l'infusion Sang.\n\n"
                         "Rushez la [Rivers of Blood] pour maximiser les procs de saignement en secondaire.\n"
                         "Toujours accompagner le [Mimic Tear Ashes] pour distraire.")]),
     None),

    ("StarCaster", "Astrologer Glass Cannon",
     "Full intelligence, dommages massifs à distance mais tres fragile. Comet Azur pour les boss.",
     "pve", ["Sorceries", "Intelligence"], True,
     build_data([loadout("Main", stats(vig=25, mnd=40, end=15, str_=8, dex=12, int_=80),
                         {"head": HEAD_ASTRO, "chest": CHEST_ASTRO,
                          "hands": HANDS_ASTRO, "legs": LEGS_ASTRO},
                         {"right": ASTRO_STAFF, "left": None,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         empty_ashes(),
                         [TAL_GRAVEN_MASS, TAL_MAGIC_SCORPION, TAL_RADAGON, TAL_STARSCOURGE],
                         [SORC_COMET_AZUR, SORC_COMET, SORC_ROCK_SLING, SORC_GLINTSTONE],
                         SPI_MIMIC,
                         "## Guide\n\n[Comet Azur] pour les boss. Boit un [Cerulean Hidden Tear] "
                         "dans la Fiole de Wondrous Physick pour cast gratuitement.\n\n"
                         "[Rock Sling] pour les enemis mineurs, [Glintstone Pebble] contre les casters.")]),
     None),

    ("Goldmask", "Faith Tank Golden Vow",
     "Build tanky base foi. Golden Vow + Erdtree Seal pour buff toute l'equipe en coop.",
     "coop", ["Faith", "Incantations"], True,
     build_data([loadout("Main", stats(vig=60, mnd=25, end=30, str_=25, fai=60),
                         {"head": HEAD_LIONEL, "chest": CHEST_LIONEL,
                          "hands": HANDS_LIONEL, "legs": LEGS_LIONEL},
                         {"right": ERDTREE_SEAL, "left": BRASS_SHIELD,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         empty_ashes(),
                         [TAL_ERDTREE_FAVOR, TAL_RADAGON],
                         [INC_GOLDEN_VOW, INC_FLAME_GRANT, INC_LIGHTNING_SPEAR],
                         SPI_TICHE,
                         "## Coop faith\n\n[Golden Vow] au debut de chaque combat, "
                         "[Flame, Grant Me Strength] avant les phases tendues.\n\n"
                         "En coop, prioriser les buffs sur les DPS.")]),
     None),

    ("Mohg_Lord", "Arcane Bleed PvP",
     "PvP focus arcane, procs de sang + bonus talisman. Roue de Ghiza pour rush.",
     "pvp", ["Arcane", "Bleed", "PvP"], True,
     build_data([loadout("Main", stats(vig=50, mnd=15, end=25, str_=20, dex=25, arc=60),
                         {"head": HEAD_ZAMOR, "chest": CHEST_ZAMOR,
                          "hands": HANDS_ZAMOR, "legs": LEGS_ZAMOR},
                         {"right": GHIZA, "left": None,
                          "rightSecondary": [UCHIGATANA, None],
                          "leftSecondary": [None, None]},
                         {"right": ASH_LIONS_CLAW, "left": None,
                          "rightSecondary": [ASH_BLOODY_SLASH, None],
                          "leftSecondary": [None, None]},
                         [TAL_LORD_BLOOD, TAL_GREEN_TURTLE, TAL_RADAGON],
                         [], None,
                         "## PvP setup\n\n[Ghiza's Wheel] pour surprendre, retour au "
                         "[Uchigatana] si l'adversaire pare.\n\nR1 spam sur roulement adverse.")]),
     None),

    ("BeastClaw", "Strength Colossal Ruins",
     "Full force, la Ruins Greatsword. Un shot les boss avec Lion's Claw.",
     "pve", ["Strength", "End-game"], True,
     build_data([loadout("Main", stats(vig=55, mnd=15, end=40, str_=70, dex=14, int_=16),
                         {"head": HEAD_LIONEL, "chest": CHEST_LIONEL,
                          "hands": HANDS_LIONEL, "legs": LEGS_LIONEL},
                         {"right": COLOSSAL, "left": None,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         {"right": ASH_LIONS_CLAW, "left": None,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         [TAL_ERDTREE_FAVOR, TAL_STARSCOURGE, TAL_RADAGON],
                         [], SPI_MIMIC,
                         "## Boss killer\n\n[Ruins Greatsword] avec [Lion's Claw] pour les mise a "
                         "mort rapides. Focus force + endurance.\n\nPas de subtilite, on cogne.")]),
     None),

    ("PoisonRose", "Status DPS Dex",
     "Application rapide de saignement + poison. Katana + arcs empoisonnes.",
     "pve", ["Dexterity", "Bleed", "Poison"], True,
     build_data([loadout("Main", stats(vig=40, mnd=20, end=30, str_=14, dex=60, arc=35),
                         {"head": HEAD_SAMURAI, "chest": CHEST_SAMURAI,
                          "hands": HANDS_SAMURAI, "legs": LEGS_SAMURAI},
                         {"right": MOONVEIL or UCHIGATANA, "left": ERDTREE_BOW,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         {"right": ASH_UNSHEATHE, "left": None,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         [TAL_MILLICENT, TAL_LORD_BLOOD],
                         [], None,
                         "## DPS statuts\n\n[Moonveil] pour la portee, arc empoisonne en support.")]),
     None),

    ("MelinaFinger", "Fingerprint Turtle Tank",
     "Tank pur en coop. Fingerprint Shield + Barricade Shield. Immobile mais indestructible.",
     "coop", ["Strength", "Boss", "Beginner"], True,
     build_data([loadout("Main", stats(vig=60, mnd=12, end=45, str_=60),
                         {"head": HEAD_ZAMOR, "chest": CHEST_ZAMOR,
                          "hands": HANDS_ZAMOR, "legs": LEGS_ZAMOR},
                         {"right": COLOSSAL, "left": FINGERPRINT_SHIELD,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         empty_ashes(),
                         [TAL_GREEN_TURTLE, TAL_ERDTREE_FAVOR, TAL_RADAGON],
                         [], SPI_TICHE,
                         "## Tank turtle\n\nGarde active a 100%, [Green Turtle Talisman] pour "
                         "l'endurance. Le [Fingerprint Shield] bloque tout.")]),
     None),

    ("Ranni_Witch", "Ranni Cosplay Moonlight",
     "Build Ranni : moonveil + Dark Moon Greatsword. RP casteuse glaciale.",
     "pve", ["Intelligence", "Sorceries"], True,
     build_data([loadout("Lvl 60", stats(vig=25, mnd=25, end=20, str_=10, dex=15, int_=50),
                         {"head": HEAD_ASTRO, "chest": CHEST_ASTRO,
                          "hands": HANDS_ASTRO, "legs": LEGS_ASTRO},
                         {"right": MOONVEIL, "left": ASTRO_STAFF,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         empty_ashes(),
                         [TAL_GRAVEN_MASS, TAL_MAGIC_SCORPION],
                         [SORC_COMET, SORC_ROCK_SLING],
                         SPI_MIMIC,
                         "## Ranni RP\n\nMoonlit sorceress. Focus glace + magie."),
                 loadout("Lvl 150", stats(vig=45, mnd=40, end=25, str_=14, dex=18, int_=80),
                         {"head": HEAD_ASTRO, "chest": CHEST_ASTRO,
                          "hands": HANDS_ASTRO, "legs": LEGS_ASTRO},
                         {"right": MOONVEIL, "left": ASTRO_STAFF,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         {"right": ASH_HOARFROST, "left": None,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         [TAL_GRAVEN_MASS, TAL_MAGIC_SCORPION, TAL_RADAGON, TAL_STARSCOURGE],
                         [SORC_COMET_AZUR, SORC_COMET, SORC_ROCK_SLING, SORC_GLINTSTONE],
                         SPI_TICHE,
                         "## Endgame\n\n[Comet Azur] cast avec [Terra Magica]. Un shot les boss.")], active=1),
     None),

    ("BeastClaw", "Beast Claw Roar Build",
     "Fervour dechainee, cris de bete + coups sauvages.",
     "pve", ["Strength", "Faith"], True,
     build_data([loadout("Main", stats(vig=50, mnd=20, end=30, str_=45, fai=40),
                         {"head": HEAD_LIONEL, "chest": CHEST_LIONEL,
                          "hands": HANDS_LIONEL, "legs": LEGS_LIONEL},
                         {"right": COLOSSAL, "left": ERDTREE_SEAL,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         {"right": ASH_LIONS_CLAW, "left": None,
                          "rightSecondary": [None, None], "leftSecondary": [None, None]},
                         [TAL_ERDTREE_FAVOR, TAL_RADAGON, TAL_STARSCOURGE],
                         [INC_GOLDEN_VOW, INC_FLAME_GRANT],
                         SPI_MIMIC,
                         "## Beast unleashed\n\nGolden Vow + Flame Strength puis Lion's Claw.")]),
     None),

    ("Tarnished_42", "Bleed Samurai (copy)",
     "Copie de mon Bleed Samurai pour tester une variante avec Ghiza.",
     "pve", ["Bleed", "Dexterity", "Arcane"], False,  # prive
     build_data([loadout("Test", stats(vig=45, end=25, str_=16, dex=50, arc=45),
                         {"head": HEAD_SAMURAI, "chest": CHEST_SAMURAI,
                          "hands": HANDS_SAMURAI, "legs": LEGS_SAMURAI},
                         {"right": GHIZA, "left": None,
                          "rightSecondary": [UCHIGATANA, None],
                          "leftSecondary": [None, None]},
                         {"right": ASH_BLOODY_SLASH, "left": None,
                          "rightSecondary": [ASH_UNSHEATHE, None],
                          "leftSecondary": [None, None]},
                         [TAL_LORD_BLOOD, TAL_MILLICENT],
                         [], SPI_MIMIC,
                         "Fork pour tester le [Ghiza's Wheel]")]),
     0),  # forked from index 0
]


# ── Likes cross-users ──
# Chaque tuple (liker_pseudo, build_index)
LIKES = [
    ("StarCaster", 0),  # StarCaster likes Bleed Samurai
    ("Goldmask", 0),
    ("Mohg_Lord", 0),
    ("BeastClaw", 0),
    ("PoisonRose", 0),
    ("MelinaFinger", 1),  # Astrologer
    ("Ranni_Witch", 1),
    ("Tarnished_42", 1),
    ("Goldmask", 1),
    ("Tarnished_42", 2),  # Faith Tank
    ("MelinaFinger", 2),
    ("Ranni_Witch", 3),  # Arcane Bleed
    ("Mohg_Lord", 4),  # Strength Colossal
    ("Tarnished_42", 4),
    ("StarCaster", 7),  # Ranni Cosplay
    ("Ranni_Witch", 7),
    ("Tarnished_42", 7),
    ("Mohg_Lord", 7),
    ("Goldmask", 8),  # Beast Claw
]


async def main():
    print(f"Connexion a la BDD...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    ph = PasswordHasher()

    async with Session() as db:
        # 1) Nettoyer les seed users existants
        pseudos = [u[0] for u in SEED_USERS]
        existing = (await db.execute(select(User).where(User.pseudo.in_(pseudos)))).scalars().all()
        if existing:
            print(f"  Nettoyage de {len(existing)} users existants...")
            for u in existing:
                await db.execute(delete(User).where(User.id == u.id))
            await db.commit()

        # 2) Creer les users
        print(f"Creation de {len(SEED_USERS)} users...")
        user_by_pseudo = {}
        for pseudo, email, pwd in SEED_USERS:
            hashed = ph.hash(pwd)
            u = User(
                pseudo=pseudo,
                email=email,
                password_hash=hashed,
                email_verified_at=datetime.now(timezone.utc),
            )
            db.add(u)
            await db.flush()
            user_by_pseudo[pseudo] = u
        await db.commit()
        print(f"  OK, {len(user_by_pseudo)} users crees.")

        # 3) Creer les builds
        print(f"Creation de {len(BUILDS)} builds...")
        created_builds = []
        for i, (author, name, desc, intent, tags, is_public, data, fork_from_idx) in enumerate(BUILDS):
            b = Build(
                user_id=user_by_pseudo[author].id,
                name=name,
                description=desc,
                data=data,
                is_public=is_public,
                intent=intent,
                tags=tags,
                forked_from_id=(created_builds[fork_from_idx].id if fork_from_idx is not None else None),
            )
            db.add(b)
            await db.flush()
            created_builds.append(b)
            print(f"  [{i}] {name} par {author} ({'public' if is_public else 'prive'})")
        await db.commit()

        # 4) Ajouter des likes
        print(f"Ajout de {len(LIKES)} likes...")
        for liker_pseudo, build_idx in LIKES:
            liker = user_by_pseudo.get(liker_pseudo)
            build = created_builds[build_idx]
            if liker is None or build is None:
                continue
            # skip si le liker == owner
            if liker.id == build.user_id:
                continue
            like = BuildLike(user_id=liker.id, build_id=build.id)
            db.add(like)
            build.like_count += 1
        await db.commit()

        # 5) Recap
        pub = sum(1 for b in created_builds if b.is_public)
        print(f"\nOK -- {len(user_by_pseudo)} users, {len(created_builds)} builds "
              f"({pub} publics), {len(LIKES)} likes.")
        print(f"\nComptes disponibles pour tester le login :")
        for pseudo, email, pwd in SEED_USERS[:3]:
            print(f"  {pseudo} / {pwd}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
