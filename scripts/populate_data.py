"""
Standalone script to populate the Blog Portal with 10 users and 100 articles.
Each user gets 5 public and 5 private articles.

Usage (on EC2):
    cd /opt/blogportal
    python3 scripts/populate_data.py

Requires: requests (pip3 install requests)
Uses the admin account to create users, then logs in as each user to create articles.
"""

import argparse
import random
import requests
import sys

ADMIN_USER = "admin"

USERS = [
    {"username": f"user{i}", "email": f"user{i}@blogportal.local", "password": f"Password{i}!"}
    for i in range(1, 11)
]

ARTICLE_TOPICS = [
    ("Understanding Database Indexing", "Database indexing is a critical technique for improving query performance. An index is a data structure that allows the database engine to locate rows quickly without scanning the entire table. Common index types include B-tree, hash, and full-text indexes. Proper indexing can reduce query time from seconds to milliseconds, but over-indexing can slow down write operations. The key is to analyze your query patterns and create indexes that match your most frequent access paths."),
    ("Introduction to Microservices", "Microservices architecture breaks down a monolithic application into small, independently deployable services. Each service owns its data and communicates via APIs. Benefits include independent scaling, technology diversity, and fault isolation. Challenges include distributed data management, service discovery, and increased operational complexity. Start with a monolith and extract services as boundaries become clear."),
    ("AWS Lambda Best Practices", "AWS Lambda enables serverless computing where you pay only for execution time. Key best practices include keeping functions small and focused, minimizing cold starts by choosing appropriate memory settings, using environment variables for configuration, and implementing proper error handling. Connection pooling for databases is essential since Lambda functions are ephemeral."),
    ("React State Management Patterns", "React offers several approaches to state management. Local state with useState works for component-specific data. Context API handles shared state without prop drilling. For complex applications, consider Redux or Zustand. The choice depends on application size, team familiarity, and performance requirements. Start simple and add complexity only when needed."),
    ("Python Flask REST API Design", "Flask is a lightweight Python web framework ideal for building REST APIs. Use blueprints to organize routes, SQLAlchemy for database access, and marshmallow for serialization. Implement proper error handling with custom exception classes. Use decorators for authentication and authorization. Keep your route handlers thin by moving business logic to service modules."),
    ("Container Security Fundamentals", "Container security starts with using minimal base images and scanning for vulnerabilities. Never run containers as root. Use read-only file systems where possible. Implement network policies to restrict container communication. Regularly update base images and dependencies. Use secrets management tools instead of environment variables for sensitive data."),
    ("CI/CD Pipeline Optimization", "An efficient CI/CD pipeline reduces deployment time and increases reliability. Cache dependencies between builds, run tests in parallel, and use incremental builds. Implement canary deployments for gradual rollouts. Monitor pipeline metrics like build time, failure rate, and deployment frequency. Automate rollbacks for failed deployments."),
    ("Monitoring and Observability", "Observability goes beyond traditional monitoring by providing insights into system behavior through metrics, logs, and traces. Implement structured logging with correlation IDs. Use distributed tracing to follow requests across services. Set up meaningful alerts based on SLOs rather than arbitrary thresholds. Dashboards should tell a story about system health."),
    ("Infrastructure as Code with CloudFormation", "CloudFormation enables you to define AWS infrastructure in YAML or JSON templates. Use parameters for environment-specific values, mappings for region-specific configurations, and outputs for cross-stack references. Implement change sets to preview modifications before applying them. Use nested stacks for reusable components."),
    ("SQL Query Optimization Techniques", "Slow SQL queries are a common cause of application performance issues. Start by analyzing execution plans to identify full table scans. Add appropriate indexes for frequently queried columns. Avoid SELECT * and fetch only needed columns. Use JOINs instead of subqueries where possible. Consider query caching and connection pooling for high-traffic applications."),
]


def admin_login():
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if resp.status_code != 200:
        print(f"Admin login failed: {resp.status_code} {resp.text}")
        sys.exit(1)
    return resp.json()["token"]


def create_user(admin_token, user):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.post(f"{BASE_URL}/users", json=user, headers=headers)
    if resp.status_code == 201:
        print(f"  Created user: {user['username']}")
    elif resp.status_code == 400 and "already" in resp.text.lower():
        print(f"  User already exists: {user['username']}")
    else:
        print(f"  Failed to create {user['username']}: {resp.status_code} {resp.text}")


def user_login(username, password):
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    if resp.status_code != 200:
        print(f"  Login failed for {username}: {resp.status_code}")
        return None
    return resp.json()["token"]


def create_article(token, title, body, visibility):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/articles", json={
        "title": title,
        "body": body,
        "visibility": visibility,
    }, headers=headers)
    if resp.status_code == 201:
        print(f"    Created {visibility} article: {title[:50]}...")
    else:
        print(f"    Failed: {resp.status_code} {resp.text[:100]}")


def main():
    parser = argparse.ArgumentParser(description="Populate blog portal with test data")
    parser.add_argument("--url", required=True, help="Base URL (e.g., http://<ALB-DNS-NAME>)")
    parser.add_argument("--password", required=True, help="Admin account password")
    args = parser.parse_args()

    global BASE_URL, ADMIN_PASS
    BASE_URL = args.url.rstrip("/") + "/api"
    ADMIN_PASS = args.password

    print("=== Blog Portal Data Population ===\n")

    print("1. Logging in as admin...")
    admin_token = admin_login()
    print("   Admin login successful.\n")

    print("2. Creating 10 users...")
    for user in USERS:
        create_user(admin_token, user)
    print()

    print("3. Creating articles for each user (5 public + 5 private)...")
    for user in USERS:
        print(f"\n  User: {user['username']}")
        token = user_login(user["username"], user["password"])
        if not token:
            continue

        topics = random.sample(ARTICLE_TOPICS, 10)
        for i, (title, body) in enumerate(topics):
            visibility = "public" if i < 5 else "private"
            user_title = f"{title} - by {user['username']}"
            create_article(token, user_title, body, visibility)

    print("\n=== Done! Created 10 users with 100 articles (50 public, 50 private) ===")


if __name__ == "__main__":
    main()
