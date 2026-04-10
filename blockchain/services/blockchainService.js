/**
 * Blockchain service for AgriAssist
 * Handles all ethers.js interaction with FarmVerificationRegistry
 */
const { ethers } = require("ethers");
const path = require("path");
const fs = require("fs");
require("dotenv").config();

// ─── Load ABI ────────────────────────────────────────────────────────────────
// Hardhat stores artifacts at artifacts/contracts/FileName.sol/ContractName.json
const artifactPath = path.join(
  __dirname,
  "../artifacts/contracts/FarmVerificationRegistry.sol/FarmVerificationRegistry.json"
);

let CONTRACT_ABI;
try {
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  CONTRACT_ABI = artifact.abi;
} catch (err) {
  console.error("❌ Could not load ABI. Run 'npm run compile' first.");
  process.exit(1);
}

// ─── Provider + Wallet ───────────────────────────────────────────────────────
const RPC_URL = process.env.RPC_URL;
const PRIVATE_KEY = process.env.PRIVATE_KEY;
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS;

if (!RPC_URL || !PRIVATE_KEY) {
  console.error("❌ RPC_URL and PRIVATE_KEY must be set in blockchain/.env");
  process.exit(1);
}

const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
let contract = null;

function getContract() {
  if (!CONTRACT_ADDRESS) {
    throw new Error(
      "CONTRACT_ADDRESS not set in blockchain/.env. Deploy the contract first."
    );
  }
  if (!contract) {
    contract = new ethers.Contract(CONTRACT_ADDRESS, CONTRACT_ABI, wallet);
  }
  return contract;
}

// ─── Service Functions ───────────────────────────────────────────────────────

/**
 * Approve a farm on-chain.
 * @param {bigint|number|string} farmId   - Numeric farm ID (derived from UUID)
 * @param {string} farmerRef              - 0x-prefixed bytes32 hex string
 * @param {string} landHash               - 0x-prefixed bytes32 hex string
 * @returns {{ success: boolean, txHash: string, blockNumber: number }}
 */
async function approveFarm(farmId, farmerRef, landHash) {
  const c = getContract();

  // ethers.js v6 requires BigInt for uint256 parameters
  const farmIdBigInt = BigInt(farmId);

  // Pad hex strings to 32 bytes (bytes32 in Solidity)
  const farmerRefBytes = ethers.zeroPadValue(farmerRef, 32);
  const landHashBytes = ethers.zeroPadValue(landHash, 32);

  console.log(`\n📤 Sending approveFarm tx:`);
  console.log(`   farmId    : ${farmIdBigInt}`);
  console.log(`   farmerRef : ${farmerRefBytes}`);
  console.log(`   landHash  : ${landHashBytes}`);

  const tx = await c.approveFarm(farmIdBigInt, farmerRefBytes, landHashBytes);
  console.log(`   tx sent   : ${tx.hash}`);

  const receipt = await tx.wait(1); // wait for 1 confirmation
  console.log(`   confirmed : block ${receipt.blockNumber}`);

  return {
    success: true,
    txHash: receipt.hash,
    blockNumber: receipt.blockNumber,
  };
}

/**
 * Check if a farm is approved.
 * @param {bigint|number|string} farmId
 * @returns {boolean}
 */
async function isFarmApproved(farmId) {
  const c = getContract();
  return await c.isFarmApproved(BigInt(farmId));
}

/**
 * Get full farm record from contract.
 * @param {bigint|number|string} farmId
 */
async function getFarmRecord(farmId) {
  const c = getContract();
  const [approved, landHash, farmerRef, approvedBy, approvedAt] =
    await c.getFarmRecord(BigInt(farmId));
  return {
    approved,
    landHash,
    farmerRef,
    approvedBy,
    approvedAt: Number(approvedAt),
  };
}

/**
 * Health check — wallet balance and contract accessibility.
 */
async function healthCheck() {
  const balance = await provider.getBalance(wallet.address);
  const networkInfo = await provider.getNetwork();
  const contractOk = CONTRACT_ADDRESS ? true : false;

  return {
    walletAddress: wallet.address,
    balancePOL: ethers.formatEther(balance),
    network: networkInfo.name,
    chainId: Number(networkInfo.chainId),
    contractAddress: CONTRACT_ADDRESS || "NOT CONFIGURED",
    contractReady: contractOk,
  };
}

module.exports = { approveFarm, isFarmApproved, getFarmRecord, healthCheck };
