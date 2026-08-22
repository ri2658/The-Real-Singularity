import json
import logging
import os
import time
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config

from similarity_querying import (
    TrefleClient,
    get_plant_details,
    search_plant,
    normalize_plant_card,
    get_similar_plants_bundle,
    get_similar_by_genus,
    get_similar_by_family,
    get_similar_by_distribution,
    get_similar_by_edible_part,
    get_similar_by_growth_habit,
    get_similar_by_growth_form,
    get_similar_by_fruit_color,
)


logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

_cached_trefle_token = None
_dynamodb_resource = None
_cache_table = None


# -----------------------------
# General helpers
# -----------------------------

def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def make_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body),
    }


def log_step(label: str, start_time: float, level: int = logging.INFO) -> None:
    """
    Log a timed step relative to a request start time.

    Args:
        label:
            Human-readable step label.
        start_time:
            Timestamp returned by `time.time()` when the request started.
        level:
            Logging level to use. Defaults to INFO.

    Example:
        start = time.time()
        log_step("cache checked", start)
    """
    elapsed = round(time.time() - start_time, 3)
    logger.log(level, "%s at %.3fs", label, elapsed)


def clamp_max_results(value: Any, default: int = 10, upper_bound: int = 25) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default

    return max(1, min(parsed, upper_bound))


def get_request_id(context: Any) -> Optional[str]:
    """
    Return the AWS Lambda request ID when available.
    """
    return getattr(context, "aws_request_id", None) if context else None


