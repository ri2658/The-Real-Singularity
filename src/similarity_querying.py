import os
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple


TREFLE_BASE_URL = "https://trefle.io/api/v1"


class TrefleClient:
    def __init__(self, token: Optional[str] = None, base_url: str = TREFLE_BASE_URL):
        """
        Initialize a Trefle API client.
        
        Args:
            token: Trefle API token. If not provided, reads from TREFLE_TOKEN environment variable.
            base_url: Base URL for Trefle API. Defaults to TREFLE_BASE_URL.
        
        Raises:
            ValueError: If no token is provided and TREFLE_TOKEN is not set.
        
        Example:
            >>> client = TrefleClient(token="your_token_here")
            >>> # or rely on TREFLE_TOKEN env var:
            >>> client = TrefleClient()
        """
        self.token = token or os.getenv("TREFLE_TOKEN")
        self.base_url = base_url.rstrip("/")

        if not self.token:
            raise ValueError("Missing Trefle token. Pass token=... or set TREFLE_TOKEN.")

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a single GET request to the Trefle API.
        
        Args:
            path: API endpoint path (e.g., "/plants/search").
            params: Query parameters as a dictionary.
        
        Returns:
            Parsed JSON response. On error, returns dict with error=True and message.
        
        Example:
            >>> client = TrefleClient(token="test_token")
            >>> response = client.get("/plants/search", {"q": "oak", "limit": 5})
            >>> plants = response.get("data", [])
        """
        params = dict(params or {})
        params["token"] = self.token

        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{self.base_url}{path}?{query}"

        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return json_loads_safe(response.read().decode("utf-8"))
        except Exception as e:
            return {
                "data": None,
                "error": True,
                "message": str(e),
                "url": url,
            }

    def post(
        self,
        path: str,
        body: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request to the Trefle API with a JSON body.
        """
        params = dict(params or {})
        params["token"] = self.token

        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{self.base_url}{path}?{query}"
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                parsed = json_loads_safe(response.read().decode("utf-8"))
                parsed["_http_status"] = getattr(response, "status", 200)
                return parsed
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            parsed = json_loads_safe(raw) if raw.strip().startswith("{") else {"message": raw}
            return {
                "data": None,
                "error": True,
                "message": parsed.get("message") or parsed.get("error") or raw or str(e),
                "details": parsed,
                "status": e.code,
                "url": url,
            }
        except Exception as e:
            return {
                "data": None,
                "error": True,
                "message": str(e),
                "url": url,
            }

    def paginated_get(
        self,
        path: str,
        max_results: int = 20,
        params: Optional[Dict[str, Any]] = None,
        image_only: bool = True,
        exclude_ids: Optional[Set[str]] = None,
        delay_seconds: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Paginate through Trefle API results until max_results is reached.
        
        Args:
            path: API endpoint path.
            max_results: Maximum number of results to retrieve. Defaults to 20.
            params: Query parameters. Defaults to None.
            image_only: If True, skip plants without images. Defaults to True.
            exclude_ids: Set of plant IDs to skip. Defaults to None.
            delay_seconds: Sleep duration between requests. Defaults to 0.0.
        
        Returns:
            List of normalized plant cards.
        
        Example:
            >>> client = TrefleClient(token="test_token")
            >>> plants = client.paginated_get(
            ...     "/genus/quercus/plants",
            ...     max_results=50,
            ...     image_only=True,
            ...     delay_seconds=0.5
            ... )
        """
        results = []
        page = 1
        exclude_ids = exclude_ids or set()

        while len(results) < max_results:
            page_params = dict(params or {})
            page_params["page"] = page

            payload = self.get(path, page_params)
            data = payload.get("data") or []

            if not isinstance(data, list) or not data:
                break

            for plant in data:
                if len(results) >= max_results:
                    break

                plant_key = plant_identity(plant)
                if plant_key in exclude_ids:
                    continue

                if image_only and not has_image(plant):
                    continue

                results.append(normalize_plant_card(plant))

            links = payload.get("links") or {}
            if not links.get("next"):
                break

            page += 1

            if delay_seconds > 0:
                time.sleep(delay_seconds)

        return results


def json_loads_safe(raw: str) -> Dict[str, Any]:
    """
    Safely parse JSON string, returning error dict on failure.
    
    Args:
        raw: Raw JSON string to parse.
    
    Returns:
        Parsed JSON object, or error dict with 'error': True if parsing fails.
    
    Example:
        >>> result = json_loads_safe('{"name": "oak"}')
        >>> print(result)  # {'name': 'oak'}
        >>> result = json_loads_safe('invalid json')
        >>> print(result.get('error'))  # True
    """
    import json

    try:
        return json.loads(raw)
    except Exception:
        return {
            "data": None,
            "error": True,
            "message": "Could not decode JSON response.",
            "raw": raw,
        }


def plant_identity(plant: Dict[str, Any]) -> str:
    """
    Extract a unique identifier for a plant record.
    
    Returns ID, then slug, then scientific_name, or empty string if none exist.
    
    Args:
        plant: Plant record dictionary.
    
    Returns:
        String identifier for the plant.
    
    Example:
        >>> plant = {"id": 123, "slug": "quercus-robur", "scientific_name": "Quercus robur"}
        >>> plant_identity(plant)
        '123'
        >>> plant = {"slug": "quercus-robur", "scientific_name": "Quercus robur"}
        >>> plant_identity(plant)
        'quercus-robur'
    """
    return str(
        plant.get("id")
        or plant.get("slug")
        or plant.get("scientific_name")
        or ""
    )


def has_image(plant: Dict[str, Any]) -> bool:
    """
    Check if a plant record has an associated image.
    
    Args:
        plant: Plant record dictionary.
    
    Returns:
        True if image_url exists or images dict has non-empty values.
    
    Example:
        >>> plant = {"image_url": "https://example.com/oak.jpg"}
        >>> has_image(plant)
        True
        >>> plant = {"images": {"thumb": None}}
        >>> has_image(plant)
        False
    """
    if plant.get("image_url"):
        return True

    images = plant.get("images") or {}
    if isinstance(images, dict):
        return any(bool(items) for items in images.values())

    return False


def normalize_plant_card(plant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and normalize key fields from a plant record for display/storage.
    
    Args:
        plant: Full plant record from Trefle API.
    
    Returns:
        Normalized plant card with key fields extracted.
    
    Example:
        >>> plant = {"id": 1, "slug": "oak", "common_name": "Oak", "scientific_name": "Quercus"}
        >>> card = normalize_plant_card(plant)
        >>> card["common_name"]
        'Oak'
    """
    return {
        "id": plant.get("id"),
        "slug": plant.get("slug"),
        "common_name": plant.get("common_name"),
        "scientific_name": plant.get("scientific_name"),
        "family": plant.get("family"),
        "family_common_name": plant.get("family_common_name"),
        "genus": plant.get("genus"),
        "genus_id": plant.get("genus_id"),
        "image_url": plant.get("image_url"),
        "rank": plant.get("rank"),
        "status": plant.get("status"),
        "vegetable": plant.get("vegetable"),
        "edible": plant.get("edible"),
        "links": plant.get("links") or {},
    }


def search_plant(client: TrefleClient, query: str) -> Optional[Dict[str, Any]]:
    """
    Search for a plant by common or scientific name.
    
    Returns the first result or None if no matches found.
    
    Args:
        client: TrefleClient instance.
        query: Search term (common name, scientific name, etc.).
    
    Returns:
        First plant record found, or None if no results.
    
    Example:
        >>> client = TrefleClient(token="test_token")
        >>> plant = search_plant(client, "oak")
        >>> if plant:
        ...     print(plant.get("common_name"))
        ... else:
        ...     print("No plant found")
    """
    if not query or not query.strip():
        return None

    payload = client.get(
        "/plants/search",
        {
            "q": query.strip(),
        },
    )

    data = payload.get("data") or []
    if not data:
        return None

    return data[0]


def get_plant_details(client: TrefleClient, plant_id_or_query: str) -> Optional[Dict[str, Any]]:
    """
    Fetch full plant details by ID, slug, or search query.
    
    Tries direct lookup first (by ID/slug), then falls back to search if that fails.
    
    Args:
        client: TrefleClient instance.
        plant_id_or_query: Plant ID, slug, or search term.
    
    Returns:
        Full plant record with nested details, or None if not found.
    
    Example:
        >>> client = TrefleClient(token="test_token")
        >>> # Direct lookup by slug:
        >>> plant = get_plant_details(client, "quercus-robur")
        >>> # Fallback search:
        >>> plant = get_plant_details(client, "oak")
        >>> if plant:
        ...     main_species = plant.get("main_species")
    """
    if not plant_id_or_query or not plant_id_or_query.strip():
        return None

    raw = plant_id_or_query.strip()

    direct = client.get(f"/plants/{urllib.parse.quote(raw)}")
    if direct.get("data"):
        return direct["data"]

    searched = search_plant(client, raw)
    if not searched:
        return None

    slug_or_id = searched.get("slug") or searched.get("id")
    if not slug_or_id:
        return searched

    detail = client.get(f"/plants/{slug_or_id}")
    return detail.get("data") or searched


def extract_genus_slug(plant_details: Dict[str, Any]) -> Optional[str]:
    """
    Extract the genus slug from a plant record.
    
    Checks genus.slug, falls back to genus.name slugified, or tries main_species.genus.
    
    Args:
        plant_details: Full plant record from Trefle API.
    
    Returns:
        Genus slug string, or None if not found.
    
    Example:
        >>> plant = {"genus": {"slug": "quercus"}}
        >>> extract_genus_slug(plant)
        'quercus'
        >>> plant = {"genus": {"name": "Quercus"}}
        >>> extract_genus_slug(plant)
        'quercus'
    """
    genus = plant_details.get("genus") or {}
    if isinstance(genus, dict):
        return genus.get("slug") or slugify(genus.get("name"))

    main_species = plant_details.get("main_species") or {}
    return slugify(main_species.get("genus"))


def extract_family_slug(plant_details: Dict[str, Any]) -> Optional[str]:
    """
    Extract the family slug from a plant record.
    
    Checks family.slug, falls back to family.name slugified, or tries main_species.family.
    
    Args:
        plant_details: Full plant record from Trefle API.
    
    Returns:
        Family slug string, or None if not found.
    
    Example:
        >>> plant = {"family": {"slug": "fagaceae"}}
        >>> extract_family_slug(plant)
        'fagaceae'
        >>> plant = {"family": {"name": "Fagaceae"}}
        >>> extract_family_slug(plant)
        'fagaceae'
    """
    family = plant_details.get("family") or {}
    if isinstance(family, dict):
        return family.get("slug") or slugify(family.get("name"))

    main_species = plant_details.get("main_species") or {}
    return slugify(main_species.get("family"))


def extract_distribution_slugs(plant_details: Dict[str, Any]) -> List[str]:
    """
    Extract geographic distribution zone slugs from a plant record.
    
    Collects both native and introduced distribution zones.
    
    Args:
        plant_details: Full plant record from Trefle API.
    
    Returns:
        List of unique zone slugs, order preserved, no duplicates.
    
    Example:
        >>> plant = {
        ...     "main_species": {
        ...         "distributions": {
        ...             "native": [{"slug": "north-america"}],
        ...             "introduced": [{"slug": "europe"}]
        ...         }
        ...     }
        ... }
        >>> slugs = extract_distribution_slugs(plant)
        >>> print(slugs)  # ['north-america', 'europe']
    """
    main_species = plant_details.get("main_species") or {}
    distributions = main_species.get("distributions") or {}

    slugs = []

    for status in ("native", "introduced"):
        zones = distributions.get(status) or []
        for zone in zones:
            slug = zone.get("slug") or zone.get("tdwg_code")
            if slug:
                slugs.append(str(slug).lower())

    return unique_preserve_order(slugs)


def slugify(value: Optional[str]) -> Optional[str]:
    """
    Convert a string to URL-friendly slug format.
    
    Lowercases, strips whitespace, and replaces spaces/underscores with hyphens.
    
    Args:
        value: Input string to slugify, or None.
    
    Returns:
        Slugified string, or None if input is None/empty.
    
    Example:
        >>> slugify("Quercus Robur")
        'quercus-robur'
        >>> slugify("Family_Name")
        'family-name'
        >>> slugify(None)
        None
    """
    if not value:
        return None

    return (
        value.strip()
        .lower()
        .replace(" ", "-")
        .replace("_", "-")
    )


def unique_preserve_order(values: List[str]) -> List[str]:
    """
    Remove duplicates from a list while preserving order.
    
    Args:
        values: List of strings, possibly with duplicates.
    
    Returns:
        List with duplicates removed, original order maintained.
    
    Example:
        >>> unique_preserve_order(["oak", "oak", "maple", "oak"])
        ['oak', 'maple']
        >>> unique_preserve_order(["a", "b", "c"])
        ['a', 'b', 'c']
    """
    seen = set()
    out = []

    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)

    return out


