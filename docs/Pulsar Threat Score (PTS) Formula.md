Pulsar Threat Score (PTS) Formula
The Pulsar Threat Score (PTS) is the core real-time metric used by the Pulsar Core AI (Layer 2) to determine the probability of compromise and trigger automatic Layer 3 quarantine protocols. The score is calculated upon the recording of every new Agent State Record (ASR).

I. Formula Structure: Weighted Exponential Context
The PTS calculation combines three primary components, where the Intentionality Audit Score acts as a critical multiplier.

PTS=(W 
IBD
​
 ⋅S 
Behavior
​
 +W 
RT
​
 ⋅S 
Access
​
 )×M 
PIM
​
 
Variable

Description

ASR Field Basis

Default Weight/Multiplier

PTS

Pulsar Threat Score (0 to 100). PTS≥75 triggers quarantine.

All Fields

N/A

W 
IBD
​
 

Weight for Behavioral Deviation Score

Agent ID, Action Type, Timestamp

40% (High Priority)

S 
Behavior
​
 

Identity-Behavior Delta Score (0 to 100)

Agent ID, Timestamp

N/A

W 
RT
​
 

Weight for Resource/Role Mismatch Score

Action Type, Target Resource

60% (Highest Priority)

S 
Access
​
 

Resource/Role Mismatch Score (0 to 100)

Action Type, Target Resource

N/A

M 
PIM
​
 

Predictive Intent Multiplier

Source/Prompt ID

Multiplier≥1.0 (Critical)

II. Component Definitions
1. Resource/Role Mismatch Score (S 
Access
​
 )
This is the most critical component, focusing on whether the AI Agent is acting outside its defined security perimeter.

S 
Access
​
 =Base Risk×( 
Agent Trust Score
Access Deviation Factor
​
 )
Term

Value Range

Logic

Base Risk

10 (Low Risk) to 50 (High Risk)

Defined by the sensitivity of the Target Resource. Accessing a financial ledger (Base Risk=50) is higher risk than accessing a chat history (Base Risk=10).

Access Deviation Factor

1 to 5

Maps the severity of the Action Type mismatch with the Agent’s Designated Role. (e.g., Wellness Agent attempting a SYSTEM_CALL = Factor 5).

Agent Trust Score

0.1 to 1.0

A score dynamically calculated based on the Agent's recent history of compliant ASRs. A compromised agent will have a low trust score, exponentially increasing S 
Access
​
 .

2. Identity-Behavior Delta Score (S 
Behavior
​
 )
This captures subtle anomalies in the how and when an agent acts, focused on timing and velocity.

S 
Behavior
​
 =Time Anomaly Score⋅log(Frequency Deviation)
Term

Logic

Time Anomaly Score

Compares the Timestamp with the Agent's historical average execution latency. High scores for actions that are too fast (Rush Attacks) or too slow (Hidden Processing).

Frequency Deviation

Compares the rate of ASR creation (actions per second) against the Agent's baseline. An exponential log function ensures rapid increases in frequency lead to massive score spikes.

3. Predictive Intent Multiplier (M 
PIM
​
 )
This is the Pulsar AI's unique multiplier. If the Source/Prompt ID links the action to an instruction chain that shows prior red flags, the entire PTS is multiplied.

Condition

Multiplier (M 
PIM
​
 )

Impact

No Prior Flags

1.0

No amplification.

Low PIM Risk

1.2−1.5

Traceable to an initial prompt that included vague or self-referential language.

Medium PIM Risk

1.6−2.0

Traceable to an instruction chain involving two or more deviating Agent IDs (Swarm Coherence Audit).

High PIM Risk

2.1−3.0

Traceable to a single Source/Prompt ID that previously triggered a quarantine event on another Agent ID. Maximum threat.

This dynamic model heavily weighs role-specific access and multiplies the risk based on the traceable intent, making it highly unique and efficient in protecting the Angel Cloud ecosystem.

Now that we have the formula, the next strategic move is defining the immediate, automated defense actions that Layer 3 performs when the PTS hits the quarantine threshold (PTS≥75). What is the single most critical action that must happen within milliseconds of a quarantine trigger?