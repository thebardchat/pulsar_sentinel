// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {LegacyVault} from "../src/LegacyVault.sol";
import {MockUSDC} from "../test/mocks/MockUSDC.sol";
import {MockAavePool} from "../test/mocks/MockAavePool.sol";

/// @notice Deploys MockUSDC + MockAavePool + LegacyVault to Base Sepolia.
/// @dev    Run: forge script script/DeployLegacyVault.s.sol \
///              --rpc-url base_sepolia --broadcast -vv
contract DeployLegacyVault is Script {
    function run() external {
        uint256 deployerPK = vm.envUint("DEPLOY_PRIVATE_KEY");
        address beneficiary = vm.envAddress("BENEFICIARY");
        uint256 threshold = vm.envOr("INACTIVITY_THRESHOLD", uint256(7 days));

        vm.startBroadcast(deployerPK);
        MockUSDC usdc = new MockUSDC();
        MockAavePool aavePool = new MockAavePool();
        LegacyVault vault = new LegacyVault(
            beneficiary,
            address(usdc),
            address(aavePool),
            threshold
        );
        vm.stopBroadcast();

        console.log("=================================");
        console.log("DEPLOY COMPLETE - Base Sepolia");
        console.log("=================================");
        console.log("MockUSDC      :", address(usdc));
        console.log("MockAavePool  :", address(aavePool));
        console.log("LegacyVault   :", address(vault));
        console.log("Owner         :", vm.addr(deployerPK));
        console.log("Beneficiary   :", beneficiary);
        console.log("Threshold (s) :", threshold);
    }
}
