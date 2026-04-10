"""
blockchain_client.py — AgriAssist FastAPI → Node.js Blockchain Bridge

This module is the ONLY place in the Python codebase that talks to the
Node.js blockchain API. FastAPI never touches private keys or ethers.js directly.

Architecture:
    FastAPI (Python)
        → POST http://localhost:3001/blockchain/approve   [Node.js]
        → Returns { success, txHash, blockNumber }

Design rules:
  - All errors are caught and returned as dicts (never crash the admin route)
  - Async all the way (httpx.AsyncClient)
  - Timeout: 120s (blockchain tx confirmation can take ~30-60s on Amoy)
"""
import httpx
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Timeout: 120 seconds — Amoy block times are ~5s but tx can queue
BLOCKCHAIN_TIMEOUT = 120.0


class BlockchainClient:
    """
    HTTP client that calls the Node.js blockchain API layer.
    Instantiated once at module level and reused across requests.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        logger.info(f"BlockchainClient initialized → {self.base_url}")

    async def health_check(self) -> dict:
        """
        Check if the Node.js blockchain server is reachable and wallet is funded.
        Returns the health response dict or an error dict.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/blockchain/health")
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            return {
                "status": "error",
                "error": "Blockchain API server is not running. Start with: cd blockchain && node server.js",
            }
        except Exception as e:
            logger.error(f"Blockchain health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def approve_farm(
        self,
        farm_id: int,
        farmer_ref: str,
        land_hash: str,
    ) -> dict:
        """
        Call Node.js to record farm approval on Polygon Amoy.

        Args:
            farm_id    : uint256 numeric ID (derived from UUID via hash_service)
            farmer_ref : '0x' + 64 hex chars SHA-256 of farmer+farm IDs
            land_hash  : '0x' + 64 hex chars SHA-256 of canonical farm data

        Returns:
            On success: { success: True, txHash: str, blockNumber: int, polygonScanUrl: str }
            On failure: { success: False, error: str }
        """
        payload = {
            "farmId": farm_id,
            "farmerRef": farmer_ref,
            "landHash": land_hash,
        }

        logger.info(
            f"Calling blockchain approve → farmId={farm_id} "
            f"landHash={land_hash[:12]}..."
        )

        try:
            async with httpx.AsyncClient(timeout=BLOCKCHAIN_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.base_url}/blockchain/approve",
                    json=payload,
                )

                data = resp.json()

                # 409 = already approved on-chain (not a hard error for admin flow)
                if resp.status_code == 409:
                    logger.warning(
                        f"Farm {farm_id} already approved on-chain (ALREADY_APPROVED)"
                    )
                    return {
                        "success": False,
                        "error": "Farm is already approved on-chain",
                        "code": "ALREADY_APPROVED",
                    }

                # Any non-2xx other than 409 is a real failure
                if not resp.is_success:
                    error_msg = data.get("error", f"HTTP {resp.status_code}")
                    logger.error(f"Blockchain API error: {error_msg}")
                    return {"success": False, "error": error_msg}

                logger.info(
                    f"✅ Blockchain approval confirmed → tx={data.get('txHash')} "
                    f"block={data.get('blockNumber')}"
                )
                return data

        except httpx.ConnectError:
            msg = (
                "Cannot connect to blockchain API at "
                f"{self.base_url}. Is 'node server.js' running?"
            )
            logger.error(msg)
            return {"success": False, "error": msg}

        except httpx.TimeoutException:
            msg = (
                f"Blockchain API timed out after {BLOCKCHAIN_TIMEOUT}s. "
                "Transaction may have been submitted — check PolygonScan."
            )
            logger.error(msg)
            return {"success": False, "error": msg}

        except Exception as e:
            logger.error(f"Unexpected blockchain client error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_farm_record(self, farm_id: int) -> dict:
        """
        Read a farm's on-chain record directly from the contract.

        Returns:
            { success, farmId, approved, landHash, farmerRef, approvedBy, approvedAt }
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.base_url}/blockchain/farm/{farm_id}"
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"get_farm_record failed for farmId={farm_id}: {e}")
            return {"success": False, "error": str(e)}


# ─── Singleton instance ───────────────────────────────────────────────────────
# Import this in routers: from app.services.blockchain_client import blockchain_client
blockchain_client = BlockchainClient(base_url=settings.BLOCKCHAIN_API_URL)