def get_similar_by_genus(
    client: TrefleClient,
    plant_id_or_query: str,
    max_results: int = 20,
    image_only: bool = False,
) -> Dict[str, Any]:
    """
    Find plants in the same genus as the query plant.
    
    Args:
        client: TrefleClient instance.
        plant_id_or_query: Plant ID, slug, or search term.
        max_results: Maximum results to return. Defaults to 20.
        image_only: If True, only return plants with images. Defaults to False.
    
    Returns:
        Dict with 'basis', 'source_plant', 'genus_slug', 'count', 'results', 'warnings'.
    
    Example:
        >>> client = TrefleClient(token="test_token")
        >>> result = get_similar_by_genus(client, "oak", max_results=10, image_only=True)
        >>> print(f"Found {result['count']} similar genus plants")
        >>> for plant in result["results"]:
        ...     print(plant["common_name"])
    """
    plant = get_plant_details(client, plant_id_or_query)

    if not plant:
        return empty_result("genus", f"No plant found for query: {plant_id_or_query}")

    genus_slug = extract_genus_slug(plant)
    if not genus_slug:
        return empty_result("genus", "Could not extract genus from plant details.", plant)

    original_id = plant_identity(plant)
    results = client.paginated_get(
        f"/genus/{genus_slug}/plants",
        max_results=max_results,
        image_only=image_only,
        exclude_ids={original_id},
    )

    return {
        "basis": "genus",
        "query": plant_id_or_query,
        "source_plant": normalize_source_plant(plant),
        "genus_slug": genus_slug,
        "count": len(results),
        "results": results,
        "warnings": [] if results else ["No genus-level related plants found."],
    }


