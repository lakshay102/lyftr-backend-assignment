from collections import defaultdict
import threading

# Thread-safe in-memory storage for metrics
_lock = threading.Lock()
_http_requests_total = defaultdict(int)  # (path, status) -> count
_webhook_requests_total = defaultdict(int)  # result -> count
_request_latency_ms_count = 0


def increment_http_request(path: str, status: int):
    """Increment the HTTP request counter."""
    global _request_latency_ms_count
    with _lock:
        _http_requests_total[(path, status)] += 1
        _request_latency_ms_count += 1


def increment_webhook_result(result: str):
    """Increment the webhook result counter."""
    with _lock:
        _webhook_requests_total[result] += 1


def export_metrics() -> str:
    """Export metrics in Prometheus-style text format."""
    lines = []
    
    with _lock:
        # http_requests_total
        lines.append("# HELP http_requests_total Total number of HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for (path, status), count in _http_requests_total.items():
            lines.append(f'http_requests_total{{path="{path}",status="{status}"}} {count}')
        
        # webhook_requests_total
        lines.append("# HELP webhook_requests_total Total number of webhook requests by result")
        lines.append("# TYPE webhook_requests_total counter")
        for result, count in _webhook_requests_total.items():
            lines.append(f'webhook_requests_total{{result="{result}"}} {count}')
        
        # request_latency_ms_count
        lines.append("# HELP request_latency_ms_count Total count of request latencies recorded")
        lines.append("# TYPE request_latency_ms_count counter")
        lines.append(f"request_latency_ms_count {_request_latency_ms_count}")
        
    return "\n".join(lines) + "\n"
