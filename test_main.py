import pytest
from fastapi.testclient import TestClient
from main import app
from core import datasets, filter_dataframe
import pandas as pd


client = TestClient(app)


# ==================== Tests Root ====================
class TestRoot:
    def test_root_endpoint(self):
        """Test du point d'entrée de l'API."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        assert "documentation" in data


# ==================== Tests Weapons ====================
class TestWeapons:
    def test_get_all_weapons(self):
        """Test de récupération de toutes les armes."""
        response = client.get("/weapons")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_weapons_with_filter(self):
        """Test de récupération des armes avec filtre."""
        response = client.get("/weapons?category=Axe")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for weapon in data:
            assert "Axe" in weapon.get("category", "")

    def test_get_weapon_by_id_not_found(self):
        """Test de récupération d'une arme inexistante."""
        response = client.get("/weapons/id_inexistant")
        assert response.status_code == 404


# ==================== Tests Armors ====================
class TestArmors:
    def test_get_all_armors(self):
        """Test de récupération de toutes les armures."""
        response = client.get("/armors")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_armor_by_id_not_found(self):
        """Test de récupération d'une armure inexistante."""
        response = client.get("/armors/id_inexistant")
        assert response.status_code == 404


# ==================== Tests Bosses ====================
class TestBosses:
    def test_get_all_bosses(self):
        """Test de récupération de tous les boss."""
        response = client.get("/bosses")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_boss_by_id_not_found(self):
        """Test de récupération d'un boss inexistant."""
        response = client.get("/bosses/id_inexistant")
        assert response.status_code == 404


# ==================== Tests Classes ====================
class TestClasses:
    def test_get_all_classes(self):
        """Test de récupération de toutes les classes."""
        response = client.get("/classes")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== Tests Items ====================
class TestItems:
    def test_get_all_items(self):
        """Test de récupération de tous les items."""
        response = client.get("/items")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== Tests Locations ====================
class TestLocations:
    def test_get_all_locations(self):
        """Test de récupération de toutes les localisations."""
        response = client.get("/locations")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== Tests NPCs ====================
class TestNPCs:
    def test_get_all_npcs(self):
        """Test de récupération de tous les NPCs."""
        response = client.get("/npcs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== Tests filter_dataframe ====================
class TestFilterDataframe:
    def test_filter_with_no_filters(self):
        """Test du filtrage sans filtre."""
        df = pd.DataFrame({"name": ["Test1", "Test2"], "type": ["A", "B"]})
        result = filter_dataframe(df, {"name": None, "type": None})
        assert len(result) == 2

    def test_filter_with_name_filter(self):
        """Test du filtrage par nom."""
        df = pd.DataFrame({"name": ["Sword", "Shield"], "type": ["Weapon", "Armor"]})
        result = filter_dataframe(df, {"name": "Sword", "type": None})
        assert len(result) == 1
        assert result[0]["name"] == "Sword"

    def test_filter_case_insensitive(self):
        """Test que le filtrage est insensible à la casse."""
        df = pd.DataFrame({"name": ["SWORD", "Shield"], "type": ["Weapon", "Armor"]})
        result = filter_dataframe(df, {"name": "sword", "type": None})
        assert len(result) == 1

    def test_filter_partial_match(self):
        """Test que le filtrage fonctionne avec correspondance partielle."""
        df = pd.DataFrame({"name": ["Long Sword", "Short Sword", "Axe"], "type": ["A", "B", "C"]})
        result = filter_dataframe(df, {"name": "Sword", "type": None})
        assert len(result) == 2