def get_similar_by_family(
    client: TrefleClient,
    plant_id_or_query: str,
    max_results: int = 20,
    image_only: bool = False,
    exclude_genus_results: bool = True,
) -> Dict[str, Any]:
    """
    Find plants in the same family as the query plant, optionally excluding the genus.
    
    Args:
        client: TrefleClient instance.
        plant_id_or_query: Plant ID, slug, or search term.
        max_results: Maximum results to return. Defaults to 20.
        image_only: If True, only return plants with images. Defaults to False.
        exclude_genus_results: If True, exclude results from the same genus. Defaults to True.
    
    Returns:
        Dict with 'basis', 'source_plant', 'family_slug', 'excluded_genus', 'count', 'results', 'warnings'.
    
    Example:
        >>> client = TrefleClient(token="test_token")
        >>> result = get_similar_by_family(
        ...     client, "oak",
        ...     max_results=15,
        ...     exclude_genus_results=True
        ... )
        >>> print(f"Found {result['count']} family plants (excluding genus)")
    """
    plant = get_plant_details(client, plant_id_or_query)

    if not plant:
        return empty_result("family", f"No plant found for query: {plant_id_or_query}")

    family_slug = extract_family_slug(plant)
    genus_slug = extract_genus_slug(plant)

    if not family_slug:
        return empty_result("family", "Could not extract family from plant details.", plant)

    exclude_ids = {plant_identity(plant)}

    if exclude_genus_results and genus_slug:
        genus_results = client.paginated_get(
            f"/genus/{genus_slug}/plants",
            max_results=max(max_results * 3, 50),
            image_only=False,
            exclude_ids=exclude_ids,
        )
        exclude_ids.update(plant_identity(p) for p in genus_results)

    # Swagger supports /plants?filter[family_name]=...
    # The family endpoint exposes /families/{slug}/genus, not /families/{slug}/plants.
    # So filtering plants by family_name is the cleanest plant-level route.
    family_name = extract_family_name(plant) or family_slug

    results = client.paginated_get(
        "/plants",
        max_results=max_results,
        params={
            "filter[family_name]": family_name,
        },
        image_only=image_only,
        exclude_ids=exclude_ids,
    )

    return {
        "basis": "family",
        "query": plant_id_or_query,
        "source_plant": normalize_source_plant(plant),
        "family_slug": family_slug,
        "family_name": family_name,
        "excluded_genus": genus_slug if exclude_genus_results else None,
        "count": len(results),
        "results": results,
        "warnings": [] if results else ["No family-level exclusive plants found."],
    }


