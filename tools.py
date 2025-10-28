from typing import Any

import datetime

from classes import GameDetailsResponse, GameDescriptionResponse
from constants import (
    DEVELOPER_SLUGS,
    GENRE_SLUGS,
    ORDERINGS,
    PARENT_PLATFORM_SLUG_TO_ID,
    PLATFORM_SLUG_TO_ID,
    PUBLISHER_SLUGS,
    STORE_SLUG_TO_ID,
    TAG_SLUGS,
)
from database import DATABASE

# ====================
#    ID Conversions
# ====================

def _get_platform_ids(slugs: list[str]) -> list[int]:
    """Convert platform slugs into RAWG platform IDs, excluding unknown entries."""

    # Accumulate the translated platform IDs for the provided slugs.
    platform_ids: list[int] = []

    # Iterate through each slug to map it using the canonical dictionary.
    for slug in slugs:
        # Fetch the platform ID when the slug is recognized.
        platform_id = PLATFORM_SLUG_TO_ID.get(slug)

        # Append the ID only when it exists in the mapping.
        if platform_id is not None:
            platform_ids.append(platform_id)

    return platform_ids

def _get_parent_platform_ids(slugs: list[str]) -> list[int]:
    """Convert parent platform slugs into RAWG parent platform IDs."""

    parent_ids: list[int] = []

    for slug in slugs:
        parent_id = PARENT_PLATFORM_SLUG_TO_ID.get(slug)
        if parent_id is not None:
            parent_ids.append(parent_id)

    return parent_ids


def _get_store_ids(slugs: list[str]) -> list[int]:
    """Convert store slugs into RAWG store IDs, ignoring unknown entries."""

    store_ids: list[int] = []

    for slug in slugs:
        store_id = STORE_SLUG_TO_ID.get(slug)
        if store_id is not None:
            store_ids.append(store_id)

    return store_ids

def _normalize_list_param(param: list[str] | str | None) -> list[str]:
    """Convert a parameter to a list, handling None, single items, and existing lists."""
    if param is None:
        return []
    if isinstance(param, list):
        return param
    return [param]

# ====================
#    Helpers Tools
# ====================

def get_current_date() -> str:
    """Get the current date in the format YYYY-MM-DD."""
    response = f"Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}"
    return {"success": True, "results": response}

# ====================
#    Database Fetch
# ====================

def get_game_description(game_id: int) -> dict[str, Any]:
    """Fetch the description of a game by its ID."""
    # Fetch the RAWG game detail payload for the provided ID.
    db_response = DATABASE.get_game_details(game_id)
    rawg_payload = db_response.get("results")

    if not db_response.get("success") or not rawg_payload:
        # Return a structured failure response when the RAWG payload is empty or missing.
        error_message = db_response.get("error", "An unknown error occurred while fetching from the database.")
        return {
            "success": False,
            "failure_reason": f"Database error: {error_message}",
        }

    try:
        # Attempt to build the description response from the JSON payload.
        response_object = GameDescriptionResponse.create_description_response_from_json(rawg_payload)
        # Convert the pydantic model into a plain dictionary so it is JSON serializable.
        response_payload = response_object.model_dump()
        return {"success": True, "results": response_payload}
    except Exception as error:  # Broad except to handle unexpected payload issues.
        return {"success": False, "failure_reason": f"Parsing error: {error}"}

def find_game_by_name(game_name: str) -> dict[str, Any]:
    """Fetch detailed RAWG metadata for the requested game."""
    # Use the RAWG API to find the game by name.
    db_response = DATABASE.search_game_by_name(game_name)
    rawg_payload = (db_response or {}).get("results", {}).get("results")

    if not db_response.get("success") or not rawg_payload:
        # Report the absence of RAWG search data as a structured failure.
        error_message = db_response.get("error", "An unknown error occurred while fetching from the database.")
        return {
            "success": False,
            "failure_reason": f"Database error: {error_message}",
        }

    # Extract the list of search results from the RAWG payload.

    # Convert the FIRST few results into GameDetailsResponse objects.
    game_objects = GameDetailsResponse.create_game_objects_from_search_results(rawg_payload)

    if not game_objects:
        # Notify the caller that no results could be parsed.
        return {
            "success": False,
            "failure_reason": "Failed to parse database results.",
        }

    # Return the first 3 parsed GameDetailsResponses as the primary matches.
    serialized_games = [game.model_dump() for game in game_objects[:3]]
    return {"success": True, "results": serialized_games}

