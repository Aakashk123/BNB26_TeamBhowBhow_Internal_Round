import { ethers } from "hardhat";
import { mkdirSync, writeFileSync } from "node:fs";
async function main() {
  const [deployer] = await ethers.getSigners();
  const contract = await ethers.deployContract("ModelLedgerRegistry", [deployer.address]);
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  mkdirSync("../.runtime", {recursive:true});
  writeFileSync("../.runtime/deployment.json", JSON.stringify({address, chainId:Number((await ethers.provider.getNetwork()).chainId)}, null, 2));
  process.stdout.write(`ModelLedgerRegistry deployed: ${address}\n`);
}
main().catch(e => {process.stderr.write(String(e)); process.exitCode=1;});
