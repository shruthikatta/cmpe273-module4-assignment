"""Order Service.

Owns order data. Before creating an order it queries the Inventory Service
over HTTP. If the Inventory Service is down or slow, the Order Service returns
503 Service Unavailable and keeps running.
"""

import itertools
import logging
import os
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

app = Flask(__name__)

INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://127.0.0.1:8001")
INVENTORY_TIMEOUT_SECONDS = float(os.environ.get("INVENTORY_TIMEOUT", 2))

ORDERS = {}
_order_ids = itertools.count(1)


class InventoryUnavailableError(Exception):
    pass


def check_inventory(item_id, quantity):
    url = f"{INVENTORY_URL}/inventory/{item_id}/availability"
    try:
        response = requests.get(
            url, params={"quantity": quantity}, timeout=INVENTORY_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        raise InventoryUnavailableError(str(exc)) from exc


def publish_order_created(order):
    # Notification Service is not implemented; this is where the
    # OrderCreated event would be published to a message broker.
    app.logger.info("EVENT OrderCreated: %s", order)


@app.get("/health")
def health():
    return jsonify({"service": "order", "status": "ok"})


@app.post("/orders")
def create_order():
    body = request.get_json(silent=True) or {}
    item_id = body.get("item_id")
    quantity = body.get("quantity", 1)

    if not item_id or not isinstance(quantity, int) or quantity < 1:
        return (
            jsonify({"error": "item_id (string) and quantity (positive integer) are required"}),
            400,
        )

    try:
        availability = check_inventory(item_id, quantity)
    except InventoryUnavailableError as exc:
        app.logger.error("Inventory Service call failed: %s", exc)
        return (
            jsonify(
                {
                    "error": "Inventory Service is unavailable. Please try again later.",
                    "order_status": "not_created",
                }
            ),
            503,
        )

    if availability.get("status") != "available":
        return (
            jsonify(
                {
                    "order_status": "rejected",
                    "reason": f"Item '{item_id}' is unavailable",
                    "inventory": availability,
                }
            ),
            409,
        )

    order = {
        "order_id": next(_order_ids),
        "item_id": item_id,
        "quantity": quantity,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    ORDERS[order["order_id"]] = order
    publish_order_created(order)
    return jsonify({"order_status": "created", "order": order}), 201


@app.get("/orders")
def list_orders():
    return jsonify(list(ORDERS.values()))


@app.get("/orders/<int:order_id>")
def get_order(order_id):
    order = ORDERS.get(order_id)
    if order is None:
        return jsonify({"error": "order not found"}), 404
    return jsonify(order)


if __name__ == "__main__":
    port = int(os.environ.get("ORDER_PORT", 8000))
    app.run(host="127.0.0.1", port=port)
