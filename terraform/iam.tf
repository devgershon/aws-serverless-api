# ──────────────────────────────────────────────
# IAM Execution Role for Lambda
# ──────────────────────────────────────────────
# Every Lambda function needs an execution role — an IAM role that the function
# assumes when it runs. This role controls what AWS services the function
# can interact with.
#
# We follow the principle of least privilege: the role grants only the exact
# DynamoDB actions the function needs, on the exact table it uses.
# Nothing else. No wildcard resources, no unnecessary permissions.
# ──────────────────────────────────────────────

# The trust policy — defines who can assume this role.
# Only the Lambda service can assume it.
data "aws_iam_policy_document" "lambda_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# The permission policy — defines what the role can do once assumed.
data "aws_iam_policy_document" "lambda_permissions" {
  # DynamoDB — only the actions handler.py actually calls, on this table only
  statement {
    sid    = "DynamoDBCRUD"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Scan",
    ]
    resources = [aws_dynamodb_table.posts.arn]
  }

  # CloudWatch Logs — Lambda needs this to write execution logs.
  # Without it you get no visibility into what your function is doing.
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-handler:*"]
  }
}

# The role itself
resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project_name}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json

  description = "Execution role for the ${var.project_name} Lambda function. Grants DynamoDB CRUD on the posts table and CloudWatch Logs write access only."
}

# Attach the permissions policy to the role
resource "aws_iam_role_policy" "lambda_permissions" {
  name   = "${var.project_name}-lambda-permissions"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}
