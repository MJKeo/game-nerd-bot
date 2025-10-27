from pydantic import BaseModel

class GameDescriptionResponse(BaseModel):
    name: str
    game_id: int # RAWG internal ID
    description: str
    def __str__(self) -> str:
        """Render the game description in a readable format."""

        return (
            f"Name: {self.name}\n"
            f"ID: {self.game_id}\n"
            f"Description: \"{self.description}\""
        )

    @classmethod
    def create_description_response_from_json(
        cls, payload: dict
    ) -> "GameDescriptionResponse":
        """Create a GameDescriptionResponse from the RAWG API payload."""
        # Build the response, coercing missing or null fields to safe defaults.
        return cls(
            name=payload.get("name") or "",
            game_id=payload.get("id") or 0,
            description=payload.get("description") or "",
        )



class GameDetailsResponse(BaseModel):
    name: str
    game_id: int # RAWG internal ID
    average_playtime: int # how long to beat on average (hours)
    platforms: list[str] # list of platforms the game is available on
    stores: list[str] # list of stores the game is available on
    genres: list[str] # list of genres the game belongs to
    released: str # date of release (YYYY-MM-DD)
    metacritic_score: int | None # metacritic score out of 100
    esrb_rating: str | None # ESRB rating

    def __str__(self) -> str:
        """Render the game details in a human-readable format."""

        # Format platforms, stores, and genres as comma-separated strings for readability.
        formatted_platforms = ", ".join(self.platforms) if self.platforms else "N/A"
        formatted_stores = ", ".join(self.stores) if self.stores else "N/A"
        formatted_genres = ", ".join(self.genres) if self.genres else "N/A"

        # Provide sensible fallbacks for optional fields.
        formatted_metacritic = str(self.metacritic_score) if self.metacritic_score is not None else "N/A"
        formatted_esrb = self.esrb_rating if self.esrb_rating else "N/A"

        # Assemble the multi-line string representation with explicit labels.
        return (
            f"Name: {self.name}\n"
            f"ID: {self.game_id}\n"
            f"Average Playtime (hours): {self.average_playtime}\n"
            f"Platforms: {formatted_platforms}\n"
            f"Stores: {formatted_stores}\n"
            f"Genres: {formatted_genres}\n"
            f"Release Date: {self.released or 'N/A'}\n"
            f"Metacritic Rating: {formatted_metacritic}/100\n"
            f"Maturity Rating: {formatted_esrb}"
        )

    @classmethod
    def create_game_objects_from_search_results(
        cls, search_results: list[dict]
    ) -> list["GameDetailsResponse"]:
        """Convert RAWG search result dictionaries into simplified game objects."""

        # Handle missing or empty search results gracefully.
        if not search_results:
            return []

        # Prepare a container to hold the parsed GameDetailsResponse instances.
        parsed_games: list[GameDetailsResponse] = []

        for result in search_results:
            # Extract platform names from nested platform dictionaries.
            platform_entries = result.get("platforms") or []
            platform_names = [
                platform_entry.get("platform", {}).get("name")
                for platform_entry in platform_entries
                if platform_entry.get("platform", {}).get("name")
            ]

            # Extract store names from nested store dictionaries.
            store_entries = result.get("stores") or []
            store_names = [
                store_entry.get("store", {}).get("name")
                for store_entry in store_entries
                if store_entry.get("store", {}).get("name")
            ]

            # Extract genre names from the genre dictionaries.
            genre_entries = result.get("genres") or []
            genre_names = [
                genre_entry.get("name")
                for genre_entry in genre_entries
                if genre_entry.get("name")
            ]

            # Pull the localized ESRB rating when available.
            esrb_rating_name = None
            esrb_rating_data = result.get("esrb_rating")
            if isinstance(esrb_rating_data, dict):
                esrb_rating_name = esrb_rating_data.get("name_en")

            # Populate the response object with normalized values and sensible defaults.
            game_details = cls(
                name=result.get("name") or "",
                game_id=result.get("id") or 0,
                average_playtime=int(result.get("playtime") or 0),
                platforms=platform_names,
                stores=store_names,
                genres=genre_names,
                released=result.get("released") or "",
                metacritic_score=result.get("metacritic"),
                esrb_rating=esrb_rating_name,
            )

            # Accumulate the parsed game details for the final response.
            parsed_games.append(game_details)

        # Return the fully constructed list of game detail objects to the caller.
        return parsed_games