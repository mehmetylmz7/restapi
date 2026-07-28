import time
import uuid
import concurrent.futures
from flask import Blueprint, render_template, request, jsonify
from services.customer_service import create_customer, delete_customer

test_bp = Blueprint("test_routes", __name__)

@test_bp.route("/test-thread")
def test_thread():
    return render_template("test_thread.html")


def generate_mock_customers(count=30):
    customers = []
    run_id = str(uuid.uuid4())[:8]
    for i in range(1, count + 1):
        customers.append({
            "name": f"Mock User {i} ({run_id})",
            "email": f"mockuser{i}_{run_id}@example.com"
        })
    return customers


@test_bp.route("/api/test-thread/run-sequential", methods=["POST"])
def run_sequential():
    customers_data = generate_mock_customers(30)
    results = []
    start_time = time.time()
    
    for c in customers_data:
        res = create_customer(c["name"], c["email"])
        results.append(res)
        
    elapsed = time.time() - start_time
    
    return jsonify({
        "success": True, 
        "mode": "sequential", 
        "elapsed_seconds": round(elapsed, 2),
        "results": results
    })


@test_bp.route("/api/test-thread/run-threaded", methods=["POST"])
def run_threaded():
    customers_data = generate_mock_customers(30)
    results = []
    start_time = time.time()
    
    def create_c(c_data):
        return create_customer(c_data["name"], c_data["email"])
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_c, c) for c in customers_data]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)
            
    elapsed = time.time() - start_time
    
    return jsonify({
        "success": True, 
        "mode": "threaded", 
        "elapsed_seconds": round(elapsed, 2),
        "results": results
    })


@test_bp.route("/api/test-thread/delete", methods=["POST"])
def delete_test_customers():
    data = request.json
    customer_ids = data.get("customer_ids", [])
    
    if not customer_ids:
        return jsonify({"success": False, "error": "No customer IDs provided"}), 400
        
    results = []
    # Deletion can also be threaded for speed since it's 30 records
    def del_c(cid):
        return delete_customer(cid)
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(del_c, cid): cid for cid in customer_ids}
        for future in concurrent.futures.as_completed(futures):
            cid = futures[future]
            try:
                res = future.result()
                results.append({"id": cid, "deleted": True})
            except Exception as e:
                results.append({"id": cid, "deleted": False, "error": str(e)})
                
    return jsonify({"success": True, "results": results})