def get_event_summary(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a compact event summary safe for logs.

    This avoids logging the entire API Gateway event while preserving the parts
    that are useful for debugging route behavior.
    """
    return {
        "rawPath": event.get("rawPath"),
        "routeKey": event.get("routeKey"),
        "queryStringParameters": event.get("queryStringParameters") or {},
        "pathParameters": event.get("pathParameters") or {},
        "requestContext": {
            "http": ((event.get("requestContext") or {}).get("http") or {}),
            "requestId": (event.get("requestContext") or {}).get("requestId"),
        },
    }


# -----------------------------
# Secrets Manager
# -----------------------------

def get_trefle_token() -> str:
    """
    Load Trefle token from Secrets Manager in AWS.
    Falls back to TREFLE_TOKEN for local development.
    Caches the token across warm Lambda invocations.
    """
    global _cached_trefle_token

    if _cached_trefle_token:
        logger.debug("Using cached Trefle token")
        return _cached_trefle_token

    local_token = os.getenv("TREFLE_TOKEN")
    if local_token:
        logger.info("Loaded Trefle token from TREFLE_TOKEN environment variable")
        _cached_trefle_token = local_token.strip()
        return _cached_trefle_token

    secret_name = os.getenv("TREFLE_SECRET_NAME")
    if not secret_name:
        logger.error("Missing TREFLE_SECRET_NAME or TREFLE_TOKEN")
        raise ValueError("Missing TREFLE_SECRET_NAME or TREFLE_TOKEN")

    logger.info("Loading Trefle token from Secrets Manager secret=%s", secret_name)

    secrets_client = boto3.client(
        "secretsmanager",
        config=Config(
            connect_timeout=2,
            read_timeout=3,
            retries={"max_attempts": 1},
        ),
    )

    response = secrets_client.get_secret_value(SecretId=secret_name)

    secret_string = response.get("SecretString")
    if not secret_string:
        logger.error("SecretString missing from Secrets Manager response")
        raise ValueError("SecretString missing from Secrets Manager response")

    parsed = json.loads(secret_string)

    if not isinstance(parsed, dict):
        logger.error("SecretString must be JSON object")
        raise ValueError("SecretString must be JSON object")

    token = parsed.get("TREFLE_TOKEN")
    if not token:
        logger.error("TREFLE_TOKEN missing inside secret JSON")
        raise ValueError("TREFLE_TOKEN missing inside secret JSON")

    logger.info("Loaded Trefle token from Secrets Manager")
    _cached_trefle_token = token.strip()
    return _cached_trefle_token


def get_client() -> TrefleClient:
    logger.debug("Creating Trefle client")
    return TrefleClient(token=get_trefle_token())


# -----------------------------
# DynamoDB cache
# -----------------------------

def get_cache_table():
    """
    Return DynamoDB cache table if caching is configured.
    If CACHE_TABLE_NAME is missing, caching is disabled.
    """
    global _dynamodb_resource
    global _cache_table

    if _cache_table is not None:
        logger.debug("Using cached DynamoDB table resource")
        return _cache_table

    table_name = os.getenv("CACHE_TABLE_NAME")
    if not table_name:
        logger.debug("CACHE_TABLE_NAME missing; cache disabled")
        return None

    if _dynamodb_resource is None:
        logger.info("Creating DynamoDB resource for cache table=%s", table_name)
        _dynamodb_resource = boto3.resource("dynamodb")

    _cache_table = _dynamodb_resource.Table(table_name)
    return _cache_table


def normalize_cache_part(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "-")


def build_cache_key(*parts: Any) -> str:
    return ":".join(normalize_cache_part(part) for part in parts)


def get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    table = get_cache_table()
    if table is None:
        logger.debug("Cache skipped because table is not configured")
        return None

    try:
        logger.debug("Checking cache key=%s", cache_key)
        item = table.get_item(Key={"cache_key": cache_key}).get("Item")

        if not item:
            logger.info("Cache miss key=%s", cache_key)
            return None

        now = int(time.time())
        expires_at = int(item.get("expires_at", 0))

        if expires_at <= now:
            logger.info("Cache expired key=%s expires_at=%s now=%s", cache_key, expires_at, now)
            return None

        response_json = item.get("response")
        if not response_json:
            logger.warning("Cache item missing response key=%s", cache_key)
            return None

        logger.info("Cache hit key=%s", cache_key)
        return json.loads(response_json)

    except Exception:
        logger.exception("Cache read error key=%s", cache_key)
        return None


def set_cached_response(cache_key: str, response_body: Dict[str, Any]) -> None:
    table = get_cache_table()
    if table is None:
        logger.debug("Cache write skipped because table is not configured")
        return

    try:
        ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
        now = int(time.time())

        table.put_item(
            Item={
                "cache_key": cache_key,
                "response": json.dumps(response_body),
                "created_at": now,
                "expires_at": now + ttl_seconds,
            }
        )

        logger.info(
            "Cache set key=%s ttl_seconds=%s expires_at=%s",
            cache_key,
            ttl_seconds,
            now + ttl_seconds,
        )

    except Exception:
        logger.exception("Cache write error key=%s", cache_key)


def add_cache_metadata(body: Dict[str, Any], hit: bool, cache_key: str) -> Dict[str, Any]:
    body["cache"] = {
        "hit": hit,
        "cache_key": cache_key,
    }
    return body


# -----------------------------
# Plant image/profile helpers
# -----------------------------

def get_best_image_url(plant: Dict[str, Any]) -> Optional[str]:
    if not plant:
        return None

    if plant.get("image_url"):
        return plant["image_url"]

    main_species = plant.get("main_species") or {}
    if main_species.get("image_url"):
        return main_species["image_url"]

    images = main_species.get("images") or {}
    if isinstance(images, dict):
        for _, image_list in images.items():
            if not image_list:
                continue

            first = image_list[0]

            if isinstance(first, dict):
                return (
                    first.get("image_url")
                    or first.get("url")
                    or first.get("original_url")
                )

            if isinstance(first, str):
                return first

    return None


def normalize_plant_profile(plant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize full plant details for frontend profile page.
    Keeps raw fields that may be useful, but exposes stable top-level fields.
    """
    main_species = plant.get("main_species") or {}
    genus = plant.get("genus") or {}
    family = plant.get("family") or {}

    return {
        "id": plant.get("id"),
        "slug": plant.get("slug"),
        "common_name": plant.get("common_name") or main_species.get("common_name"),
        "scientific_name": plant.get("scientific_name") or main_species.get("scientific_name"),
        "image_url": get_best_image_url(plant),
        "family": family.get("name") if isinstance(family, dict) else main_species.get("family"),
        "family_slug": family.get("slug") if isinstance(family, dict) else None,
        "family_common_name": (
            family.get("common_name") if isinstance(family, dict)
            else plant.get("family_common_name")
        ),
        "genus": genus.get("name") if isinstance(genus, dict) else main_species.get("genus"),
        "genus_slug": genus.get("slug") if isinstance(genus, dict) else None,
        "vegetable": plant.get("vegetable") or main_species.get("vegetable"),
        "edible": main_species.get("edible"),
        "edible_part": main_species.get("edible_part"),
        "distribution": main_species.get("distribution"),
        "distributions": main_species.get("distributions"),
        "duration": main_species.get("duration"),
        "flower": main_species.get("flower"),
        "foliage": main_species.get("foliage"),
        "fruit_or_seed": main_species.get("fruit_or_seed"),
        "specifications": main_species.get("specifications"),
        "growth": main_species.get("growth"),
        "links": plant.get("links") or {},
        "raw": plant,
    }


# -----------------------------
# Route handlers
# -----------------------------

def handle_search(event: Dict[str, Any]) -> Dict[str, Any]:
    start = time.time()
    query_params = event.get("queryStringParameters") or {}

    query = query_params.get("query") or query_params.get("q")
    max_results = clamp_max_results(query_params.get("max_results", 10), default=10, upper_bound=25)
    image_only = parse_bool(query_params.get("image_only"), default=False)

    logger.info(
        "Handling search request query=%s max_results=%s image_only=%s",
        query,
        max_results,
        image_only,
    )

    if not query:
        logger.warning("Search request missing required query parameter")
        return make_response(
            400,
            {
                "error": "Missing required query parameter: query",
                "example": "/search?query=blueberry&max_results=10&image_only=true",
            },
        )

    cache_key = build_cache_key("search", query, max_results, image_only)
    cached = get_cached_response(cache_key)
    log_step("search cache checked", start)

    if cached is not None:
        logger.info("Returning cached search response key=%s", cache_key)
        return make_response(200, add_cache_metadata(cached, True, cache_key))

    client = get_client()
    log_step("search client created", start)

    payload = client.get(
        "/plants/search",
        {
            "q": query.strip(),
        },
    )
    log_step("search Trefle API request completed", start)

    data = payload.get("data") or []

    results = []
    for plant in data:
        if len(results) >= max_results:
            break

        card = normalize_plant_card(plant)

        if image_only and not card.get("image_url"):
            continue

        results.append(card)

    body = {
        "query": query,
        "max_results": max_results,
        "image_only": image_only,
        "count": len(results),
        "results": results,
        "warnings": [] if results else ["No search results found."],
    }

    logger.info("Search response built query=%s count=%s", query, len(results))

    add_cache_metadata(body, False, cache_key)
    set_cached_response(cache_key, body)
    log_step("search response cached", start)

    return make_response(200, body)


def handle_plant_profile(event: Dict[str, Any]) -> Dict[str, Any]:
    start = time.time()
    path_params = event.get("pathParameters") or {}
    slug = path_params.get("slug")

    logger.info("Handling plant profile request slug=%s", slug)

    if not slug:
        logger.warning("Plant profile request missing slug path parameter")
        return make_response(
            400,
            {
                "error": "Missing plant slug in path.",
                "example": "/plants/vaccinium-corymbosum",
            },
        )

    cache_key = build_cache_key("plant", slug)
    cached = get_cached_response(cache_key)
    log_step("plant profile cache checked", start)

    if cached is not None:
        logger.info("Returning cached plant profile response key=%s", cache_key)
        return make_response(200, add_cache_metadata(cached, True, cache_key))

    client = get_client()
    log_step("plant profile client created", start)

    plant = get_plant_details(client, slug)
    log_step("plant profile Trefle detail request completed", start)

    if not plant:
        logger.warning("Plant not found slug=%s", slug)
        return make_response(
            404,
            {
                "error": "Plant not found.",
                "slug": slug,
            },
        )

    body = {
        "slug": slug,
        "plant": normalize_plant_profile(plant),
        "warnings": [],
    }

    logger.info("Plant profile response built slug=%s plant_id=%s", slug, plant.get("id"))

    add_cache_metadata(body, False, cache_key)
    set_cached_response(cache_key, body)
    log_step("plant profile response cached", start)

    return make_response(200, body)


def handle_similar(event: Dict[str, Any]) -> Dict[str, Any]:
    start = time.time()

    query_params = event.get("queryStringParameters") or {}

    query = query_params.get("query")
    basis = query_params.get("basis", "genus").strip().lower()
    max_results = clamp_max_results(query_params.get("max_results", 10), default=10, upper_bound=25)
    image_only = parse_bool(query_params.get("image_only"), default=False)

    logger.info(
        "Handling similar request query=%s basis=%s max_results=%s image_only=%s",
        query,
        basis,
        max_results,
        image_only,
    )

    if not query:
        logger.warning("Similar request missing required query parameter")
        return make_response(
            400,
            {
                "error": "Missing required query parameter: query",
                "example": "/similar?query=blueberry&basis=genus&max_results=5&image_only=true",
            },
        )

    cache_key = build_cache_key("similar", query, basis, max_results, image_only)
    cached = get_cached_response(cache_key)
    log_step("similar cache checked", start)

    if cached is not None:
        logger.info("Returning cached similar response key=%s", cache_key)
        return make_response(200, add_cache_metadata(cached, True, cache_key))

    client = get_client()
    log_step("similar client created", start)

    if basis == "genus":
        result = get_similar_by_genus(
            client=client,
            plant_id_or_query=query,
            max_results=max_results,
            image_only=image_only,
        )

    elif basis == "family":
        result = get_similar_by_family(
            client=client,
            plant_id_or_query=query,
            max_results=max_results,
            image_only=image_only,
            exclude_genus_results=True,
        )

    elif basis == "distribution":
        result = get_similar_by_distribution(
            client=client,
            plant_id_or_query=query,
            max_results=max_results,
            image_only=image_only,
            exclude_genus_and_family_results=True,
            max_zones_to_search=2,
        )

    elif basis == "edible_part":
        result = get_similar_by_edible_part(
            client=client,
            plant_id_or_query=query,
            max_results=max_results,
            image_only=image_only,
        )

    elif basis == "growth_habit":
        result = get_similar_by_growth_habit(
            client=client,
            plant_id_or_query=query,
            max_results=max_results,
            image_only=image_only,
        )

    elif basis == "growth_form":
        result = get_similar_by_growth_form(
            client=client,
            plant_id_or_query=query,
            max_results=max_results,
            image_only=image_only,
        )

    elif basis == "fruit_color":
        result = get_similar_by_fruit_color(
            client=client,
            plant_id_or_query=query,
            max_results=max_results,
            image_only=image_only,
        )

    elif basis == "bundle":
        result = get_similar_plants_bundle(
            client=client,
            plant_id_or_query=query,
            max_results_per_group=max_results,
            image_only=image_only,
        )

    else:
        logger.warning("Unsupported similarity basis basis=%s query=%s", basis, query)
        return make_response(
            400,
            {
                "error": f"Unsupported basis: {basis}",
                "supported_basis": [
                    "genus",
                    "family",
                    "distribution",
                    "edible_part",
                    "growth_habit",
                    "growth_form",
                    "fruit_color",
                    "bundle",
                ],
            },
        )

    log_step(f"similar computation completed basis={basis}", start)

    result["request"] = {
        "query": query,
        "basis": basis,
        "max_results": max_results,
        "image_only": image_only,
    }

    result["timing"] = {
        "duration_seconds": round(time.time() - start, 3),
    }

    logger.info(
        "Similar response built query=%s basis=%s count=%s duration_seconds=%s",
        query,
        basis,
        result.get("count"),
        result["timing"]["duration_seconds"],
    )

    add_cache_metadata(result, False, cache_key)
    set_cached_response(cache_key, result)
    log_step("similar response cached", start)

    return make_response(200, result)


# -----------------------------
# Lambda entry point
# -----------------------------

def lambda_handler(event, context):
    start = time.time()
    request_id = get_request_id(context)

    logger.info(
        "Lambda invocation started request_id=%s event=%s",
        request_id,
        json.dumps(get_event_summary(event), default=str)[:1000],
    )

    try:
        raw_path = event.get("rawPath", "")
        route_key = event.get("routeKey", "")

        logger.info("Routing request request_id=%s raw_path=%s route_key=%s", request_id, raw_path, route_key)

        if raw_path == "/search":
            response = handle_search(event)
            log_step("lambda /search completed", start)
            return response

        if raw_path.startswith("/plants/"):
            response = handle_plant_profile(event)
            log_step("lambda /plants/{slug} completed", start)
            return response

        if raw_path == "/similar":
            response = handle_similar(event)
            log_step("lambda /similar completed", start)
            return response

        logger.warning("Route not found request_id=%s raw_path=%s route_key=%s", request_id, raw_path, route_key)

        return make_response(
            404,
            {
                "error": "Route not found.",
                "path": raw_path,
                "supported_routes": [
                    "GET /search",
                    "GET /plants/{slug}",
                    "GET /similar",
                ],
            },
        )

    except Exception as e:
        logger.exception("Unhandled Lambda error request_id=%s", request_id)
        return make_response(
            500,
            {
                "error": "Internal server error",
                "message": str(e),
            },
        )