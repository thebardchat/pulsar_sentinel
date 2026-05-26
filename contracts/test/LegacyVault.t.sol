// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {LegacyVault} from "../src/LegacyVault.sol";
import {MockUSDC} from "./mocks/MockUSDC.sol";
import {MockAavePool} from "./mocks/MockAavePool.sol";

/// @title LegacyVaultTest — Phase 1 Foundry test suite
/// @notice Local-only. No RPC. No broadcast. No mainnet. Runs entirely against
///         forge's anvil-equivalent in-process EVM.
contract LegacyVaultTest is Test {
    LegacyVault internal vault;
    MockUSDC internal usdc;
    MockAavePool internal pool;

    address internal owner = makeAddr("owner");
    address internal heir = makeAddr("heir");
    address internal stranger = makeAddr("stranger");
    address internal subscriptionRouter = makeAddr("subscriptionRouter");

    uint256 internal constant THRESHOLD = 90 days;
    uint256 internal constant INITIAL_DEPOSIT = 1_000_000_000; // 1,000 USDC (6 decimals)

    // ─── setUp ──────────────────────────────────────────────────────────────

    function setUp() public {
        usdc = new MockUSDC();
        pool = new MockAavePool();

        // Deploy vault as `owner` so msg.sender becomes owner.
        vm.prank(owner);
        vault = new LegacyVault(heir, address(usdc), address(pool), THRESHOLD);

        // Fund accounts that will deposit.
        usdc.mint(owner, INITIAL_DEPOSIT * 10);
        usdc.mint(subscriptionRouter, INITIAL_DEPOSIT * 10);
    }

    // ─── Constructor tests ──────────────────────────────────────────────────

    function test_Constructor_SetsImmutables() public view {
        assertEq(vault.owner(), owner, "owner");
        assertEq(vault.beneficiary(), heir, "beneficiary");
        assertEq(address(vault.usdc()), address(usdc), "usdc");
        assertEq(address(vault.aavePool()), address(pool), "aavePool");
        assertEq(vault.inactivityThreshold(), THRESHOLD, "threshold");
        assertEq(vault.lastHeartbeat(), block.timestamp, "heartbeat init");
        assertFalse(vault.inherited(), "not inherited at deploy");
    }

    function test_Constructor_RevertsOnZeroBeneficiary() public {
        vm.expectRevert(LegacyVault.ZeroAddress.selector);
        new LegacyVault(address(0), address(usdc), address(pool), THRESHOLD);
    }

    function test_Constructor_RevertsOnZeroUSDC() public {
        vm.expectRevert(LegacyVault.ZeroAddress.selector);
        new LegacyVault(heir, address(0), address(pool), THRESHOLD);
    }

    function test_Constructor_RevertsOnZeroPool() public {
        vm.expectRevert(LegacyVault.ZeroAddress.selector);
        new LegacyVault(heir, address(usdc), address(0), THRESHOLD);
    }

    function test_Constructor_RevertsWhenOwnerIsHeir() public {
        vm.prank(owner);
        vm.expectRevert(LegacyVault.ZeroAddress.selector);
        new LegacyVault(owner, address(usdc), address(pool), THRESHOLD);
    }

    function test_Constructor_RevertsOnThresholdTooShort() public {
        vm.expectRevert(LegacyVault.ZeroAmount.selector);
        new LegacyVault(heir, address(usdc), address(pool), 1 days);
    }

    // ─── deposit() tests ────────────────────────────────────────────────────

    function test_Deposit_PullsUSDCAndSuppliesToAave() public {
        vm.startPrank(owner);
        usdc.approve(address(vault), INITIAL_DEPOSIT);
        vault.deposit(INITIAL_DEPOSIT);
        vm.stopPrank();

        assertEq(usdc.balanceOf(owner), INITIAL_DEPOSIT * 10 - INITIAL_DEPOSIT, "owner debited");
        assertEq(usdc.balanceOf(address(vault)), 0, "vault holds zero USDC (all in Aave)");
        assertEq(pool.balances(address(usdc), address(vault)), INITIAL_DEPOSIT, "pool credited vault");
    }

    function test_Deposit_RefreshesHeartbeat() public {
        // Advance time, then deposit. Heartbeat should match the new now.
        vm.warp(block.timestamp + 30 days);

        vm.startPrank(owner);
        usdc.approve(address(vault), INITIAL_DEPOSIT);
        vault.deposit(INITIAL_DEPOSIT);
        vm.stopPrank();

        assertEq(vault.lastHeartbeat(), block.timestamp, "heartbeat refreshed");
    }

    function test_Deposit_AnyoneCanDeposit_SubscriptionRouter() public {
        // The subscription auto-router (not the owner) can fund the vault.
        // This is the "subscription portion auto-routes USDC → vault" path.
        vm.startPrank(subscriptionRouter);
        usdc.approve(address(vault), INITIAL_DEPOSIT);
        vault.deposit(INITIAL_DEPOSIT);
        vm.stopPrank();

        assertEq(pool.balances(address(usdc), address(vault)), INITIAL_DEPOSIT, "deposited");
    }

    function test_Deposit_RevertsOnZeroAmount() public {
        vm.prank(owner);
        vm.expectRevert(LegacyVault.ZeroAmount.selector);
        vault.deposit(0);
    }

    function test_Deposit_RevertsAfterInherited() public {
        _triggerInheritance();
        vm.startPrank(owner);
        usdc.approve(address(vault), INITIAL_DEPOSIT);
        vm.expectRevert(LegacyVault.AlreadyInherited.selector);
        vault.deposit(INITIAL_DEPOSIT);
        vm.stopPrank();
    }

    function test_Deposit_EmitsEvent() public {
        vm.startPrank(owner);
        usdc.approve(address(vault), INITIAL_DEPOSIT);
        vm.expectEmit(true, false, false, true, address(vault));
        emit LegacyVault.Deposited(owner, INITIAL_DEPOSIT, block.timestamp);
        vault.deposit(INITIAL_DEPOSIT);
        vm.stopPrank();
    }

    // ─── ping() tests ───────────────────────────────────────────────────────

    function test_Ping_UpdatesHeartbeat() public {
        vm.warp(block.timestamp + 45 days);
        vm.prank(owner);
        vault.ping();
        assertEq(vault.lastHeartbeat(), block.timestamp, "heartbeat now");
    }

    function test_Ping_RevertsForNonOwner() public {
        vm.prank(stranger);
        vm.expectRevert(LegacyVault.NotOwner.selector);
        vault.ping();
    }

    function test_Ping_RevertsForBeneficiary() public {
        // The heir is NOT the owner — they cannot extend the heartbeat to lock
        // themselves out further. (Sanity check on access control.)
        vm.prank(heir);
        vm.expectRevert(LegacyVault.NotOwner.selector);
        vault.ping();
    }

    function test_Ping_RevertsAfterInherited() public {
        _triggerInheritance();
        vm.prank(owner);
        vm.expectRevert(LegacyVault.AlreadyInherited.selector);
        vault.ping();
    }

    function test_Ping_EmitsEvent() public {
        vm.expectEmit(true, false, false, true, address(vault));
        emit LegacyVault.Pinged(owner, block.timestamp);
        vm.prank(owner);
        vault.ping();
    }

    // ─── inherit() tests ────────────────────────────────────────────────────

    function test_Inherit_RevertsBeforeThreshold() public {
        _depositInitial();

        vm.warp(block.timestamp + THRESHOLD - 1);

        vm.prank(heir);
        vm.expectRevert(
            abi.encodeWithSelector(LegacyVault.OwnerStillActive.selector, 1)
        );
        vault.inherit();
    }

    function test_Inherit_RevertsForNonBeneficiary() public {
        _depositInitial();
        vm.warp(block.timestamp + THRESHOLD + 1);

        vm.prank(stranger);
        vm.expectRevert(LegacyVault.NotBeneficiary.selector);
        vault.inherit();
    }

    function test_Inherit_RevertsForOwnerCalling() public {
        // The owner cannot trigger inherit() against themselves. (Sanity check.)
        _depositInitial();
        vm.warp(block.timestamp + THRESHOLD + 1);

        vm.prank(owner);
        vm.expectRevert(LegacyVault.NotBeneficiary.selector);
        vault.inherit();
    }

    function test_Inherit_TransfersPrincipalToBeneficiary() public {
        _depositInitial();
        vm.warp(block.timestamp + THRESHOLD + 1);

        vm.prank(heir);
        vault.inherit();

        assertEq(usdc.balanceOf(heir), INITIAL_DEPOSIT, "heir got principal");
        assertEq(pool.balances(address(usdc), address(vault)), 0, "pool drained");
        assertTrue(vault.inherited(), "inherited flag set");
    }

    function test_Inherit_TransfersPrincipalPlusYield() public {
        _depositInitial();

        // Simulate ~3.5% APY over 90 days → ~0.86% of principal.
        uint256 yieldAmount = (INITIAL_DEPOSIT * 86) / 10_000;
        usdc.mint(address(pool), yieldAmount); // fund the pool with the yield
        pool.simulateYield(address(usdc), address(vault), yieldAmount);

        vm.warp(block.timestamp + THRESHOLD + 1);
        vm.prank(heir);
        vault.inherit();

        assertEq(usdc.balanceOf(heir), INITIAL_DEPOSIT + yieldAmount, "principal + yield");
    }

    function test_Inherit_CannotBeCalledTwice() public {
        _triggerInheritance();
        vm.prank(heir);
        vm.expectRevert(LegacyVault.AlreadyInherited.selector);
        vault.inherit();
    }

    function test_Inherit_EmitsEvent() public {
        _depositInitial();
        vm.warp(block.timestamp + THRESHOLD + 100);

        vm.expectEmit(true, false, false, true, address(vault));
        emit LegacyVault.Inherited(heir, INITIAL_DEPOSIT, THRESHOLD + 100);

        vm.prank(heir);
        vault.inherit();
    }

    function test_Inherit_PingResetsTheClock() public {
        _depositInitial();

        // Owner sneaks in at day 89 with a ping → heir blocked.
        vm.warp(block.timestamp + 89 days);
        vm.prank(owner);
        vault.ping();

        vm.warp(block.timestamp + 1 days); // total elapsed 90d but only 1d since ping
        vm.prank(heir);
        vm.expectRevert(); // OwnerStillActive — exact remaining computed dynamically
        vault.inherit();
    }

    // ─── View helper tests ──────────────────────────────────────────────────

    function test_View_SilenceDuration() public {
        vm.warp(block.timestamp + 17 days);
        assertEq(vault.silenceDuration(), 17 days);
    }

    function test_View_Inheritable_FalseBeforeThreshold() public {
        vm.warp(block.timestamp + THRESHOLD - 1);
        assertFalse(vault.inheritable());
    }

    function test_View_Inheritable_TrueAfterThreshold() public {
        vm.warp(block.timestamp + THRESHOLD);
        assertTrue(vault.inheritable());
    }

    function test_View_Inheritable_FalseAfterInherited() public {
        _triggerInheritance();
        assertFalse(vault.inheritable());
    }

    // ─── Fuzz tests ─────────────────────────────────────────────────────────

    /// @notice Deposit any non-zero amount within owner's balance — round-trips cleanly.
    function testFuzz_Deposit_RoundTrip(uint256 amount) public {
        amount = bound(amount, 1, INITIAL_DEPOSIT * 10);

        vm.startPrank(owner);
        usdc.approve(address(vault), amount);
        vault.deposit(amount);
        vm.stopPrank();

        assertEq(pool.balances(address(usdc), address(vault)), amount);
    }

    /// @notice Any silence duration >= threshold lets heir inherit.
    function testFuzz_Inherit_AtOrAboveThreshold(uint256 elapsed) public {
        elapsed = bound(elapsed, THRESHOLD, 3650 days); // up to 10 years

        _depositInitial();
        vm.warp(block.timestamp + elapsed);

        vm.prank(heir);
        vault.inherit();

        assertEq(usdc.balanceOf(heir), INITIAL_DEPOSIT);
    }

    /// @notice Any silence duration < threshold blocks heir.
    function testFuzz_Inherit_BelowThresholdReverts(uint256 elapsed) public {
        elapsed = bound(elapsed, 1, THRESHOLD - 1);

        _depositInitial();
        vm.warp(block.timestamp + elapsed);

        vm.prank(heir);
        vm.expectRevert();
        vault.inherit();
    }

    // ─── Invariant test ─────────────────────────────────────────────────────

    /// @notice I1 — lastHeartbeat is monotonically non-decreasing.
    ///         Ping and deposit only ever push it forward; nothing decreases it.
    function test_Invariant_HeartbeatMonotonic() public {
        uint256 prior = vault.lastHeartbeat();

        // ping at the same timestamp — heartbeat must equal, never be less.
        vm.prank(owner);
        vault.ping();
        assertGe(vault.lastHeartbeat(), prior);

        // warp and ping again — heartbeat strictly greater.
        vm.warp(block.timestamp + 1 days);
        uint256 mid = vault.lastHeartbeat();
        vm.prank(owner);
        vault.ping();
        assertGt(vault.lastHeartbeat(), mid);
    }

    // ─── Internal helpers ───────────────────────────────────────────────────

    function _depositInitial() internal {
        vm.startPrank(owner);
        usdc.approve(address(vault), INITIAL_DEPOSIT);
        vault.deposit(INITIAL_DEPOSIT);
        vm.stopPrank();
    }

    function _triggerInheritance() internal {
        _depositInitial();
        vm.warp(block.timestamp + THRESHOLD + 1);
        vm.prank(heir);
        vault.inherit();
    }
}
