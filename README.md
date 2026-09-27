# Blog Posts API — Serverless on AWS

**Live API:** https://t0tn9g17b7.execute-api.eu-west-2.amazonaws.com/posts &nbsp;·&nbsp; **Author:** [devgershon](https://github.com/devgershon)

A serverless REST API that powers the blog section of my [portfolio site](https://d2eeybsp9y6gvd.cloudfront.net). Lambda runs the code, API Gateway routes the requests, DynamoDB stores the posts. When the API is idle, nothing runs and nothing is charged.

---

## Architecture

```
Browser / curl / Postman
        |
        v
API Gateway (HTTP API)  — routing, CORS, access logging
        |
        v
  Lambda (Python 3.12)  — business logic, CRUD operations
        |
        v
    DynamoDB             — NoSQL storage, on-demand billing
        |
  CloudWatch Logs        — execution logs and API access logs

All infrastructure provisioned by Terraform.
Code updates deployed by GitHub Actions (tests run first).
```

---

## Endpoints

| Method | Path | What it does |
|---|---|---|
| `POST` | `/posts` | Create a new blog post |
| `GET` | `/posts` | List all posts (filter by `?status=published`) |
| `GET` | `/posts/{id}` | Get a single post by ID |
| `PUT` | `/posts/{id}` | Update one or more fields on a post |
| `DELETE` | `/posts/{id}` | Delete a post |

### Post object

```json
{
  "id":           "uuid",
  "title":        "My first post",
  "content":      "Full post content...",
  "excerpt":      "First 150 chars auto-generated if not provided",
  "slug":         "my-first-post",
  "status":       "draft | published",
  "published_at": "2025-05-22T10:00:00+00:00",
  "created_at":   "2025-05-22T09:00:00+00:00",
  "updated_at":   "2025-05-22T09:00:00+00:00"
}
```

---

## Quick test with curl

```bash
API="https://t0tn9g17b7.execute-api.eu-west-2.amazonaws.com"

# Create a post
curl -X POST "$API/posts" \
  -H "Content-Type: application/json" \
  -d '{"title": "Hello World", "content": "My first serverless blog post.", "status": "published"}'

# List all published posts
curl "$API/posts?status=published"

# Get a specific post
curl "$API/posts/YOUR-POST-ID"

# Update a post
curl -X PUT "$API/posts/YOUR-POST-ID" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'

# Delete a post
curl -X DELETE "$API/posts/YOUR-POST-ID"
```

---

## Deploy it yourself

You need an AWS account (free tier works), the AWS CLI configured, Terraform, and Python 3.12.

### 1. Clone and configure

```bash
git clone https://github.com/devgershon/aws-serverless-api.git
cd aws-serverless-api
```

Open `terraform/variables.tf` and set `allowed_origin` to your site URL. Use `"*"` if you just want to test without a frontend.

### 2. IAM permissions your user needs

Before running Terraform, make sure your IAM user has these policies attached. You can do this in the AWS console under IAM -> Users -> your user -> Permissions:

- `AWSLambda_FullAccess`
- `AmazonAPIGatewayAdministrator`
- `AmazonDynamoDBFullAccess`
- `IAMFullAccess`
- `CloudWatchLogsFullAccess`

### 3. Deploy

```bash
cd terraform
terraform init
terraform apply
```

Creates the DynamoDB table, Lambda function, API Gateway, IAM role, and CloudWatch log groups. Takes about a minute. When done:

```
api_endpoint         = "https://xxx.execute-api.eu-west-2.amazonaws.com"
posts_url            = "https://xxx.execute-api.eu-west-2.amazonaws.com/posts"
lambda_function_name = "blog-api-handler"
dynamodb_table_name  = "blog-api-posts"
```

### 4. Set up automated deploys

Add these four secrets under `Settings -> Secrets -> Actions`:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your IAM access key |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret key |
| `LAMBDA_FUNCTION_NAME` | From `terraform output lambda_function_name` |
| `API_ENDPOINT` | From `terraform output api_endpoint` |

Every push to `main` runs the tests first and deploys only if they pass.

### 5. Connect to your portfolio site

Open `portfolio-blog-update.js`, drop in your API endpoint, and paste the script into your `index.html` just before `</body>`. The blog section will fetch real posts from DynamoDB instead of showing static content.

---

## Repo structure

```
aws-serverless-api/
├── terraform/
│   ├── main.tf           # Provider config
│   ├── variables.tf      # Region, project name, allowed origin
│   ├── dynamodb.tf       # Posts table, PITR, encryption
│   ├── iam.tf            # Least-privilege execution role
│   ├── lambda.tf         # Function, packaging, CloudWatch log group
│   ├── api_gateway.tf    # HTTP API, routes, Lambda integration, CORS
│   └── outputs.tf        # API endpoint, function name, table name
├── src/
│   └── handler.py        # All 5 endpoints in one Python file
├── tests/
│   └── test_handler.py   # Unit tests using moto (no real AWS needed)
├── .github/
│   └── workflows/
│       └── deploy.yml    # Test then deploy on every push to main
├── portfolio-blog-update.js  # Connects Project 1 portfolio to this API
└── README.md
```

---

## Design decisions

**HTTP API, not REST API.** API Gateway offers two products. HTTP API is the newer one — cheaper, lower latency, and simpler to configure for Lambda integrations. REST API adds features like request validation and usage plans that a blog API does not need.

**One Lambda function for all routes.** Some people split APIs into one function per endpoint. I kept it as one function because at this scale it is easier to deploy, easier to read, and the routing logic in the handler is straightforward.

**Least-privilege IAM.** The Lambda execution role can only call `GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, and `Scan` on this specific DynamoDB table. Nothing else. Keeping permissions tight limits what can go wrong if something is misconfigured.

**CORS locked to the portfolio origin.** `Access-Control-Allow-Origin` is set to the CloudFront URL of my portfolio site rather than `*`. Only that origin can call the API from a browser.

---

## What I actually ran into

**IAM policy attachments need the right permissions.** When I tried to attach policies to my IAM user via the CLI, it threw an AccessDenied error because the user did not have permission to manage its own policies. Had to go into the AWS console and attach them manually from the root account. Straightforward fix once I understood what was happening.

**CloudWatch Logs needs an explicit policy.** Lambda and API Gateway both write logs to CloudWatch, but Terraform cannot create the log groups unless your IAM user has `CloudWatchLogsFullAccess`. It is not bundled with the Lambda or API Gateway policies, which is not obvious until Terraform fails halfway through an apply and you have to track down which resource errored.

**moto makes testing practical.** Without it, every test would need a real DynamoDB table in AWS — slow, costs money, and awkward in CI. moto intercepts boto3 calls and runs a local DynamoDB simulation. Tests finish in seconds with no AWS involvement at all.

---

## Part of a series

| # | Project | Stack | Status |
|---|---|---|---|
| 1 | Static site on AWS | S3, CloudFront, ACM, Terraform, GitHub Actions | Live |
| 2 | **Serverless REST API** | Lambda, API Gateway, DynamoDB, IAM, Terraform | Live |
| 3 | Containerised app + CI/CD | Docker, ECR, ECS Fargate, GitHub Actions | Coming soon |
| 4 | Production VPC architecture | VPC, subnets, NAT, ALB, EC2, RDS, Terraform | Planned |

---

## Contact

[devgershon@gmail.com](mailto:devgershon@gmail.com) &nbsp;·&nbsp; [github.com/devgershon](https://github.com/devgershon) &nbsp;·&nbsp; [linkedin.com/in/gershonen](https://www.linkedin.com/in/gershonen/)
# triggered
# triggered
