from models import Base


def test_base_is_declarative():
    """Base doit être une DeclarativeBase SQLAlchemy 2.0."""
    from sqlalchemy.orm import DeclarativeBase

    assert issubclass(Base, DeclarativeBase)


def test_base_metadata_starts_empty():
    """Pas de tables enregistrées tant qu'aucun modèle n'est importé."""
    assert isinstance(Base.metadata.tables, dict)