def get_similar_by_distribution(
    client: TrefleClient,
    plant_id_or_query: str,
    max_results: int = 20,
    image_only: bool = False,
    exclude_genus_and_family_results: bool = True,
    max_zones_to_search: int = 3,
) -> Dict[str, Any]:
    """
    Find plants in the same geographic distribution zones as the query plant.
    
    Optionally excludes plants already found by genus or family.
    
    Args:
        client: TrefleClient instance.
        plant_id_or_query: Plant ID, slug, or search term.
        max_results: Maximum results to return. Defaults to 20.
        image_only: If True, only return plants with images. Defaults to False.
        exclude_genus_and_family_results: If True, exclude genus/family results first. Defaults to True.
        max_zones_to_search: Maximum distribution zones to query. Defaults to 3.
    
    Returns:
        Dict with 'basis', 'source_plant', 'distribution_slugs', 'count', 'results', 'warnings'.
    
    Example:
        >>> client = TrefleClient(token="test_token")
        >>> result = get_similar_by_distribution(
        ...     client, "oak",
        ...     max_results=10,
        ...     exclude_genus_and_family_results=True
        ... )
        >>> for plant in result["results"]:
        ...     zone = plant.get("matched_distribution_slug")
        ...     print(f"{plant['common_name']} found in {zone}")
    """
    plant = get_plant_details(client, plant_id_or_query)

    if not plant:
        return empty_result("distribution", f"No plant found for query: {plant_id_or_query}")

    distribution_slugs = extract_distribution_slugs(plant)

    if not distribution_slugs:
        return empty_result("distribution", "Could not extract distributions from plant details.", plant)

    exclude_ids = {plant_identity(plant)}
    genus_slug = extract_genus_slug(plant)
    family_slug = extract_family_slug(plant)

    if exclude_genus_and_family_results:
        if genus_slug:
            genus_results = client.paginated_get(
                f"/genus/{genus_slug}/plants",
                max_results=max(max_results * 3, 50),
                image_only=False,
                exclude_ids=exclude_ids,
            )
            exclude_ids.update(plant_identity(p) for p in genus_results)

        family_name = extract_family_name(plant)
        if family_name:
            family_results = client.paginated_get(
                "/plants",
                max_results=max(max_results * 3, 50),
                params={
                    "filter[family_name]": family_name,
                },
                image_only=False,
                exclude_ids=exclude_ids,
            )
            exclude_ids.update(plant_identity(p) for p in family_results)

    results = []
    searched_zones = distribution_slugs[:max_zones_to_search]

    for zone_slug in searched_zones:
        remaining = max_results - len(results)
        if remaining <= 0:
            break

        zone_results = client.paginated_get(
            f"/distributions/{zone_slug}/plants",
            max_results=remaining,
            image_only=image_only,
            exclude_ids=exclude_ids,
        )

        for item in zone_results:
            key = plant_identity(item)
            if key not in exclude_ids:
                item["matched_distribution_slug"] = zone_slug
                results.append(item)
                exclude_ids.add(key)

    return {
        "basis": "distribution",
        "query": plant_id_or_query,
        "source_plant": normalize_source_plant(plant),
        "distribution_slugs": distribution_slugs,
        "searched_distribution_slugs": searched_zones,
        "excluded_genus": genus_slug if exclude_genus_and_family_results else None,
        "excluded_family": family_slug if exclude_genus_and_family_results else None,
        "count": len(results),
        "results": results,
        "warnings": [] if results else ["No distribution-level exclusive plants found."],
    }


