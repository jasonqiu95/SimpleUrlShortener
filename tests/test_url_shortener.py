import unittest
from url_shortener import app
from unittest.mock import patch, MagicMock


class URLShortenerTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up the test client once for all tests."""
        app.config['TESTING'] = True
        cls.client = app.test_client()
    
    @patch('url_shortener.get_db_connection')  # Mock the Redis cache for isolated testing
    @patch('url_shortener.get_cache_connection')  # Mock the PostgreSQL connection
    def test_shorten_url(self, mock_get_cache_connection, mock_get_db_connection):
        """Test creating a shortened URL."""
        # Mock the database insert operation
        mock_db_conn = MagicMock()
        cursor_mock = MagicMock()
        cursor_mock.fetchone.return_value = None  # Simulate no existing short_url
        cursor_mock.execute.return_value = None  # Simulate successful insert
        mock_db_conn.cursor.return_value.__enter__.return_value = cursor_mock
        mock_get_db_connection.return_value = mock_db_conn
        
        # Mock the Redis cache
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Simulate no cache hit
        mock_get_cache_connection.return_value = mock_cache
        
        # Sample URL data
        original_url = "https://example.com"
        response = self.client.post("/shorten", json={"url": original_url})
        
        # Check the response status and structure
        self.assertEqual(response.status_code, 200)
        self.assertIn("short_url", response.json)

        # Verify Redis and database insertion attempts
        mock_cache.set.assert_called_once()
        self.assertEqual(cursor_mock.execute.call_count, 2)

    @patch('url_shortener.get_db_connection')  # Mock the Redis cache for isolated testing
    @patch('url_shortener.get_cache_connection')  # Mock the PostgreSQL connection
    def test_redirect_to_original(self, mock_get_cache_connection, mock_get_db_connection):
        """Test redirecting to the original URL from a shortened code."""
        # Mock the Redis cache and database fetch operations
        short_url = "abc123"
        original_url = "https://example.com"

        mock_db_conn = MagicMock()
        mock_get_db_connection.return_value = mock_db_conn
        
        # Mock the Redis cache
        mock_cache = MagicMock()
        mock_get_cache_connection.return_value = mock_cache
        
        # Case 1: URL exists in cache
        mock_cache.get.return_value = original_url.encode('utf-8')  # Cache returns the original URL
        response = self.client.get(f"/{short_url}")
        self.assertEqual(response.status_code, 302)  # Check for redirection
        self.assertEqual(response.location, original_url)  # Check the redirect URL

        cursor_mock = mock_db_conn.cursor.return_value.__enter__.return_value
        # Case 2: URL not in cache but exists in database
        mock_cache.get.return_value = None  # No cache hit
        cursor_mock.fetchone.return_value = (original_url,)  # Database returns the original URL
        response = self.client.get(f"/{short_url}")
        self.assertEqual(response.status_code, 302)  # Check for redirection
        self.assertEqual(response.location, original_url)  # Check the redirect URL

        # Case 3: URL does not exist in both cache and database
        cursor_mock.fetchone.return_value = None  # Database returns no result
        response = self.client.get(f"/{short_url}")
        self.assertEqual(response.status_code, 404)  # Should return 404 for missing URL

    if __name__ == '__main__':
        unittest.main()