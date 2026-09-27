"""
Unit tests for the blog posts Lambda handler.
Uses moto to mock DynamoDB so no real AWS resources are needed.

Run with:
  pip install moto boto3 pytest
  pytest tests/ -v
"""

import json
import os
import pytest

# Set env vars before importing handler
os.environ["TABLE_NAME"]             = "blog-posts"
os.environ["ALLOWED_ORIGIN"]         = "*"
os.environ["AWS_DEFAULT_REGION"]     = "eu-west-2"
os.environ["AWS_ACCESS_KEY_ID"]      = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"]  = "testing"

import boto3
from moto import mock_aws


@pytest.fixture
def dynamodb_table():
    with mock_aws():
        client = boto3.resource("dynamodb", region_name="eu-west-2")
        table  = client.create_table(
            TableName            = "blog-posts",
            KeySchema            = [{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions = [{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode          = "PAY_PER_REQUEST",
        )
        table.meta.client.get_waiter("table_exists").wait(TableName="blog-posts")
        yield table


def make_event(method, path, body=None, path_params=None, query_params=None):
    """Build a minimal API Gateway HTTP API event."""
    return {
        "requestContext": {"http": {"method": method}},
        "rawPath":        path,
        "pathParameters": path_params or {},
        "queryStringParameters": query_params,
        "body":           json.dumps(body) if body else None,
    }


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_post_success(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        event = make_event("POST", "/posts", {"title": "Hello World", "content": "My first post."})
        res   = handler.lambda_handler(event, {})

        assert res["statusCode"] == 201
        body = json.loads(res["body"])
        assert body["post"]["title"]  == "Hello World"
        assert body["post"]["status"] == "draft"
        assert "id" in body["post"]


def test_create_post_missing_fields(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        event = make_event("POST", "/posts", {"title": "No content here"})
        res   = handler.lambda_handler(event, {})

        assert res["statusCode"] == 400
        assert "required" in json.loads(res["body"])["error"]


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_posts_empty(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        event = make_event("GET", "/posts")
        res   = handler.lambda_handler(event, {})

        assert res["statusCode"] == 200
        body = json.loads(res["body"])
        assert body["posts"]  == []
        assert body["count"]  == 0


def test_list_posts_filter_by_status(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        handler.lambda_handler(make_event("POST", "/posts", {"title": "Draft", "content": "..."}), {})
        handler.lambda_handler(make_event("POST", "/posts", {"title": "Published", "content": "...", "status": "published"}), {})

        event = make_event("GET", "/posts", query_params={"status": "published"})
        res   = handler.lambda_handler(event, {})

        body = json.loads(res["body"])
        assert body["count"] == 1
        assert body["posts"][0]["title"] == "Published"


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_post_success(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        create_res = handler.lambda_handler(
            make_event("POST", "/posts", {"title": "Test Post", "content": "Content here."}), {}
        )
        post_id = json.loads(create_res["body"])["post"]["id"]

        event = make_event("GET", f"/posts/{post_id}", path_params={"id": post_id})
        res   = handler.lambda_handler(event, {})

        assert res["statusCode"] == 200
        assert json.loads(res["body"])["post"]["id"] == post_id


def test_get_post_not_found(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        event = make_event("GET", "/posts/nonexistent-id", path_params={"id": "nonexistent-id"})
        res   = handler.lambda_handler(event, {})

        assert res["statusCode"] == 404


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_post_success(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        create_res = handler.lambda_handler(
            make_event("POST", "/posts", {"title": "Original", "content": "Original content."}), {}
        )
        post_id = json.loads(create_res["body"])["post"]["id"]

        event = make_event("PUT", f"/posts/{post_id}", {"title": "Updated"}, path_params={"id": post_id})
        res   = handler.lambda_handler(event, {})

        assert res["statusCode"] == 200
        assert json.loads(res["body"])["post"]["title"] == "Updated"


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_post_success(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        create_res = handler.lambda_handler(
            make_event("POST", "/posts", {"title": "To Delete", "content": "Gone soon."}), {}
        )
        post_id = json.loads(create_res["body"])["post"]["id"]

        event = make_event("DELETE", f"/posts/{post_id}", path_params={"id": post_id})
        res   = handler.lambda_handler(event, {})

        assert res["statusCode"] == 200

        get_event = make_event("GET", f"/posts/{post_id}", path_params={"id": post_id})
        get_res   = handler.lambda_handler(get_event, {})
        assert get_res["statusCode"] == 404


def test_delete_post_not_found(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        event = make_event("DELETE", "/posts/ghost-id", path_params={"id": "ghost-id"})
        res   = handler.lambda_handler(event, {})

        assert res["statusCode"] == 404


# ── CORS ──────────────────────────────────────────────────────────────────────

def test_cors_headers_present(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        event = make_event("GET", "/posts")
        res   = handler.lambda_handler(event, {})

        assert "Access-Control-Allow-Origin" in res["headers"]


def test_options_preflight(dynamodb_table):
    with mock_aws():
        from src import handler
        handler.table = dynamodb_table

        event = make_event("OPTIONS", "/posts")
        res   = handler.lambda_handler(event, {})

        assert res["statusCode"] == 200
