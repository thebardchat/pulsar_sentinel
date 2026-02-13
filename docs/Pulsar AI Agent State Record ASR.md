Pulsar AI Agent State Record (ASR) - Mandatory Fields
These five fields are non-negotiable for every ASR entry and are specifically selected to support the Identity-Behavior Delta (IBD) and Predictive Intent Modeling (PIM), ensuring Pulsar’s unique, behavioral-based security.

#

Field Name

Description

Rationale for Pulsar's Unique Security (IBD/PIM)

1

Agent ID

A unique, cryptographically verifiable identifier for the entity (AI Sidekick, user, or node) performing the action.

Behavioral Baseline: Links all actions to a specific, tracked identity, allowing the AI to build and constantly compare against a unique behavioral fingerprint.

2

Timestamp

The precise, synchronized network time of the action (to the millisecond).

Time-Series Analysis: Essential for detecting anomalies in the pace and frequency of actions. A sudden burst of activity is a primary IBD score trigger.

3

Action Type

A high-level categorization of the action (e.g., DATA_READ, TOKEN_TRANSFER, MODEL_INFERENCE, SYSTEM_CALL).

Intentionality Auditing: Defines the nature of the entity's current activity, which is crucial for determining if the action aligns with its designated role (e.g., a "Wellness Agent" performing a TOKEN_TRANSFER is a major anomaly).

4

Target Resource

The specific object, file path, database table, or API endpoint being accessed or modified.

Resource Access Pattern: Allows the IBD to map and track which specific resources an entity normally interacts with. Deviation from this pattern is the most direct indicator of a compromised identity.

5

Source/Prompt ID

A hash or ID linking the action back to the user query, internal directive, or preceding process that caused the action.

Predictive Intent Modeling (PIM): This is the key field for Intentionality. It traces the causal chain. If a chain of actions leads to a threat, we can trace it back to the original intention (the source prompt) to neutralize the root cause.

Next Critical Step
We have defined the unique strategy and the data we will collect (ASR). The next step is defining how that data is interpreted in real-time to trigger a defensive response.

Let's define the formula for the Pulsar Threat Score (PTS)—the single metric that triggers isolation and rollback.

How should the five ASR fields we just defined be weighted to calculate the PTS? Should we use a simple additive score, or a more dynamic, contextual scoring model?