def get_similar_by_filter(
    client,
    plant_id_or_query: str,
    filter_field: str,
    source_value: str,
    basis: str,
    max_results: int = 20,
    image_only: bool = False,
    exclude_ids=None,
):
    """
    Return plants similar to a source plant using a single API filter.

    This is a generic helper function used by the more specific similarity
    functions below. It queries the `/plants` endpoint with a Trefle-style
    filter parameter, such as `filter[growth_habit]` or `filter[fruit_color]`.
    """
    if isinstance(source_value, list):
        source_value = ",".join(str(v) for v in source_value if v)

    if not source_value:
        return empty_result(basis, f"No source value found for {filter_field}.")

    exclude_ids = exclude_ids or set()

    results = client.paginated_get(
        "/plants",
        max_results=max_results,
        params={
            f"filter[{filter_field}]": source_value,
        },
        image_only=image_only,
        exclude_ids=exclude_ids,
    )

    return {
        "basis": basis,
        "query": plant_id_or_query,
        "filter_field": filter_field,
        "filter_value": source_value,
        "count": len(results),
        "results": results,
        "warnings": [] if results else [f"No similar plants found by {basis}."],
    }


def get_similar_by_edible_part(
    client,
    plant_id_or_query: str,
    max_results: int = 20,
    image_only: bool = False,
):
    """
    Return plants similar to the source plant by edible part.

    This function retrieves the source plant details, extracts
    `main_species.edible_part`, and searches for other plants with the same
    edible part value.

    Args:
        client:
            API client instance used to fetch plant details and query plants.
        plant_id_or_query:
            Plant ID, slug, or user search query for the source plant.
        max_results:
            Maximum number of similar plants to return.
        image_only:
            If True, only return plants with images.

    Returns:
        dict:
            Standardized similarity response for edible-part similarity.

    Example:
        result = get_similar_by_edible_part(
            client=client,
            plant_id_or_query="blueberry",
            max_results=12,
            image_only=True,
        )

        print(result["filter_value"])
        for plant in result["results"]:
            print(plant.get("common_name"), plant.get("scientific_name"))
    """
    plant = get_plant_details(client, plant_id_or_query)
    if not plant:
        return empty_result("edible_part", f"No plant found for query: {plant_id_or_query}")

    main_species = plant.get("main_species") or {}
    edible_part = main_species.get("edible_part")

    if isinstance(edible_part, list):
        edible_part = ",".join(edible_part)

    return get_similar_by_filter(
        client,
        plant_id_or_query,
        filter_field="edible_part",
        source_value=edible_part,
        basis="edible_part",
        max_results=max_results,
        image_only=image_only,
        exclude_ids={plant_identity(plant)},
    )


