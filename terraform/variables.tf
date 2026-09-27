variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Used to name all resources consistently."
  type        = string
  default     = "blog-api"
}

variable "allowed_origin" {
  description = "The CloudFront URL of your portfolio site (Project 1). Restricts CORS to your site only. Use * to allow all origins during development."
  type        = string
  default     = "https://d2eeybsp9y6gvd.cloudfront.net"
}

variable "lambda_runtime" {
  description = "Python runtime version for the Lambda function."
  type        = string
  default     = "python3.12"
}

variable "lambda_timeout" {
  description = "Maximum execution time for the Lambda function in seconds."
  type        = number
  default     = 10
}

variable "lambda_memory" {
  description = "Memory allocated to the Lambda function in MB."
  type        = number
  default     = 128
}
