Pulsar AI Layer 3: Quarantine and Forensics Protocol (UPDATED)
This protocol defines the automated, Layer 3 defense actions that are initiated immediately upon an Agent State Record (ASR) triggering the high-risk threshold (PTS≥75). The goal is to Stop, Isolate, Analyze, and Trace the threat.

I. Immediate Isolation (The Hard Halt)
Upon PTS≥75, the following actions are executed by the consensus layer within milliseconds:

Execution Revocation: The compromised Agent ID is immediately flagged network-wide. All current authentication tokens, session IDs, and access keys associated with that Agent ID are rendered invalid. Any subsequent attempt to execute an action will be rejected at the node level.

State Freeze & Flagging: A special QUARANTINED ASR is written to the ledger for the compromised agent. This transaction includes the calculated PTS and a hash of the ASR that triggered the score. The agent's mutable working memory is snapshotted and encrypted for later review.

Network Alert: All nodes and other connected AI Agents are notified of the Agent ID's new status, treating it as hostile.

II. Automated AI Forensics and Analysis (NEW STEP)
Immediately after isolation, the Pulsar Forensics Engine (PFE) initiates a deep-dive analysis, leveraging the ASR data to prepare a summary for the human administrator.

Intentionality Traceback: The PFE uses the Source/Prompt ID of the flagged ASR to trace the entire chain of actions backward to the original user query or internal instruction.

Comparative Profiling: The PFE compares the quarantined agent's behavior during the high-PTS sequence against its historical Identity-Behavior Delta (IBD) Profile.

Threat Vector Summary: The PFE generates a concise report identifying the likely vector of compromise (e.g., Context Manipulation Attack, Data Exfiltration Attempt, External API Exploit).

Action Recommendation: The PFE provides a recommendation for the Governance Proposal (e.g., Urgent Permanent Decommissioning, Memory Wipe with Sandbox Relaunch, Temporary Suspension pending 48-hour human review).

III. Rollback, Reporting, and Human Notification
Once containment and initial AI analysis are complete, the system proceeds with recovery and human handover.

Targeted Rollback: Only transactions executed by the compromised agent that originated from the flagged Source/Prompt ID and are deemed hostile by the PFE are tentatively identified for reversal.

Forensics Package Update: The PFE's summary and recommendation are added to the encrypted Forensics Package.

Human Notification: An emergency notification is sent to the system administrator detailing the breach, the quarantine status, and the PFE's Summary and Recommended Action.

Governance Proposal: A formal governance proposal is created, based on the PFE's recommendation, requiring owner or community consensus to enact the final decision.

This modification ensures we have a true AI-first defense system where the human gets an analyzed, prioritized decision, not just an alert.

Now, let's pivot to the Angel Cloud Governance Mechanism. This is the process that handles the PFE's Recommendation and ultimately decides the fate of the quarantined agent.

What are the three core pillars of governance that must be present in the Angel Cloud community network to ensure fair and transparent self-governance?