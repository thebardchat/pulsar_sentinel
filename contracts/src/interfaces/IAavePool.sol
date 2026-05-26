// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IAavePool — minimal Aave V3 IPool interface
/// @notice Only the two functions LegacyVault actually calls. Full IPool lives
///         in lib/aave-v3-core; we declare this slim interface so unit tests can
///         mock without pulling the entire Aave dependency graph into the test
///         harness.
/// @dev Base mainnet pool: 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5
///      Base Sepolia pool: 0xbE781D7Bdf469f3d94a62Cdcc407aCe106AEcA74 (Aave testnet)
interface IAavePool {
    /// @notice Supplies `amount` of `asset` to Aave on behalf of `onBehalfOf`.
    /// @param asset The address of the underlying asset (USDC on Base)
    /// @param amount The amount to supply
    /// @param onBehalfOf The address that will receive the aTokens
    /// @param referralCode 0 — no referral program
    function supply(
        address asset,
        uint256 amount,
        address onBehalfOf,
        uint16 referralCode
    ) external;

    /// @notice Withdraws `amount` of `asset` from Aave.
    /// @param asset The underlying asset to withdraw (USDC on Base)
    /// @param amount Pass type(uint256).max to withdraw the entire aToken balance
    /// @param to The address that will receive the underlying asset
    /// @return The actual amount withdrawn
    function withdraw(
        address asset,
        uint256 amount,
        address to
    ) external returns (uint256);
}
