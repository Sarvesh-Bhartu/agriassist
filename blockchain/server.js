/**
 * AgriAssist Blockchain API Server
 * Express server exposing blockchain interaction endpoints to FastAPI.
 * 
 * Endpoints:
 *   GET  /blockchain/health        — wallet + contract status
 *   POST /blockchain/approve       — approve farm on-chain
 *   GET  /blockchain/farm/:id      — read farm record from contract
 */
const express = require("express");
const { approveFarm, isFarmApproved, getFarmRecord, healthCheck } = require("./services/blockchainService");
require("dotenv").config();

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;

// ─── Middleware: Request Logger ───────────────────────────────────────────────
app.use((req, res, next) => {
  const ts = new Date().toISOString();
  console.log(`[${ts}] ${req.method} ${req.path}`);
  next();
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /blockchain/health
// ─────────────────────────────────────────────────────────────────────────────
app.get("/blockchain/health", async (req, res) => {
  try {
    const status = await healthCheck();
    res.json({
      status: "ok",
      timestamp: new Date().toISOString(),
      ...status,
    });
  } catch (err) {
    console.error("Health check failed:", err.message);
    res.status(500).json({
      status: "error",
      error: err.message,
    });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /blockchain/approve
// Body: { farmId: number, farmerRef: string, landHash: string }
// ─────────────────────────────────────────────────────────────────────────────
app.post("/blockchain/approve", async (req, res) => {
  const { farmId, farmerRef, landHash } = req.body;

  // Validation
  if (farmId === undefined || !farmerRef || !landHash) {
    return res.status(400).json({
      success: false,
      error: "Missing required fields: farmId, farmerRef, landHash",
    });
  }

  if (!farmerRef.startsWith("0x") || !landHash.startsWith("0x")) {
    return res.status(400).json({
      success: false,
      error: "farmerRef and landHash must be 0x-prefixed hex strings",
    });
  }

  try {
    console.log(`\n🌾 Approving farm ID: ${farmId}`);
    const result = await approveFarm(farmId, farmerRef, landHash);

    return res.json({
      success: true,
      txHash: result.txHash,
      blockNumber: result.blockNumber,
      polygonScanUrl: `https://amoy.polygonscan.com/tx/${result.txHash}`,
    });
  } catch (err) {
    console.error("❌ approveFarm error:", err.message);

    // Contract revert: farm already approved
    if (err.message?.includes("Already approved")) {
      return res.status(409).json({
        success: false,
        error: "Farm is already approved on-chain",
        code: "ALREADY_APPROVED",
      });
    }

    return res.status(500).json({
      success: false,
      error: err.message || "Blockchain transaction failed",
    });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /blockchain/farm/:id
// ─────────────────────────────────────────────────────────────────────────────
app.get("/blockchain/farm/:id", async (req, res) => {
  const farmId = req.params.id;

  if (isNaN(Number(farmId))) {
    return res.status(400).json({
      success: false,
      error: "farmId must be a numeric string",
    });
  }

  try {
    const [approved, record] = await Promise.all([
      isFarmApproved(BigInt(farmId)),
      getFarmRecord(BigInt(farmId)),
    ]);

    return res.json({
      success: true,
      farmId: farmId,
      approved,
      ...record,
      polygonScanUrl: approved
        ? `https://amoy.polygonscan.com/address/${process.env.CONTRACT_ADDRESS}`
        : null,
    });
  } catch (err) {
    console.error("❌ getFarmRecord error:", err.message);
    return res.status(500).json({
      success: false,
      error: err.message,
    });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// 404 fallback
// ─────────────────────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({ error: "Not found" });
});

// ─────────────────────────────────────────────────────────────────────────────
// Start server
// ─────────────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n🟢 AgriAssist Blockchain API running on http://localhost:${PORT}`);
  console.log(`   Health check : http://localhost:${PORT}/blockchain/health`);
  console.log(`   Approve farm : POST http://localhost:${PORT}/blockchain/approve`);
  console.log(`   Get farm     : GET  http://localhost:${PORT}/blockchain/farm/:id\n`);
});
