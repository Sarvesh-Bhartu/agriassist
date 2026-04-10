const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Deploying FarmVerificationRegistry to Polygon Amoy...\n");

  // Get deployer
  const [deployer] = await ethers.getSigners();
  console.log(`📍 Deployer wallet : ${deployer.address}`);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`💰 Wallet balance  : ${ethers.formatEther(balance)} POL\n`);

  if (balance === 0n) {
    console.error("❌ Wallet has 0 POL. Visit https://faucet.polygon.technology/ to get test tokens.");
    process.exit(1);
  }

  // Deploy
  console.log("📦 Compiling and deploying contract...");
  const Factory = await ethers.getContractFactory("FarmVerificationRegistry");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  const deployTx = contract.deploymentTransaction();

  console.log("\n✅ Contract deployed successfully!");
  console.log(`   Contract Address : ${address}`);
  console.log(`   Transaction Hash : ${deployTx.hash}`);
  console.log(`   Block Number     : ${deployTx.blockNumber ?? "pending..."}`);
  console.log(`\n🔍 View on PolygonScan: https://amoy.polygonscan.com/address/${address}`);

  // Save deployment info to config/deployment.json
  const deploymentInfo = {
    contractAddress: address,
    txHash: deployTx.hash,
    network: "polygon-amoy",
    chainId: 80002,
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
  };

  const configDir = path.join(__dirname, "../config");
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
  }

  fs.writeFileSync(
    path.join(configDir, "deployment.json"),
    JSON.stringify(deploymentInfo, null, 2)
  );

  console.log("\n📄 Deployment info saved to blockchain/config/deployment.json");
  console.log("\n⚠️  IMPORTANT: Now update your .env files:");
  console.log(`   blockchain/.env          → CONTRACT_ADDRESS=${address}`);
  console.log(`   agriassist/.env          → FARM_VERIFICATION_CONTRACT=${address}`);
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error("\n❌ Deployment failed:");
    console.error(err);
    process.exit(1);
  });
