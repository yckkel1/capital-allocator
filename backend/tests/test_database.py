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

    def test_database_module_has_engine(self):
        """Test that database module exposes engine"""
        from database import engine
        assert engine is not None

    def test_database_module_has_session_local(self):
        """Test that database module exposes SessionLocal"""
        from database import SessionLocal
        assert SessionLocal is not None

    def test_database_module_has_base(self):
        """Test that database module exposes Base"""
        from database import Base
        assert Base is not None

    def test_database_module_has_get_db(self):
        """Test that database module exposes get_db"""
        from database import get_db
        assert callable(get_db)

    def test_database_module_has_init_db(self):
        """Test that database module exposes init_db"""
        from database import init_db
        assert callable(init_db)


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
