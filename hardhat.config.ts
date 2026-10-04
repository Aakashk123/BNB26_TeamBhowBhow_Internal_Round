import { HardhatUserConfig, subtask } from "hardhat/config";
import { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } from "hardhat/builtin-tasks/task-names";
import "@nomicfoundation/hardhat-ethers";
import "@nomicfoundation/hardhat-chai-matchers";
// Pinned local solc avoids a build-time compiler download.
subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD).setAction(async ({solcVersion}: {solcVersion: string}) => ({
  compilerPath: require.resolve("solc/soljson.js"), isSolcJs: true,
  version: solcVersion, longVersion: require("solc").version()
}));
const config: HardhatUserConfig = {
  solidity: {version: "0.8.24", settings: {evmVersion: "paris", optimizer: {enabled: true, runs: 200}, viaIR: true}},
  networks: {hardhat: {chainId: 31337}, localhost: {url: process.env.CHAIN_RPC_URL || "http://127.0.0.1:8545"},
    testnet: {url: process.env.TESTNET_RPC_URL || "http://127.0.0.1:8545", accounts: process.env.DEPLOYER_KEY ? [process.env.DEPLOYER_KEY] : []}},
};
export default config;
