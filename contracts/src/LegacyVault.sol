// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IAavePool} from "./interfaces/IAavePool.sol";

/// @title LegacyVault — YourLegacy non-custodial digital trust fund
/// @author Shane Brazelton (ShaneBrain / Angel Cloud)
/// @notice One vault per family. Owner deposits USDC, vault supplies to Aave V3
///         and earns yield 24/7. Owner pings monthly to prove they're alive.
///         After `inactivityThreshold` of silence (default 90 days), the named
///         beneficiary can withdraw the full principal + accrued yield.
/// @dev Non-custodial. Shane / Angel Cloud / Pulsar Sentinel cannot touch user
///      funds. The contract is the custodian. Owner and beneficiary are set
///      at deployment and never change in v1 (Phase 1 scope — see README).
///
///      Pulsar Sentinel Rule Code mapping:
///        - ping()    → heartbeat for RC 1.01 (Signature Required)
///        - inherit() → RC 1.02 (Heir Transfer) trigger
///
///      Phase 1 invariants:
///        I1: lastHeartbeat is monotonically non-decreasing
///        I2: Only owner can ping
///        I3: Only beneficiary can inherit, and only after threshold elapsed
///        I4: deposit() always pulls then supplies — vault never holds USDC
///            outside of an in-progress call
///        I5: inherit() empties the entire aToken position to beneficiary
contract LegacyVault is ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ─── Immutables (set at deployment, cannot be changed) ───────────────────

    /// @notice The wallet that funds and controls the vault.
    address public immutable owner;

    /// @notice The wallet that inherits after `inactivityThreshold` of silence.
    address public immutable beneficiary;

    /// @notice USDC token contract on this chain.
    /// @dev Base mainnet:  0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
    ///      Base Sepolia: 0x036CbD53842c5426634e7929541eC2318f3dCF7e
    IERC20 public immutable usdc;

    /// @notice Aave V3 Pool on this chain.
    IAavePool public immutable aavePool;

    /// @notice Seconds of owner silence before beneficiary may inherit.
    /// @dev Default 90 days. Set at construction; immutable to remove governance
    ///      surface. v2 may make this owner-settable with a multi-sig delay.
    uint256 public immutable inactivityThreshold;

    // ─── Mutable state ───────────────────────────────────────────────────────

    /// @notice Unix timestamp of the most recent owner ping (or deployment).
    /// @dev Monotonic — see invariant I1.
    uint256 public lastHeartbeat;

    /// @notice Set true once inherit() succeeds. Prevents double-inherit.
    bool public inherited;

    // ─── Events ──────────────────────────────────────────────────────────────

    event Deposited(address indexed from, uint256 amount, uint256 newHeartbeat);
    event Pinged(address indexed by, uint256 timestamp);
    event Inherited(address indexed by, uint256 amount, uint256 silenceDuration);

    // ─── Custom errors (cheaper than require strings) ────────────────────────

    error NotOwner();
    error NotBeneficiary();
    error OwnerStillActive(uint256 secondsRemaining);
    error AlreadyInherited();
    error ZeroAmount();
    error ZeroAddress();

    // ─── Constructor ─────────────────────────────────────────────────────────

    /// @param _beneficiary The heir wallet (cannot be owner).
    /// @param _usdc USDC token address for this chain.
    /// @param _aavePool Aave V3 Pool address for this chain.
    /// @param _inactivityThreshold Seconds of silence required before inherit().
    ///        90 days = 7_776_000. Min sanity floor: 7 days.
    constructor(
        address _beneficiary,
        address _usdc,
        address _aavePool,
        uint256 _inactivityThreshold
    ) {
        if (_beneficiary == address(0)) revert ZeroAddress();
        if (_usdc == address(0)) revert ZeroAddress();
        if (_aavePool == address(0)) revert ZeroAddress();
        if (_beneficiary == msg.sender) revert ZeroAddress(); // owner != heir
        if (_inactivityThreshold < 7 days) revert ZeroAmount();

        owner = msg.sender;
        beneficiary = _beneficiary;
        usdc = IERC20(_usdc);
        aavePool = IAavePool(_aavePool);
        inactivityThreshold = _inactivityThreshold;
        lastHeartbeat = block.timestamp;
    }

    // ─── External functions ──────────────────────────────────────────────────

    /// @notice Pull USDC from caller and supply it to Aave on behalf of this vault.
    /// @dev Deposit refreshes the heartbeat — depositing IS proof of life.
    ///      Anyone may deposit (e.g. subscription auto-router). Only owner pings.
    function deposit(uint256 amount) external nonReentrant {
        if (amount == 0) revert ZeroAmount();
        if (inherited) revert AlreadyInherited();

        // Pull USDC from caller into vault.
        usdc.safeTransferFrom(msg.sender, address(this), amount);

        // Approve Aave to spend exactly `amount`. Reset approval each call to
        // avoid lingering allowance — defense-in-depth even though we control
        // the pool address.
        usdc.forceApprove(address(aavePool), amount);

        // Supply to Aave. aTokens accrue to address(this).
        aavePool.supply(address(usdc), amount, address(this), 0);

        // Heartbeat refresh — depositing = proof the human is still here.
        lastHeartbeat = block.timestamp;

        emit Deposited(msg.sender, amount, lastHeartbeat);
    }

    /// @notice Owner heartbeat. Updates lastHeartbeat to now.
    /// @dev Cheap call — costs only a storage write. Owner can auto-sign monthly
    ///      via the orchestrator (Pi MCP on :8550) or manually via the dapp.
    function ping() external {
        if (msg.sender != owner) revert NotOwner();
        if (inherited) revert AlreadyInherited();

        lastHeartbeat = block.timestamp;
        emit Pinged(msg.sender, block.timestamp);
    }

    /// @notice Beneficiary claims the entire vault after threshold of silence.
    /// @dev Withdraws ALL USDC (principal + accrued Aave yield) to beneficiary.
    ///      One-shot: sets `inherited = true` and locks the vault forever.
    function inherit() external nonReentrant {
        if (msg.sender != beneficiary) revert NotBeneficiary();
        if (inherited) revert AlreadyInherited();

        uint256 silenceDuration = block.timestamp - lastHeartbeat;
        if (silenceDuration < inactivityThreshold) {
            revert OwnerStillActive(inactivityThreshold - silenceDuration);
        }

        // Mark inherited BEFORE external call (checks-effects-interactions).
        inherited = true;

        // Withdraw entire aToken balance — Aave converts type(uint256).max
        // to "withdraw all" and returns the actual amount transferred.
        uint256 withdrawn = aavePool.withdraw(
            address(usdc),
            type(uint256).max,
            beneficiary
        );

        emit Inherited(msg.sender, withdrawn, silenceDuration);
    }

    // ─── View helpers ────────────────────────────────────────────────────────

    /// @notice Seconds since last heartbeat. UI can call this to render a
    ///         "days since last ping" gauge.
    function silenceDuration() external view returns (uint256) {
        return block.timestamp - lastHeartbeat;
    }

    /// @notice Whether the beneficiary could currently call inherit() successfully.
    function inheritable() external view returns (bool) {
        return !inherited && (block.timestamp - lastHeartbeat) >= inactivityThreshold;
    }
}
