// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title MockUSDC — 6-decimal ERC-20 mirroring USDC for unit tests
/// @notice Real USDC has 6 decimals, not 18. Bugs hide in that gap.
contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USDC", "mUSDC") {}

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    /// @notice Open mint for testing. Never deploy this to anything real.
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}
