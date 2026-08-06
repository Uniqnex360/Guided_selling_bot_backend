# Guided Selling Chatbot – Product Assistant GPT

## Project Overview & Introduction

### What the Tool Does
The Guided Selling Chatbot (Product Assistant GPT) is an AI-powered assistant designed to help users discover, compare, and select products through a conversational interface. It leverages advanced natural language processing to understand user queries and provide tailored product recommendations, details, and comparisons.

### Core Purpose
To streamline the product discovery and selection process for end-users by providing intelligent, context-aware assistance, reducing friction in e-commerce and product support scenarios.

### High-Level Problem It Solves
- Reduces user effort in finding suitable products
- Automates product Q&A and support
- Enhances user engagement and satisfaction

---

## Technical Stack

### Backend Technologies
- Python 3.x
- Django (Web framework)

### Frontend Technologies
- React

### Databases
-mongodb



### Infrastructure-as-Code
- Docker, Docker Compose

### DevOps Tools
- Git, GitHub Actions (or other CI/CD)
- Docker

---

## System Architecture

### Cloud Architecture Diagram Description
- Web clients interact with Django backend via REST endpoints
- Django backend communicates with PostgreSQL/SQLite DB

### Deployment Architecture
- Dockerized services: web, worker, db
- Docker Compose for local orchestration

### Networking Overview
- HTTP(S) traffic to web server
- (If cloud) Security groups/firewall rules restrict access



### Service-to-Service Interactions
- Django app → DB (ORM queries)
- Django app → Celery (task dispatch)

### Data Flow Description
1. User sends query via web UI
2. Django processes request, may enqueue Celery task
3. Celery worker processes task, updates DB
4. Django returns response to user

---

## Entity & Data Model Documentation

### List of All Entities
- User
- Product
- ProductCategory
- ChatSession
- Message
- (Custom entities as per business logic)

### Entity-Relationship Descriptions
- User ↔ ChatSession (1:N)
- ChatSession ↔ Message (1:N)
- Product ↔ ProductCategory (N:1)

### Schemas, Attributes, Constraints
- User: id, username, email, password, ...
- Product: id, name, description, price, category_id, ...
- ProductCategory: id, name, ...
- ChatSession: id, user_id, started_at, ...
- Message: id, session_id, sender, content, timestamp, ...

### ORM Modeling Notes
- Django ORM models in `guidedProductAssistant/models.py`
- Use ForeignKey for relationships
- Use migrations for schema changes

---

## Celery Worker Architecture

### What Tasks Exist
- Product data import
- Long-running AI inference

### How Tasks Are Scheduled

### Retry Logic
- Configurable retries per task (default: 3)
- Exponential backoff supported

### Error Handling
- Failed tasks logged
- Alerts for repeated failures


### Scaling Strategy
- Increase worker count for higher throughput
- Use autoscaling in cloud

---

## API Documentation

### Full Endpoint List
- `/api/products/` – List products (GET)
- `/api/products/<id>/` – Product detail (GET)
- `/api/chat/` – Start chat session (POST)
- `/api/chat/<session_id>/message/` – Send/receive message (POST/GET)
- (See `urls.py` for full list)

### HTTP Methods
- GET, POST, PUT, DELETE (RESTful)

### Request/Response Examples
- **GET /api/products/**
  - Request: None
  - Response: `[ { "id": 1, "name": "Product A", ... }, ... ]`
- **POST /api/chat/**
  - Request: `{ "user_id": 1 }`
  - Response: `{ "session_id": "abc123" }`

### Authentication/Authorization
- Token-based (JWT or DRF TokenAuth)
- Session-based (Django default)

### Error Codes
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 500 Internal Server Error

### Pagination/Filtering Rules
- Standard limit/offset pagination
- Filtering by query params (e.g., `?category=...`)

### Webhooks
- (None by default; add as needed)

---

## Environment Setup

### Local Development Environment
- Python 3.x
- Docker & Docker Compose
- Node.js (if using advanced frontend)

### Environment Variables List & Purpose
- `DJANGO_SECRET_KEY`: Django secret
- `DATABASE_URL`: DB connection string
- `REDIS_URL`: Redis broker URL
- `CELERY_BROKER_URL`: Celery broker
- `DEBUG`: Enable/disable debug mode
- (See `.env` or settings.py)

### Configurations for Dev/Staging/Production
- Separate `.env` files or environment variable sets
- Debug, logging, DB, and allowed hosts differ per environment

### Docker Setup
- `docker-compose up` to start all services
- `Dockerfile` for app image
- Volumes for DB persistence


## Deployment & CI/CD

### Pipeline Steps
1. Lint & test
2. Build Docker image
3. Push to registry
4. Deploy to staging
5. Run integration tests
6. Deploy to production


### Build → Release → Deploy Lifecycle
- Automated via GitHub Actions or similar



## Security Considerations

### API Security
- HTTPS enforced
- Auth required for sensitive endpoints

### Secrets Management
# OPEN_AI_KEY=""
# MONGODB_HOST = mongodb+srv://techteam:Tech!123@dataextraction.h6crc.mongodb.net/
# MONGODB_NAME = ai_assistant
# GOOGLE_GEMINI_API_KEY=""

### Access Control
- Role-based permissions (if needed)

### Data Encryption
- In-transit (HTTPS)

---

## Maintenance & Observability




## Appendices

### Glossary
- **Celery**: Distributed task queue
- **Redis**: In-memory data store
- **ORM**: Object-relational mapping
- **JWT**: JSON Web Token

### Troubleshooting
- **Docker won’t start**: Check Docker daemon, permissions
- **DB connection errors**: Validate `DATABASE_URL`, DB status
- **Celery not processing**: Check Redis, worker logs
- **Common errors and fixes**: See logs, check environment variables

---

