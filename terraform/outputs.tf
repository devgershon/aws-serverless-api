output "api_endpoint" {
  description = "The base URL of your blog posts API. All requests go to this URL."
  value       = aws_apigatewayv2_api.blog_api.api_endpoint
}

output "posts_url" {
  description = "The full URL for the /posts endpoint. Use this in Postman or curl."
  value       = "${aws_apigatewayv2_api.blog_api.api_endpoint}/posts"
}

output "dynamodb_table_name" {
  description = "The DynamoDB table name — used in the GitHub Actions deploy workflow."
  value       = aws_dynamodb_table.posts.name
}

output "lambda_function_name" {
  description = "The Lambda function name — useful for checking logs in CloudWatch."
  value       = aws_lambda_function.handler.function_name
}

output "lambda_function_arn" {
  description = "The Lambda function ARN."
  value       = aws_lambda_function.handler.arn
}
