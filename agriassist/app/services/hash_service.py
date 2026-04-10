"""
hash_service.py — AgriAssist Blockchain Hashing

Generates deterministic SHA-256 hashes for:
  - landHash  : hash of canonical farm data → stored on-chain as proof
  - farmerRef : hash linking farmer+farm IDs → stored on-chain as reference

Rules:
  - Canonical JSON (sort_keys=True) — same data always produces same hash
  - Output is "0x" + 64 hex chars (32 bytes), ready for bytes32 in Solidity
"""
import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.farm import Farm


def generate_land_hash(farm: "Farm") -> str:
    """
    SHA-256 hash of canonical farm data.
    This is the tamper-proof fingerprint of the farm record at approval time.

    Includes: farm_id, farmer_id, soil_type, area_hectares, water_source,
              irrigation_type, polygon_coordinates.

    Returns: '0x' + 64 hex chars (bytes32 ready)
    """
    data = {
        "farm_id": str(farm.id),
        "farmer_id": str(farm.farmer_id),
        "soil_type": farm.soil_type or "",
        "area_hectares": str(farm.area_hectares) if farm.area_hectares else "0",
        "water_source": farm.water_source or "",
        "irrigation_type": farm.irrigation_type or "",
        "polygon_coordinates": farm.polygon_coordinates or [],
    }
    # Canonical JSON — sort_keys ensures same order regardless of dict creation order
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return "0x" + digest


def generate_farmer_ref(farmer_id: str, farm_id: str) -> str:
    """
    SHA-256 reference linking a farmer to a specific farm.
    Used on-chain as farmerRef — allows cross-referencing with AgriAssist DB
    without exposing personal data.

    Returns: '0x' + 64 hex chars (bytes32 ready)
    """
    data = {
        "farmer_id": str(farmer_id),
        "farm_id": str(farm_id),
    }
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return "0x" + digest


def farm_uuid_to_uint256(farm_id: str) -> int:
    """
    Convert a farm UUID string to a stable uint256 for use as Solidity farmId.

    Solidity mapping uses uint256 keys. AgriAssist uses UUID strings.
    We take SHA-256(farm_uuid) mod 2^64 for a stable, collision-resistant numeric ID.

    Example:
        "c3d4e5f6-..." → 12345678901234567 (deterministic)
    """
    digest = hashlib.sha256(farm_id.encode("utf-8")).hexdigest()
    # Use full 256-bit value mod 2^64 to stay within safe JS integer range
    return int(digest, 16) % (2 ** 64)