def get_similar_by_growth_habit(
    client,
    plant_id_or_query: str,
    max_results: int = 20,
    image_only: bool = False,
):
    """
    Return plants similar to the source plant by growth habit.

    This function retrieves the source plant details, extracts
    `main_species.specifications.growth_habit`, and searches for other plants
    with the same growth habit.

    Args:
        client:
            API client instance used to fetch plant details and query plants.
        plant_id_or_query:
            Plant ID, slug, or user search query for the source plant.
        max_results:
            Maximum number of similar plants to return.
        image_only:
            If True, only return plants with images.

    Returns:
        dict:
            Standardized similarity response for growth-habit similarity.

    Example:
        result = get_similar_by_growth_habit(
            client=client,
            plant_id_or_query="monstera",
            max_results=10,
            image_only=True,
        )

        print(result["filter_value"])
        print(result["count"])
    """
    plant = get_plant_details(client, plant_id_or_query)
    if not plant:
        return empty_result("growth_habit", f"No plant found for query: {plant_id_or_query}")

    specs = ((plant.get("main_species") or {}).get("specifications") or {})
    growth_habit = specs.get("growth_habit")

    return get_similar_by_filter(
        client,
        plant_id_or_query,
        filter_field="growth_habit",
        source_value=growth_habit,
        basis="growth_habit",
        max_results=max_results,
        image_only=image_only,
        exclude_ids={plant_identity(plant)},
    )


