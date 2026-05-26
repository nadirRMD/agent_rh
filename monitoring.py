import json
import logging
import time
from datetime import datetime


logger = logging.getLogger(__name__)

metrics = {
    "total": 0,
    "erreurs": 0,
    "latence_totale": 0,
    "cout_total": 0.0,
    "fallbacks": 0,
}


def log_request(
    question,
    latency_ms,
    tokens_in,
    tokens_out,
    error=None,
    fallback=False,
):
    # Estimer le coût (GPT-4o)
    cost = (tokens_in * 2.5 + tokens_out * 10) / 1_000_000

    metrics["total"] += 1
    metrics["latence_totale"] += latency_ms
    metrics["cout_total"] += cost

    if error:
        metrics["erreurs"] += 1
    if fallback:
        metrics["fallbacks"] += 1

    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "question": question,
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": round(cost, 6),
        "error": str(error) if error else None,
        "fallback": fallback,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))


def get_dashboard():
    n = metrics["total"] or 1
    return {
        "total_requetes": metrics["total"],
        "latence_moy_ms": metrics["latence_totale"] // n,
        "taux_erreur": f"{metrics['erreurs'] / n * 100:.1f}%",
        "cout_total": f"{metrics['cout_total']:.2f} $",
        "fallbacks": metrics["fallbacks"],
    }


def reset_metrics():
    metrics["total"] = 0
    metrics["erreurs"] = 0
    metrics["latence_totale"] = 0
    metrics["cout_total"] = 0.0
    metrics["fallbacks"] = 0


def measure_latency(start_time):
    return int((time.perf_counter() - start_time) * 1000)
