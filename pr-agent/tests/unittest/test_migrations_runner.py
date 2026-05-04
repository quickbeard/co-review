"""Unit tests for Alembic bootstrap (`migrations_runner`) and `init_database` wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from pr_agent.db import database
from pr_agent.db import migrations_runner


@pytest.fixture
def mock_engine() -> MagicMock:
    return MagicMock()


def test_init_database_passes_engine_url_and_logger():
    log = MagicMock()
    with patch.object(migrations_runner, "run_migrations") as mock_run:
        database.init_database(logger=log)

    mock_run.assert_called_once_with(
        database.engine,
        database.DATABASE_URL,
        logger=log,
    )


def test_init_database_accepts_default_logger():
    with patch.object(migrations_runner, "run_migrations") as mock_run:
        database.init_database()

    mock_run.assert_called_once_with(
        database.engine,
        database.DATABASE_URL,
        logger=None,
    )


def test_run_migrations_greenfield_create_all_and_stamp_head(mock_engine):
    inspector = MagicMock()
    inspector.get_table_names.return_value = []
    cfg = MagicMock()

    with patch.object(migrations_runner, "inspect", return_value=inspector):
        with patch.object(
            migrations_runner, "_build_alembic_config", return_value=cfg
        ):
            with patch.object(migrations_runner.command, "stamp") as mock_stamp:
                with patch.object(migrations_runner.command, "upgrade") as mock_upgrade:
                    with patch.object(
                        migrations_runner.SQLModel.metadata, "create_all"
                    ) as mock_create_all:
                        migrations_runner.run_migrations(
                            mock_engine, "postgresql://localhost/db"
                        )

    mock_create_all.assert_called_once_with(mock_engine)
    mock_stamp.assert_called_once_with(cfg, "head")
    mock_upgrade.assert_not_called()


def test_run_migrations_legacy_stamps_baseline_then_upgrades(mock_engine):
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["git_providers"]
    cfg = MagicMock()

    with patch.object(migrations_runner, "inspect", return_value=inspector):
        with patch.object(
            migrations_runner, "_build_alembic_config", return_value=cfg
        ):
            with patch.object(migrations_runner.command, "stamp") as mock_stamp:
                with patch.object(migrations_runner.command, "upgrade") as mock_upgrade:
                    with patch.object(
                        migrations_runner.SQLModel.metadata, "create_all"
                    ) as mock_create_all:
                        migrations_runner.run_migrations(
                            mock_engine, "postgresql://localhost/db"
                        )

    mock_create_all.assert_not_called()
    mock_stamp.assert_called_once_with(cfg, migrations_runner.BASELINE_REVISION)
    mock_upgrade.assert_called_once_with(cfg, "head")


def test_run_migrations_normal_only_upgrades(mock_engine):
    inspector = MagicMock()
    inspector.get_table_names.return_value = ["git_providers", "alembic_version"]
    cfg = MagicMock()

    with patch.object(migrations_runner, "inspect", return_value=inspector):
        with patch.object(
            migrations_runner, "_build_alembic_config", return_value=cfg
        ):
            with patch.object(migrations_runner.command, "stamp") as mock_stamp:
                with patch.object(migrations_runner.command, "upgrade") as mock_upgrade:
                    with patch.object(
                        migrations_runner.SQLModel.metadata, "create_all"
                    ) as mock_create_all:
                        migrations_runner.run_migrations(
                            mock_engine, "postgresql://localhost/db"
                        )

    mock_create_all.assert_not_called()
    mock_stamp.assert_not_called()
    mock_upgrade.assert_called_once_with(cfg, "head")


def test_build_alembic_config_sets_script_location_and_url():
    cfg = migrations_runner._build_alembic_config("postgresql://user:pass@db/app")
    assert cfg.get_main_option("sqlalchemy.url") == "postgresql://user:pass@db/app"
    assert cfg.get_main_option("script_location") == str(
        migrations_runner._MIGRATIONS_DIR
    )