def get_similar_by_growth_form(
    client,
    plant_id_or_query: str,
    max_results: int = 20,
    image_only: bool = False,
):
    """
    Return plants similar to the source plant by growth form.

    This function retrieves the source plant details, extracts
    `main_species.specifications.growth_form`, and searches for other plants
    with the same growth form.

    Args:
        client:
            API client instance used to fetch plant details and query plants.
        plant_id_or_query:
            Plant ID, slug, or user search query for the source plant.
        max_results:
            Maximum number of similar plants to return.
        image_only:
            If True, only return plants with images.

    Returns:
        dict:
            Standardized similarity response for growth-form similarity.

    Example:
        result = get_similar_by_growth_form(
            client=client,
            plant_id_or_query="maple",
            max_results=15,
            image_only=False,
        )

        for plant in result["results"]:
            print(plant.get("common_name"))
    """
    plant = get_plant_details(client, plant_id_or_query)
    if not plant:
        return empty_result("growth_form", f"No plant found for query: {plant_id_or_query}")

    specs = ((plant.get("main_species") or {}).get("specifications") or {})
    growth_form = specs.get("growth_form")

    return get_similar_by_filter(
        client,
        plant_id_or_query,
        filter_field="growth_form",
        source_value=growth_form,
        basis="growth_form",
        max_results=max_results,
        image_only=image_only,
        exclude_ids={plant_identity(plant)},
    )


def get_similar_by_fruit_color(
    client,
    plant_id_or_query: str,
    max_results: int = 20,
    image_only: bool = False,
):
    """
    Return plants similar to the source plant by fruit or seed color.

    This function retrieves the source plant details, extracts
    `main_species.fruit_or_seed.color`, and searches for other plants with the
    same fruit or seed color.

    Args:
        client:
            API client instance used to fetch plant details and query plants.
        plant_id_or_query:
            Plant ID, slug, or user search query for the source plant.
        max_results:
            Maximum number of similar plants to return.
        image_only:
            If True, only return plants with images.

    Returns:
        dict:
            Standardized similarity response for fruit-color similarity.

    Example:
        result = get_similar_by_fruit_color(
            client=client,
            plant_id_or_query="tomato",
            max_results=10,
            image_only=True,
        )

        print(result["filter_value"])
        for plant in result["results"]:
            print(plant.get("common_name"), plant.get("image_url"))
    """
    plant = get_plant_details(client, plant_id_or_query)
    if not plant:
        return empty_result("fruit_color", f"No plant found for query: {plant_id_or_query}")

    fruit = ((plant.get("main_species") or {}).get("fruit_or_seed") or {})
    fruit_color = fruit.get("color")

    # Trefle often returns color as a list, e.g. ["red", "orange"]
    if isinstance(fruit_color, list):
        fruit_color = ",".join(str(c) for c in fruit_color if c)

    return get_similar_by_filter(
        client,
        plant_id_or_query,
        filter_field="fruit_color",
        source_value=fruit_color,
        basis="fruit_color",
        max_results=max_results,
        image_only=image_only,
        exclude_ids={plant_identity(plant)},
    )  

