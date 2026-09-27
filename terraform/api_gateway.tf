# ──────────────────────────────────────────────
# API Gateway — HTTP API
# ──────────────────────────────────────────────
# API Gateway is the front door to your Lambda function. It receives HTTP
# requests, routes them to Lambda, and returns the response.
#
# We use HTTP API (not REST API). HTTP API is:
#   - ~70% cheaper than REST API
#   - Lower latency
#   - Simpler to configure for Lambda proxy integrations
#   - Supports CORS configuration natively
#
# The trade-off: HTTP API has fewer advanced features (no usage plans,
# no request validation, no caching). For a blog posts API, none of
# those are needed.
# ──────────────────────────────────────────────

# The HTTP API
resource "aws_apigatewayv2_api" "blog_api" {
  name          = "${var.project_name}-http-api"
  protocol_type = "HTTP"
  description   = "Blog posts REST API"

  # CORS configuration — allows your portfolio site to call this API from
  # the browser. Without this, browsers block cross-origin requests.
  cors_configuration {
    allow_origins = [var.allowed_origin]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }
}

# Lambda integration — tells API Gateway to invoke our Lambda function
# and pass the full request as an event (proxy integration).
resource "aws_apigatewayv2_integration" "lambda" {
  api_id             = aws_apigatewayv2_api.blog_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.handler.invoke_arn
  payload_format_version = "2.0" # Required for HTTP API Lambda proxy
}

# Routes — maps HTTP methods + paths to the Lambda integration.
# $default catches all routes not explicitly defined — our handler
# does the routing internally based on method and path.
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.blog_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Stage — a named deployment of your API.
# $default is the auto-deployed stage for HTTP APIs.
# auto_deploy means changes deploy immediately without a manual deploy step.
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.blog_api.id
  name        = "$default"
  auto_deploy = true

  # Access logging — sends API Gateway logs to CloudWatch.
  # Useful for debugging routing issues and monitoring traffic.
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      sourceIp       = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      protocol       = "$context.protocol"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }
}

# CloudWatch Log Group for API Gateway access logs
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${var.project_name}"
  retention_in_days = 14
}

# Lambda resource policy — grants API Gateway permission to invoke the function.
# Without this, API Gateway gets a 403 when it tries to call Lambda.
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.blog_api.execution_arn}/*/*"
}
