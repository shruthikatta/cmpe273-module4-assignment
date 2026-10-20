"""Inventory Service.

Owns item stock data. Answers availability queries from other services.
Other services never read this data directly; they must go through this API.
"""

import os

from flask import Flask, jsonify, request

app = Flask(__name__)

INVENTORY = {
    "apple": {"name": "Apple", "quantity": 10},
    "banana": {"name": "Banana", "quantity": 0},
    "laptop": {"name": "Laptop", "quantity": 3},
    "headphones": {"name": "Headphones", "quantity": 25},
}


@app.get("/health")
def health():
    return jsonify({"service": "inventory", "status": "ok"})


@app.get("/inventory")
def list_inventory():
    return jsonify(INVENTORY)


@app.get("/inventory/<item_id>/availability")
def check_availability(item_id):
    try:
        quantity = int(request.args.get("quantity", 1))
    except ValueError:
        return jsonify({"error": "quantity must be an integer"}), 400
    if quantity < 1:
        return jsonify({"error": "quantity must be at least 1"}), 400

    item = INVENTORY.get(item_id)
    if item is None:
        return jsonify({"item_id": item_id, "status": "unavailable", "reason": "unknown item"})

    available = item["quantity"] >= quantity
    return jsonify(
        {
            "item_id": item_id,
            "requested_quantity": quantity,
            "in_stock": item["quantity"],
            "status": "available" if available else "unavailable",
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("INVENTORY_PORT", 8001))
    app.run(host="127.0.0.1", port=port)
