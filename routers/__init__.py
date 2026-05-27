from .auth import router as auth_router
from .builds import router as builds_router
from .users import router as users_router
from .ammos import router as ammos_router
from .armors import router as armors_router
from .ashes import router as ashes_router
from .bosses import router as bosses_router
from .classes import router as classes_router
from .creatures import router as creatures_router
from .incantations import router as incantations_router
from .items import router as items_router
from .locations import router as locations_router
from .npcs import router as npcs_router
from .shields import router as shields_router
from .sorceries import router as sorceries_router
from .spirits import router as spirits_router
from .talismans import router as talismans_router
from .weapons import router as weapons_router

all_routers = [
    (auth_router, "/auth", ["Auth"]),
    (builds_router, "/builds", ["Builds"]),
    (users_router, "/users", ["Users"]),
    (ammos_router, "/ammos", ["Ammos"]),
    (armors_router, "/armors", ["Armors"]),
    (ashes_router, "/ashes", ["Ashes"]),
    (bosses_router, "/bosses", ["Bosses"]),
    (classes_router, "/classes", ["Classes"]),
    (creatures_router, "/creatures", ["Creatures"]),
    (incantations_router, "/incantations", ["Incantations"]),
    (items_router, "/items", ["Items"]),
    (locations_router, "/locations", ["Locations"]),
    (npcs_router, "/npcs", ["NPCs"]),
    (shields_router, "/shields", ["Shields"]),
    (sorceries_router, "/sorceries", ["Sorceries"]),
    (spirits_router, "/spirits", ["Spirits"]),
    (talismans_router, "/talismans", ["Talismans"]),
    (weapons_router, "/weapons", ["Weapons"]),
]
