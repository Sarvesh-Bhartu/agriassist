// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title FarmVerificationRegistry
 * @notice AgriAssist — Records admin-verified farms on Polygon Amoy.
 *         Farmers never interact with this contract directly.
 *         Only accounts with VERIFIER_ROLE can approve farms.
 */
contract FarmVerificationRegistry is AccessControl {
    // ─── Roles ───────────────────────────────────────────────────
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");

    // ─── Data ────────────────────────────────────────────────────
    struct FarmRecord {
        bool approved;
        bytes32 landHash;    // SHA-256 of canonical farm data
        bytes32 farmerRef;   // SHA-256 of farmer + farm IDs
        address approvedBy;  // which verifier wallet approved
        uint256 approvedAt;  // unix timestamp
    }

    /// @dev farmId → FarmRecord. farmId is derived from UUID hash off-chain.
    mapping(uint256 => FarmRecord) public farms;

    // ─── Events ──────────────────────────────────────────────────
    event FarmApproved(
        uint256 indexed farmId,
        bytes32 indexed farmerRef,
        bytes32 landHash,
        address approvedBy,
        uint256 approvedAt
    );

    // ─── Constructor ─────────────────────────────────────────────
    constructor() {
        // Deployer gets both admin and verifier roles
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(VERIFIER_ROLE, msg.sender);
    }

    // ─── Write Functions ─────────────────────────────────────────

    /**
     * @notice Record on-chain proof that a farm has been admin-verified.
     * @param farmId    Numeric ID derived from farm UUID (deterministic hash)
     * @param farmerRef SHA-256 reference linking to the farmer in AgriAssist DB
     * @param landHash  SHA-256 of canonical farm data (soil, area, polygon, etc.)
     */
    function approveFarm(
        uint256 farmId,
        bytes32 farmerRef,
        bytes32 landHash
    ) external onlyRole(VERIFIER_ROLE) {
        require(!farms[farmId].approved, "FarmRegistry: Already approved");

        farms[farmId] = FarmRecord({
            approved: true,
            landHash: landHash,
            farmerRef: farmerRef,
            approvedBy: msg.sender,
            approvedAt: block.timestamp
        });

        emit FarmApproved(
            farmId,
            farmerRef,
            landHash,
            msg.sender,
            block.timestamp
        );
    }

    // ─── Read Functions ──────────────────────────────────────────

    /**
     * @notice Quick check — is a farm approved?
     */
    function isFarmApproved(uint256 farmId) public view returns (bool) {
        return farms[farmId].approved;
    }

    /**
     * @notice Full farm verification record.
     */
    function getFarmRecord(uint256 farmId)
        public
        view
        returns (
            bool approved,
            bytes32 landHash,
            bytes32 farmerRef,
            address approvedBy,
            uint256 approvedAt
        )
    {
        FarmRecord memory r = farms[farmId];
        return (
            r.approved,
            r.landHash,
            r.farmerRef,
            r.approvedBy,
            r.approvedAt
        );
    }
}
