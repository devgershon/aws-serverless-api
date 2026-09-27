# Blog Posts API — Serverless on AWS

**Live API:** `https://YOUR_API_ENDPOINT/posts` &nbsp;·&nbsp; **Author:** [devgershon](https://github.com/devgershon)

A serverless REST API that powers the blog section of my [portfolio site](https://d2eeybsp9y6gvd.cloudfront.net). No servers to manage, no capacity to plan for. Lambda runs the code, API Gateway handles the routing, DynamoDB stores the data. When nobody is hitting the API, it costs nothing.

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
# Set your API endpoint
API="https://YOUR_API_ENDPOINT"

# Create a post
curl -X POST "$API/posts" \
  -H "Content-Type: application/json" \
  -d '{"title": "Hello World", "content": "My first serverless blog post.", "status": "published"}'

# List all published posts
curl "$API/posts?status=published"

# Get a specific post (replace ID with the one returned above)
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

This is for anyone who wants to clone the repo and run their own version. You need an AWS account (free tier works), the AWS CLI, Terraform, and Python 3.12.

### 1. Clone and configure

```bash
git clone https://github.com/devgershon/aws-serverless-api.git
cd aws-serverless-api
```

Open `terraform/variables.tf` and set `allowed_origin` to your own site URL, or `"*"` if you just want to get it running quickly without a frontend.

### 2. Deploy the infrastructure

```bash
cd terraform
terraform init
terraform apply
```

This creates the DynamoDB table, Lambda function, API Gateway, IAM role, and CloudWatch log groups. Takes about a minute. When it finishes you get:

```
api_endpoint         = "https://abc123.execute-api.eu-west-2.amazonaws.com"
posts_url            = "https://abc123.execute-api.eu-west-2.amazonaws.com/posts"
lambda_function_name = "blog-api-handler"
dynamodb_table_name  = "blog-api-posts"
```

### 3. Test it

```bash
curl https://abc123.execute-api.eu-west-2.amazonaws.com/posts
```

### 4. Set up automated deploys

Add these four secrets under `Settings -> Secrets -> Actions` in your GitHub repo:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your IAM access key |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret key |
| `LAMBDA_FUNCTION_NAME` | From `terraform output lambda_function_name` |
| `API_ENDPOINT` | From `terraform output api_endpoint` |

From here, every push to `main` runs the tests and deploys if they pass.

### 5. Connect it to your portfolio site

Open `portfolio-blog-update.js`, replace `API_BASE_URL` with your API endpoint, and drop the script into your `index.html` just before `</body>`. The blog section will pull real posts from DynamoDB instead of showing static placeholders.

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
├── portfolio-blog-update.js  # Drop into Project 1 to connect the two
└── README.md
```

---

## Design decisions worth explaining

**HTTP API, not REST API.** API Gateway has two products and the naming is confusing. HTTP API is the newer one — cheaper, faster, and simpler for Lambda proxy integrations. REST API has extra features like request validation and usage plans that this project does not need. Using HTTP API here was the right call and saves money.

**One Lambda function for all routes.** You could split this into five separate functions, one per endpoint. I did not because for a project at this scale, one function is easier to deploy and reason about. The routing logic lives in the handler and is easy to follow.

**Least-privilege IAM.** The execution role only has permission to call `GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, and `Scan` on this specific DynamoDB table. Nothing wider. If the function were somehow compromised, the blast radius is limited to the posts table.

**CORS locked to the portfolio origin.** The `Access-Control-Allow-Origin` header is set to the CloudFront URL of my portfolio site, not `*`. This means only my site can call the API from a browser. Changed to `*` during development, then tightened before deploying.

---

## What I actually ran into

**API Gateway has two completely different products with similar names.** HTTP API and REST API are not the same thing despite what the name implies. I went down the REST API path initially before realising HTTP API was what I needed and was cheaper. The AWS documentation makes this harder to figure out than it should be.

**IAM has two separate policies and you need both right.** The trust policy (who can use the role) and the permission policy (what the role can do) are distinct documents. Getting the trust policy wrong means the Lambda function cannot even start — it cannot assume its own role. Getting the permission policy wrong means it starts but cannot touch DynamoDB. Both need to be correct before anything works.

**Cold starts exist and are worth understanding.** The first time Lambda runs after sitting idle, there is a delay while AWS provisions the execution environment. For a blog API this is completely fine. But it is something you need to understand before recommending Lambda for anything latency-sensitive.

**moto saved a lot of time.** Testing DynamoDB code without moto means you need a real AWS table to run your tests against, which is slow and costs money in CI. moto intercepts the boto3 calls and simulates DynamoDB locally. The tests run in a few seconds with zero AWS cost.

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
