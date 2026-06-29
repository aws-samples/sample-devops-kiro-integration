"""
Trigger high CPU utilization on the blog portal EC2 instance (t2.micro).
Sends a flood of concurrent requests to exhaust the small instance's CPU.

Usage:
    pip install requests
    python3 scripts/trigger_high_cpu.py --url http://<ALB-DNS-NAME>
"""

import argparse
import threading
import time
import requests

ADMIN_USER = "admin"


def login(base_url, password):
    resp = requests.post(f"{base_url}/api/auth/login", json={"username": ADMIN_USER, "password": password})
    resp.raise_for_status()
    return resp.json()["token"]


def hammer_endpoint(base_url, token, password, thread_id, duration, results):
    """Continuously hit endpoints as fast as possible."""
    headers = {"Authorization": f"Bearer {token}"}
    end_time = time.time() + duration
    count = 0
    errors = 0

    while time.time() < end_time:
        try:
            # Mix of endpoints to create varied load
            requests.get(f"{base_url}/api/articles/public", headers=headers, timeout=30)
            count += 1

            # Create an article (write-heavy, more CPU)
            requests.post(f"{base_url}/api/articles", headers=headers, json={
                "title": f"Load test article {thread_id}-{count}",
                "body": "x " * 500,  # 500 words
                "visibility": "public",
            }, timeout=30)
            count += 1

            # Login again (bcrypt is CPU-intensive)
            requests.post(f"{base_url}/api/auth/login", json={
                "username": ADMIN_USER, "password": password
            }, timeout=30)
            count += 1

        except Exception:
            errors += 1

    results[thread_id] = {"requests": count, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description="Trigger high CPU on blog portal")
    parser.add_argument("--url", required=True, help="ALB URL (e.g., http://blog-portal-ALB-123.us-east-1.elb.amazonaws.com)")
    parser.add_argument("--password", required=True, help="Admin account password")
    parser.add_argument("--threads", type=int, default=50, help="Number of concurrent threads (default: 50)")
    parser.add_argument("--duration", type=int, default=120, help="Duration in seconds (default: 120)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    print(f"=== High CPU Load Test ===")
    print(f"Target: {base_url}")
    print(f"Threads: {args.threads}")
    print(f"Duration: {args.duration}s\n")

    print("Logging in as admin...")
    token = login(base_url, args.password)
    print("Login successful.\n")

    print(f"Launching {args.threads} threads for {args.duration} seconds...")
    print("(bcrypt login calls are especially CPU-heavy on t2.micro)\n")

    results = {}
    threads = []
    start = time.time()

    for i in range(args.threads):
        t = threading.Thread(target=hammer_endpoint, args=(base_url, token, args.password, i, args.duration, results))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    elapsed = time.time() - start
    total_requests = sum(r["requests"] for r in results.values())
    total_errors = sum(r["errors"] for r in results.values())

    print(f"\n=== Results ===")
    print(f"Total requests: {total_requests}")
    print(f"Total errors:   {total_errors}")
    print(f"Duration:       {elapsed:.1f}s")
    print(f"RPS:            {total_requests / elapsed:.1f}")


if __name__ == "__main__":
    main()
