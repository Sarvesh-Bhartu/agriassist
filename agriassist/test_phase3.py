"""
Quick test of Phase 3 services.
Run: uv run python test_phase3.py
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.hash_service import generate_land_hash, generate_farmer_ref, farm_uuid_to_uint256
from app.services.blockchain_client import blockchain_client


# ─── Mock Farm Object ─────────────────────────────────────────────────────────
class MockFarm:
    id = "test-farm-uuid-0001"
    farmer_id = "test-farmer-uuid-001"
    soil_type = "black"
    area_hectares = "2.50"
    water_source = "well"
    irrigation_type = "drip"
    polygon_coordinates = [{"lat": 18.52, "lon": 73.85}, {"lat": 18.53, "lon": 73.86}]


def test_hash_service():
    print("\n--- Testing hash_service ---")
    farm = MockFarm()

    land_hash = generate_land_hash(farm)
    farmer_ref = generate_farmer_ref(farm.farmer_id, farm.id)
    numeric_id = farm_uuid_to_uint256(farm.id)

    print(f"land_hash    : {land_hash}")
    print(f"farmer_ref   : {farmer_ref}")
    print(f"numeric_id   : {numeric_id}")

    # Verify determinism
    assert generate_land_hash(farm) == land_hash, "FAIL: land_hash not deterministic!"
    assert generate_farmer_ref(farm.farmer_id, farm.id) == farmer_ref, "FAIL: farmer_ref not deterministic!"
    assert len(land_hash) == 66, f"FAIL: land_hash length {len(land_hash)} != 66"
    assert land_hash.startswith("0x"), "FAIL: land_hash must start with 0x"
    print("Hash service: PASSED")


async def test_blockchain_client():
    print("\n--- Testing blockchain_client (health check) ---")
    health = await blockchain_client.health_check()
    print(f"health response: {health}")

    if health.get("status") == "ok":
        print("Blockchain client health: PASSED")
    else:
        print("Blockchain API not reachable (is 'node server.js' running?)")
        print("Skipping approve test.")
        return

    print("\n--- Testing blockchain_client.approve_farm (REAL TX) ---")
    # Use a unique test farm id to avoid ALREADY_APPROVED
    import hashlib
    test_farm_id = "phase3-test-farm-001"
    numeric = farm_uuid_to_uint256(test_farm_id)
    land_hash = "0x" + hashlib.sha256(b"test_land_data_phase3").hexdigest()
    farmer_ref = "0x" + hashlib.sha256(b"test_farmer_ref_phase3").hexdigest()

    result = await blockchain_client.approve_farm(numeric, farmer_ref, land_hash)
    print(f"approve result: {result}")

    if result.get("success"):
        print(f"Blockchain approve: PASSED")
        print(f"  txHash      : {result['txHash']}")
        print(f"  blockNumber : {result['blockNumber']}")
        print(f"  polygonScan : {result.get('polygonScanUrl')}")
    elif result.get("code") == "ALREADY_APPROVED":
        print("Blockchain approve: OK (ALREADY_APPROVED - test already ran before)")
    else:
        print(f"Blockchain approve: FAILED - {result.get('error')}")


def main():
    test_hash_service()
    asyncio.run(test_blockchain_client())
    print("\nPhase 3 tests complete.")


if __name__ == "__main__":
    main()
