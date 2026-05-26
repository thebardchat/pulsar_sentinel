// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IAavePool} from "../../src/interfaces/IAavePool.sol";

/// @title MockAavePool — minimal Aave V3 pool stand-in for LegacyVault tests
/// @notice Tracks per-(asset, supplier) balances. Supports a faked yield bump
///         via `simulateYield(asset, supplier, extraAmount)` so tests can
///         verify "principal + yield" semantics without running fork tests.
contract MockAavePool is IAavePool {
    using SafeERC20 for IERC20;

    // asset => supplier => deposited balance (in underlying token units)
    mapping(address => mapping(address => uint256)) public balances;

    function supply(
        address asset,
        uint256 amount,
        address onBehalfOf,
        uint16 /* referralCode */
    ) external override {
        IERC20(asset).safeTransferFrom(msg.sender, address(this), amount);
        balances[asset][onBehalfOf] += amount;
    }

    function withdraw(
        address asset,
        uint256 amount,
        address to
    ) external override returns (uint256) {
        uint256 bal = balances[asset][msg.sender];
        uint256 actual = (amount == type(uint256).max || amount > bal) ? bal : amount;
        balances[asset][msg.sender] = bal - actual;
        IERC20(asset).safeTransfer(to, actual);
        return actual;
    }

    /// @notice Inject "yield" into a supplier's position. Mints nothing — just
    ///         shifts the balance ledger and assumes the asset was pre-funded
    ///         into the pool. Tests should mint extra USDC to this pool first.
    function simulateYield(address asset, address supplier, uint256 extra) external {
        balances[asset][supplier] += extra;
    }
}
