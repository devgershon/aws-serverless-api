"""
Blog Posts API — Lambda Handler
Handles all CRUD operations for blog posts stored in DynamoDB.

Endpoints:
  POST   /posts          — create a post
  GET    /posts          — list all published posts
  GET    /posts/{id}     — get a single post
  PUT    /posts/{id}     — update a post
  DELETE /posts/{id}     — delete a post
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# ── Logger ──────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── DynamoDB client ──────────────────────────────────────────────────────────
# Table name is injected as an environment variable by Terraform.
dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table(os.environ["TABLE_NAME"])

# ── CORS headers ─────────────────────────────────────────────────────────────
# These are returned on every response so the portfolio site (a different origin)
# can call this API from the browser without being blocked.
CORS_HEADERS = {
    "Content-Type":                "application/json",
    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
    "Access-Control-Allow-Headers":"Content-Type,Authorization",
    "Access-Control-Allow-Methods":"GET,POST,PUT,DELETE,OPTIONS",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def response(status_code: int, body: dict) -> dict:
    """Build a standard API Gateway response."""
    return {
        "statusCode": status_code,
        "headers":    CORS_HEADERS,
        "body":       json.dumps(body, default=str),
    }


def now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def parse_body(event: dict) -> dict:
    """Safely parse the request body as JSON."""
    body = event.get("body") or "{}"
    if isinstance(body, str):
        return json.loads(body)
    return body


# ── Route handlers ────────────────────────────────────────────────────────────

def create_post(event: dict) -> dict:
    """
    POST /posts
    Creates a new blog post.

    Required fields: title, content
    Optional fields: excerpt, slug, status (draft | published)
    """
    body = parse_body(event)

    title   = body.get("title",   "").strip()
    content = body.get("content", "").strip()

    if not title or not content:
        return response(400, {"error": "title and content are required"})

    post_id = str(uuid.uuid4())
    slug    = body.get("slug", title.lower().replace(" ", "-"))
    ts      = now()

    item = {
        "id":           post_id,
        "title":        title,
        "content":      content,
        "excerpt":      body.get("excerpt", content[:150] + "..." if len(content) > 150 else content),
        "slug":         slug,
        "status":       body.get("status", "draft"),
        "published_at": ts if body.get("status") == "published" else None,
        "created_at":   ts,
        "updated_at":   ts,
    }

    table.put_item(Item=item)
    logger.info("Created post %s", post_id)
    return response(201, {"message": "Post created", "post": item})


def list_posts(event: dict) -> dict:
    """
    GET /posts
    Returns all posts. Pass ?status=published to filter by status.
    Results are sorted newest first by created_at.
    """
    params      = event.get("queryStringParameters") or {}
    status      = params.get("status")

    scan_kwargs = {}
    if status:
        scan_kwargs["FilterExpression"] = Attr("status").eq(status)

    result = table.scan(**scan_kwargs)
    posts  = result.get("Items", [])

    # Handle DynamoDB pagination (scan returns max 1 MB per call)
    while "LastEvaluatedKey" in result:
        scan_kwargs["ExclusiveStartKey"] = result["LastEvaluatedKey"]
        result = table.scan(**scan_kwargs)
        posts.extend(result.get("Items", []))

    # Sort newest first
    posts.sort(key=lambda p: p.get("created_at", ""), reverse=True)

    return response(200, {"posts": posts, "count": len(posts)})


def get_post(event: dict) -> dict:
    """
    GET /posts/{id}
    Returns a single post by ID.
    """
    post_id = event.get("pathParameters", {}).get("id")
    if not post_id:
        return response(400, {"error": "Missing post id"})

    result = table.get_item(Key={"id": post_id})
    post   = result.get("Item")

    if not post:
        return response(404, {"error": f"Post {post_id} not found"})

    return response(200, {"post": post})


def update_post(event: dict) -> dict:
    """
    PUT /posts/{id}
    Updates one or more fields on an existing post.
    Only the fields present in the request body are changed.
    """
    post_id = event.get("pathParameters", {}).get("id")
    if not post_id:
        return response(400, {"error": "Missing post id"})

    body = parse_body(event)
    if not body:
        return response(400, {"error": "Request body is empty"})

    # Build a DynamoDB update expression dynamically from the body fields.
    # Only these fields are updatable — id, created_at are immutable.
    allowed = {"title", "content", "excerpt", "slug", "status"}
    updates = {k: v for k, v in body.items() if k in allowed}

    if not updates:
        return response(400, {"error": f"No updatable fields found. Allowed: {allowed}"})

    updates["updated_at"] = now()

    # If the post is being published for the first time, record published_at.
    if updates.get("status") == "published":
        # Only set published_at if it is not already set.
        existing = table.get_item(Key={"id": post_id}).get("Item", {})
        if not existing:
            return response(404, {"error": f"Post {post_id} not found"})
        if not existing.get("published_at"):
            updates["published_at"] = now()

    # Build expression: SET #title = :title, #content = :content, ...
    set_expr   = ", ".join(f"#f_{k} = :v_{k}" for k in updates)
    expr_names = {f"#f_{k}": k for k in updates}
    expr_vals  = {f":v_{k}": v for k, v in updates.items()}

    try:
        result = table.update_item(
            Key={"id": post_id},
            UpdateExpression=f"SET {set_expr}",
            ExpressionAttributeNames=names  if (names := expr_names) else None,
            ExpressionAttributeValues=expr_vals,
            ConditionExpression=Attr("id").exists(),  # Fail if post does not exist
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"error": f"Post {post_id} not found"})
        raise

    logger.info("Updated post %s", post_id)
    return response(200, {"message": "Post updated", "post": result["Attributes"]})


def delete_post(event: dict) -> dict:
    """
    DELETE /posts/{id}
    Deletes a post. Returns 404 if the post does not exist.
    """
    post_id = event.get("pathParameters", {}).get("id")
    if not post_id:
        return response(400, {"error": "Missing post id"})

    try:
        table.delete_item(
            Key={"id": post_id},
            ConditionExpression=Attr("id").exists(),
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"error": f"Post {post_id} not found"})
        raise

    logger.info("Deleted post %s", post_id)
    return response(200, {"message": f"Post {post_id} deleted"})


# ── Main handler ──────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context) -> dict:
    """
    Entry point for all API Gateway requests.
    Routes the request to the correct handler based on HTTP method and path.
    """
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path   = event.get("rawPath", "")

    logger.info("Received %s %s", method, path)

    # Handle CORS preflight requests
    if method == "OPTIONS":
        return response(200, {})

    # Route to the correct handler
    try:
        if method == "POST" and path == "/posts":
            return create_post(event)

        elif method == "GET" and path == "/posts":
            return list_posts(event)

        elif method == "GET" and path.startswith("/posts/"):
            return get_post(event)

        elif method == "PUT" and path.startswith("/posts/"):
            return update_post(event)

        elif method == "DELETE" and path.startswith("/posts/"):
            return delete_post(event)

        else:
            return response(404, {"error": f"Route not found: {method} {path}"})

    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON in request body"})

    except Exception as e:
        logger.exception("Unhandled error: %s", e)
        return response(500, {"error": "Internal server error"})
