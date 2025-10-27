"""Database abstraction that manages external game service integrations."""

from __future__ import annotations

from dotenv import load_dotenv
import os
import random
import requests
import time
from typing import Any


class Database:
    """Coordinate external API credentials and data lookups for NerdBot."""

    # ====================
    #      Constants
    # ====================

    RAWG_GAMES_API_BASE_URL = "https://api.rawg.io/api/games"

    # ====================
    #    Initialization
    # ====================

    def __init__(self) -> None:
        """Load environment configuration and cache credential values."""

        # Resolve the environment file so credential updates persist across runs.
        load_dotenv(override=True)

        # Store configuration details for downstream API calls.
        self.rawg_api_key = os.getenv("RAWG_API_KEY")

        # Maintain a shared HTTP session to reuse TCP connections for outbound calls.
        self.http_session = requests.Session()

    # ====================
    #     Helper Methods
    # ====================

    def _make_request_with_retry(
        self, url: str, params: dict[str, Any], max_retries: int = 3, base_delay: float = 1.0
    ) -> dict[str, Any]:
        """
        Execute an HTTP GET request with exponential backoff retry logic for transient failures.
        
        Uses exponential backoff with jitter to prevent overwhelming the API during outages
        and to avoid thundering herd problems when multiple clients retry simultaneously.
        
        Args:
            url: The URL to send the GET request to
            params: Query parameters to include in the request
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)
                       Actual delays will be: base_delay, base_delay*2, base_delay*4, etc.
        
        Returns:
            A dictionary with 'success' boolean and either 'results' or 'error' key
        """
        last_error = None
        
        # Attempt the request up to max_retries times
        for attempt in range(max_retries):
            try:
                # Execute the GET request with timeout settings
                response = self.http_session.get(url, params=params, timeout=(3, 10))
                response.raise_for_status()
                return {"success": True, "results": response.json()}
            except requests.RequestException as error:
                last_error = error
                
                # Log the retry attempt unless this is the final attempt
                if attempt < max_retries - 1:
                    # Calculate exponential backoff delay: base_delay * (2 ^ attempt)
                    # Add jitter (random 0-100ms) to prevent thundering herd
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    
                    print(f"Request failed (attempt {attempt + 1}/{max_retries}): {error}")
                    print(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    # Final attempt failed - log and return error
                    print(f"Request failed after {max_retries} attempts: {error}")
        
        # All retries exhausted - return the last error encountered
        return {"success": False, "error": str(last_error)}

    # ====================
    #     Game Data
    # ====================

    def get_game_details(self, game_id: int) -> dict[str, Any]:
        """Get the details of a game by its ID."""

        # Prepare query parameters for the RAWG game details endpoint.
        params = {
            "key": self.rawg_api_key,
            "exclude_additions": True,
        }

        # Execute the request with automatic retry logic
        return self._make_request_with_retry(
            url=f"{self.RAWG_GAMES_API_BASE_URL}/{game_id}",
            params=params
        )


    def search_game_by_name(self, game_name: str) -> dict[str, Any]:
        """Search the RAWG catalogue for games matching the provided name."""

        # Prepare query parameters for the RAWG search endpoint.
        search_params = {
            "key": self.rawg_api_key,
            "search": game_name,
            "exclude_additions": True,
        }

        # Execute the request with automatic retry logic
        return self._make_request_with_retry(
            url=self.RAWG_GAMES_API_BASE_URL,
            params=search_params
        )

    def find_multiple_games_by_conditions(
        self,
        release_date_lower_bound: str,
        release_date_upper_bound: str,
        metacritic_lower_bound: int,
        metacritic_upper_bound: int,
        page_size: int = 5,
        title: str | None = None,
        parent_platform_ids: list[int] | None = None,
        platform_ids: list[int] | None = None,
        store_ids: list[int] | None = None,
        developers: list[str] | None = None,
        publishers: list[str] | None = None,
        genres: list[str] | None = None,
        tags: list[str] | None = None,
        ordering: str | None = None,
    ) -> dict[str, Any]:
        # Prepare query parameters for the RAWG search endpoint.
        search_params = {
            "key": self.rawg_api_key,
            "page_size": page_size,
            "dates": f"{release_date_lower_bound},{release_date_upper_bound}",
            "metacritic": f"{metacritic_lower_bound},{metacritic_upper_bound}",
            "exclude_additions": True,
        }

        if title is not None:
            search_params["search"] = title

        if parent_platform_ids:
            search_params["parent_platforms"] = ",".join(str(id) for id in parent_platform_ids)

        if platform_ids:
            search_params["platforms"] = ",".join(str(id) for id in platform_ids)

        if store_ids:
            search_params["stores"] = ",".join(str(id) for id in store_ids)

        if developers:
            search_params["developers"] = ",".join(developers)

        if publishers:
            search_params["publishers"] = ",".join(publishers)

        if genres:
            search_params["genres"] = ",".join(genres)

        if tags:
            search_params["tags"] = ",".join(tags)

        if ordering is not None:
            search_params["ordering"] = ordering

        # Execute the request with automatic retry logic
        result = self._make_request_with_retry(
            url=self.RAWG_GAMES_API_BASE_URL,
            params=search_params
        )
        return result

        return result

# Instantiate a shared database object for reuse across the application.
DATABASE = Database()  # Shared singleton exposing configuration, authentication, and query helpers.

__all__ = ["DATABASE"]