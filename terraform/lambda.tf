# ──────────────────────────────────────────────
# Lambda Function
# ──────────────────────────────────────────────
# Lambda runs your code in response to events — in this case, HTTP requests
# from API Gateway. You do not manage any servers. AWS handles scaling,
# patching, and availability automatically.
#
# Terraform packages the source code into a zip file and uploads it to Lambda.
# The archive_file data source does the zipping.
# ──────────────────────────────────────────────

# Zip the src/ directory into a deployment package.
# Terraform recreates the zip whenever the source files change.
data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/../build/lambda.zip"
}

# The Lambda function
resource "aws_lambda_function" "handler" {
  function_name = "${var.project_name}-handler"
  description   = "Blog posts CRUD API — handles all HTTP routes"

  # The deployment package
  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256

  # handler.py file, lambda_handler function inside it
  handler = "handler.lambda_handler"
  runtime = var.lambda_runtime

  role    = aws_iam_role.lambda_exec.arn
  timeout = var.lambda_timeout
  memory_size = var.lambda_memory

  # Environment variables injected into the function at runtime.
  # The function reads these with os.environ["TABLE_NAME"] etc.
  environment {
    variables = {
      TABLE_NAME     = aws_dynamodb_table.posts.name
      ALLOWED_ORIGIN = var.allowed_origin
    }
  }

  tags = {
    Name = "${var.project_name}-handler"
  }

  depends_on = [
    aws_iam_role_policy.lambda_permissions,
    aws_cloudwatch_log_group.lambda_logs,
  ]
}

# CloudWatch Log Group for Lambda logs.
# Creating this explicitly (rather than letting Lambda auto-create it) means
# Terraform manages its lifecycle and retention policy.
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-handler"
  retention_in_days = 14  # Keep logs for 14 days — adjust as needed
}
