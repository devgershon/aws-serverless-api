# ──────────────────────────────────────────────
# DynamoDB Table — Blog Posts
# ──────────────────────────────────────────────
# DynamoDB is AWS's fully managed NoSQL database.
# There are no servers to manage, no schema to define upfront (beyond the key),
# and billing is per request (PAY_PER_REQUEST), so you pay nothing when idle.
#
# Key design decisions:
#   - Partition key: id (UUID string) — uniquely identifies each post
#   - No sort key needed — we retrieve posts by id or scan the whole table
#   - On-demand billing — correct for a personal project with variable traffic
#   - Point-in-time recovery — lets you restore the table to any second in the
#     last 35 days. Free to enable, protects against accidental deletes.
# ──────────────────────────────────────────────

resource "aws_dynamodb_table" "posts" {
  name         = "${var.project_name}-posts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S" # String
  }

  # Point-in-time recovery — restore to any second in the last 35 days
  point_in_time_recovery {
    enabled = true
  }

  # Encryption at rest using AWS-managed keys (free)
  server_side_encryption {
    enabled = true
  }

  # TTL — allows individual items to expire automatically.
  # Not used in the API right now but good practice to define upfront.
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-posts"
  }
}