def find_multiple_games(
    num_results: int = 5,
    title: str | None = None,
    parent_platforms: list[str] | None = None,
    platforms: list[str] | None = None,
    stores: list[str] | None = None,
    developers: list[str] | None = None,
    publishers: list[str] | None = None,
    genres: list[str] | None = None,
    tags: list[str] | None = None,
    release_date_lower_bound: str | None = None,
    release_date_upper_bound: str | None = None,
    metacritic_lower_bound: int | None = None,
    metacritic_upper_bound: int | None = None,
    ordering: str | None = None,
) -> dict[str, Any]:
    """Uses RAWG API to search for multiple games based on the provided conditions."""

    # Normalize all list parameters in one clean step
    parent_platforms = _normalize_list_param(parent_platforms)
    platforms = _normalize_list_param(platforms)
    stores = _normalize_list_param(stores)
    developers = _normalize_list_param(developers)
    publishers = _normalize_list_param(publishers)
    genres = _normalize_list_param(genres)
    tags = _normalize_list_param(tags)

    # Invoke the database to retrieve the raw results.
    db_response = DATABASE.find_multiple_games_by_conditions(
        page_size=num_results,
        title=title,
        parent_platform_ids=_get_parent_platform_ids(parent_platforms),
        platform_ids=_get_platform_ids(platforms),
        store_ids=_get_store_ids(stores),
        developers=developers,
        publishers=publishers,
        genres=genres,
        tags=tags,
        release_date_lower_bound=release_date_lower_bound or "1800-01-01",
        release_date_upper_bound=release_date_upper_bound or "3000-01-01",
        metacritic_lower_bound=metacritic_lower_bound if metacritic_lower_bound is not None else 0,
        metacritic_upper_bound=metacritic_upper_bound if metacritic_upper_bound is not None else 100,
        ordering=ordering,
    )
    rawg_payload = (db_response or {}).get("results", {}).get("results")

    if not db_response.get("success") or not rawg_payload:
        error_message = db_response.get("error", "Unknown database error.")
        return {
            "success": False,
            "failure_reason": f"Database error: {error_message}",
        }


    # Convert the FIRST few results into GameDetailsResponse objects.
    game_objects = GameDetailsResponse.create_game_objects_from_search_results(rawg_payload)

    if not game_objects:
        return {
            "success": False,
            "failure_reason": "Failed to parse database results.",
        }

    # Return all parsed GameDetailsResponse objects as serializable dictionaries.
    serialized_games = [game.model_dump() for game in game_objects]
    return {"success": True, "results": serialized_games}

# =====================
#   Tool Declarations
# =====================

VIDEO_GAME_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Get the current date in the format YYYY-MM-DD. Use this when you need to calculate date ranges for filtering games by relative dates (e.g., 'games from last year', 'games released in the past 6 months').",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_game_by_name",
            "description": "Search for a specific game by name and fetch its metadata (title, release date, rating, platforms, etc.). Use this when the user asks about a particular game by name and you need current data about it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_name": {
                        "type": "string",
                        "description": "Exact or partial game title to search for. The game returned will be the one whose name/title best matches this value.",
                    }
                },
                "required": ["game_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_multiple_games",
            "description": "Search for multiple games using various filters (platform, genre, tags, ratings, release dates, etc.). Use this when the user explicitly asks for game recommendations or lists matching specific criteria (e.g., 'best PS4 games', 'top-rated RPGs', 'indie games from 2023').",
            "parameters": {
                "type": "object",
                "properties": {
                    "num_results": {
                        "type": "integer",
                        "description": "Maximum number of games to return. Default 5.",
                        "minimum": 1,
                        "maximum": 25,
                    },
                    "title": {
                        "type": "string",
                        "description": "Filters results to games with a title that contain or closely matches this value.",
                    },
                    "parent_platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "enum": sorted(PARENT_PLATFORM_SLUG_TO_ID.keys()),
                        "description": "Filters results to games that can be played on at least one of the provided parent platforms.",
                    },
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "enum": sorted(PLATFORM_SLUG_TO_ID.keys()),
                        "description": "Filters results to games that can be played on at least one of the provided platforms.",
                    },
                    "stores": {
                        "type": "array",
                        "items": {"type": "string"},
                        "enum": sorted(STORE_SLUG_TO_ID.keys()),
                        "description": "Filters results to games that are available for purchase from at least one of the provided stores.",
                    },
                    "developers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "enum": DEVELOPER_SLUGS,
                        "description": "Filters results to games that were developed by at least one of the provided developers.",
                    },
                    "publishers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "enum": PUBLISHER_SLUGS,
                        "description": "Filters results to games that were published by at least one of the provided publishers.",
                    },
                    "genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "enum": GENRE_SLUGS,
                        "description": "Filters results to games that fall into at least one of the provided genres.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "enum": TAG_SLUGS,
                        "description": "Filters results to games that contain at least one of the provided tags.",
                    },
                    "release_date_lower_bound": {
                        "type": "string",
                        "format": "date",
                        "description": "Filters results to games that were released on or AFTER this date. Only provide if you need games explicitly released AFTER a certain date (ex. \"show me games released 6 months ago\", \"show me games released in the 80s\").",
                    },
                    "release_date_upper_bound": {
                        "type": "string",
                        "format": "date",
                        "description": "Filters results to games that were released on or BEFORE this date. Only provide if you need games explicitly released BEFORE a certain date (ex. \"show me games released last year\", \"show me games released in the 2000s\").",
                    },
                    "metacritic_lower_bound": {
                        "type": "integer",
                        "description": "Filters results to games that have a metacritic score of AT LEAST this value. Only provide if you explicitly need games with higher metacritic scores than a certain value.",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "metacritic_upper_bound": {
                        "type": "integer",
                        "description": "Filters results to games that have a metacritic score of AT MOST this value. Only provide if you explicitly need games with lower metacritic scores than a certain value.",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "ordering": {
                        "type": "string",
                        "enum": ORDERINGS,
                        "description": "What attribute to sort the resulting list of games by. Values prefixed with '-' are sorted in descending order. Otherwise it is ascending order.",
                    },
                },
            },
        },
    },
]