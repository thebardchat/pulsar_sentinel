// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IERC20 — minimal ERC-20 interface
/// @notice Slim interface so tests can mock without pulling OpenZeppelin into
///         the mock layer. Production LegacyVault uses OZ's IERC20 directly
///         via remappings.
interface IERC20 {
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}
