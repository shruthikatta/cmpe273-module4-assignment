#!/usr/bin/env bash
# Runs the success, unavailable, and Inventory-failure scenarios end to end.
# Usage: ./demo.sh   (from the repo root, with the virtualenv set up)

set -u
cd "$(dirname "$0")"
PY=.venv/bin/python
ORDER=http://127.0.0.1:8000
INVENTORY=http://127.0.0.1:8001

post_order() {
  echo "\$ curl -X POST $ORDER/orders -H 'Content-Type: application/json' -d '$1'"
  curl -s -w '\nHTTP status: %{http_code}\n' -X POST "$ORDER/orders" \
    -H 'Content-Type: application/json' -d "$1"
  echo
}

$PY inventory_service/app.py > inventory.log 2>&1 &
INVENTORY_PID=$!
$PY order_service/app.py > order.log 2>&1 &
ORDER_PID=$!
trap 'kill $ORDER_PID $INVENTORY_PID 2>/dev/null' EXIT
sleep 2

echo "=== Both services running (Order PID $ORDER_PID, Inventory PID $INVENTORY_PID) ==="
echo "\$ curl $INVENTORY/inventory/apple/availability?quantity=2"
curl -s "$INVENTORY/inventory/apple/availability?quantity=2"
echo

echo "=== 1. Successful order (item in stock) ==="
post_order '{"item_id": "apple", "quantity": 2}'

echo "=== 2. Rejected order (item out of stock) ==="
post_order '{"item_id": "banana", "quantity": 1}'

echo "=== 3. Failure test: stopping Inventory Service (PID $INVENTORY_PID) ==="
kill $INVENTORY_PID
wait $INVENTORY_PID 2>/dev/null
sleep 1
post_order '{"item_id": "laptop", "quantity": 1}'

echo "=== 4. Order Service is still running after the failure ==="
echo "\$ curl $ORDER/health"
curl -s -w '\nHTTP status: %{http_code}\n' "$ORDER/health"
echo
echo "\$ curl $ORDER/orders"
curl -s "$ORDER/orders"
echo

echo "=== Order Service log ==="
cat order.log
