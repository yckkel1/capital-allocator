"""
Unit tests for database.py
Tests database connection, session management, and initialization
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabaseModule:
    """Test database module functions"""

    @patch('database.get_settings')
    @patch('database.create_engine')
    def test_engine_created_with_settings(self, mock_create_engine, mock_get_settings):
        """Test that engine is created with correct settings"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test:test@localhost:5432/testdb"
        mock_get_settings.return_value = mock_settings

        # Import fresh to trigger module-level code
        import importlib
        import database
        importlib.reload(database)

        # Verify create_engine was called
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "postgresql://test:test@localhost:5432/testdb"
        assert call_args[1]['pool_pre_ping'] is True
        assert call_args[1]['echo'] is True

    @patch('database.get_settings')
    @patch('database.create_engine')
    @patch('database.sessionmaker')
    def test_sessionlocal_configured(self, mock_sessionmaker, mock_create_engine, mock_get_settings):
        """Test that SessionLocal is configured correctly"""
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://test:test@localhost:5432/testdb"
        mock_get_settings.return_value = mock_settings
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        import importlib
        import database
        importlib.reload(database)

        # Verify sessionmaker was called with correct parameters
        mock_sessionmaker.assert_called_once_with(
            autocommit=False,
            autoflush=False,
            bind=mock_engine
        )


class TestGetDb:
    """Test get_db dependency function"""

    @patch('database.SessionLocal')
    def test_get_db_yields_session(self, mock_session_local):
        """Test that get_db yields a session and closes it"""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        from database import get_db

        # Get the generator
        gen = get_db()

        # Get the session
        session = next(gen)

        # Verify session was created
        mock_session_local.assert_called_once()
        assert session is mock_session

        # Close the generator (simulates end of request)
        try:
            next(gen)
        except StopIteration:
            pass

        # Verify session was closed
        mock_session.close.assert_called_once()

    @patch('database.SessionLocal')
    def test_get_db_closes_on_exception(self, mock_session_local):
        """Test that session is closed even on exception"""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        from database import get_db

        gen = get_db()
        session = next(gen)

        # Simulate exception in request handler
        with pytest.raises(ValueError):
            gen.throw(ValueError("Test exception"))

        # Session should still be closed
        mock_session.close.assert_called_once()

    @patch('database.SessionLocal')
    def test_get_db_as_context_manager(self, mock_session_local):
        """Test get_db can be used in a with statement pattern"""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        from database import get_db

        # Use the generator
        db_generator = get_db()
        db = next(db_generator)

        try:
            # Simulate using the database
            db.query("SELECT 1")
        finally:
            # Cleanup
            try:
                next(db_generator)
            except StopIteration:
                pass

        mock_session.close.assert_called_once()


class TestInitDb:
    """Test init_db function"""

    @patch('database.Base')
    @patch('database.engine')
    def test_init_db_creates_tables(self, mock_engine, mock_base):
        """Test that init_db creates all tables"""
        from database import init_db

        init_db()

        mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)

    @patch('database.Base')
    @patch('database.engine')
    def test_init_db_uses_correct_engine(self, mock_engine, mock_base):
        """Test that init_db uses the configured engine"""
        from database import init_db

        # Mock engine
        mock_engine_instance = Mock()
        mock_engine = mock_engine_instance

        init_db()

        # Verify create_all is called with the engine
        call_args = mock_base.metadata.create_all.call_args
        assert 'bind' in call_args[1]


class TestDatabaseIntegration:
    """Integration-style tests for database module"""

    @patch('database.get_settings')
    @patch('database.create_engine')
    @patch('database.sessionmaker')
    def test_full_database_setup(self, mock_sessionmaker, mock_create_engine, mock_get_settings):
        """Test complete database setup flow"""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.database_url = "postgresql://user:pass@host:5432/db"
        mock_get_settings.return_value = mock_settings

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_session_factory = Mock()
        mock_sessionmaker.return_value = mock_session_factory

        # Reload database module
        import importlib
        import database
        importlib.reload(database)

        # Verify complete setup
        mock_get_settings.assert_called_once()
        mock_create_engine.assert_called_once()
        mock_sessionmaker.assert_called_once()

    @patch('database.SessionLocal')
    def test_multiple_get_db_calls(self, mock_session_local):
        """Test that each get_db call creates a new session"""
        mock_session1 = MagicMock()
        mock_session2 = MagicMock()
        mock_session_local.side_effect = [mock_session1, mock_session2]

        from database import get_db

        # First call
        gen1 = get_db()
        session1 = next(gen1)

        # Second call
        gen2 = get_db()
        session2 = next(gen2)

        # Should be different sessions
        assert session1 is not session2
        assert session1 is mock_session1
        assert session2 is mock_session2

        # Cleanup
        try:
            next(gen1)
        except StopIteration:
            pass
        try:
            next(gen2)
        except StopIteration:
            pass

        # Both should be closed
        mock_session1.close.assert_called_once()
        mock_session2.close.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