def get_similar_plants_bundle(
    client: TrefleClient,
    plant_id_or_query: str,
    max_results_per_group: int = 10,
    image_only: bool = False,
) -> Dict[str, Any]:
    """
    Find similar plants grouped by similarity basis: genus, family, and distribution.
    
    Convenience function that runs all three similarity queries and combines results.
    
    Args:
        client: TrefleClient instance.
        plant_id_or_query: Plant ID, slug, or search term.
        max_results_per_group: Max results per similarity group. Defaults to 10.
        image_only: If True, only return plants with images. Defaults to False.
    
    Returns:
        Dict with 'query', 'image_only', 'groups' containing same_genus, same_family_excluding_genus,
        and same_distribution_excluding_taxonomy keys, each with results and metadata.
    
    Example:
        >>> client = TrefleClient(token="test_token")
        >>> bundle = get_similar_plants_bundle(
        ...     client, "blueberry",
        ...     max_results_per_group=5,
        ...     image_only=True
        ... )
        >>> genus_results = bundle["groups"]["same_genus"]["results"]
        >>> family_results = bundle["groups"]["same_family_excluding_genus"]["results"]
        >>> distrib_results = bundle["groups"]["same_distribution_excluding_taxonomy"]["results"]
    """
    return {
        "query": plant_id_or_query,
        "image_only": image_only,
        "groups": {
            "same_genus": get_similar_by_genus(
                client, plant_id_or_query, max_results_per_group, image_only
            ),
            "same_family_excluding_genus": get_similar_by_family(
                client, plant_id_or_query, max_results_per_group, image_only, True
            ),
            "same_distribution_excluding_taxonomy": get_similar_by_distribution(
                client, plant_id_or_query, max_results_per_group, image_only, True
            ),
            "same_edible_part": get_similar_by_edible_part(
                client, plant_id_or_query, max_results_per_group, image_only
            ),
            "same_growth_habit": get_similar_by_growth_habit(
                client, plant_id_or_query, max_results_per_group, image_only
            ),
            "same_growth_form": get_similar_by_growth_form(
                client, plant_id_or_query, max_results_per_group, image_only
            ),
            "same_fruit_color": get_similar_by_fruit_color(
                client, plant_id_or_query, max_results_per_group, image_only
            ),
        },
    }


def extract_family_name(plant_details: Dict[str, Any]) -> Optional[str]:
    """
    Extract the family name (not slug) from a plant record.
    
    Args:
        plant_details: Full plant record from Trefle API.
    
    Returns:
        Family name string (e.g., "Fagaceae"), or None if not found.
    
    Example:
        >>> plant = {"family": {"name": "Fagaceae"}}
        >>> extract_family_name(plant)
        'Fagaceae'
    """
    family = plant_details.get("family") or {}
    if isinstance(family, dict):
        return family.get("name")

    main_species = plant_details.get("main_species") or {}
    return main_species.get("family")


def normalize_source_plant(plant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a plant record into a compact source-plant summary.
    
    Extracts key fields and falls back to main_species nested fields when available.
    
    Args:
        plant: Full plant record from Trefle API.
    
    Returns:
        Normalized dict with id, slug, common_name, scientific_name, image_url, genus, family.
    
    Example:
        >>> plant = {
        ...     "id": 1,
        ...     "slug": "quercus-robur",
        ...     "common_name": "English Oak",
        ...     "scientific_name": "Quercus robur",
        ...     "genus": {"slug": "quercus"},
        ...     "family": {"slug": "fagaceae"}
        ... }
        >>> source = normalize_source_plant(plant)
        >>> source["genus"]
        'quercus'
    """
    main_species = plant.get("main_species") or {}

    return {
        "id": plant.get("id"),
        "slug": plant.get("slug"),
        "common_name": plant.get("common_name") or main_species.get("common_name"),
        "scientific_name": plant.get("scientific_name") or main_species.get("scientific_name"),
        "image_url": plant.get("image_url") or main_species.get("image_url"),
        "genus": extract_genus_slug(plant),
        "family": extract_family_slug(plant),
    }


def empty_result(
    basis: str,
    warning: str,
    plant: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create an empty result dict when no plants are found or an error occurs.
    
    Args:
        basis: Type of similarity search (e.g., "genus", "family", "distribution").
        warning: Warning/error message to include.
        plant: Optional plant record to include in source_plant field.
    
    Returns:
        Standardized empty result dict with warnings.
    
    Example:
        >>> result = empty_result("genus", "Plant not found")
        >>> print(result["count"])
        0
        >>> print(result["warnings"])
        ['Plant not found']
    """
    return {
        "basis": basis,
        "source_plant": normalize_source_plant(plant) if plant else None,
        "count": 0,
        "results": [],
        "warnings": [warning],
    }