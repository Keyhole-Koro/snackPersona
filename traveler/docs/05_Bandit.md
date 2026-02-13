# Bandit Allocator (`bandit/thompson_sampling.py`)

While the MAP-Elites algorithm is excellent for *exploring* and finding a diverse set of strategies, the system also needs a way to *exploit* this knowledge efficiently. When a real task needs to be performed, we want to use the strategy that is most likely to succeed. This is the job of the `BanditAllocator`.

The `BanditAllocator` implements a **Multi-Armed Bandit** algorithm to solve the "explore-exploit" problem at the strategy level.

## The Bandit Analogy

- **Arms**: Each "arm" of the bandit is a niche in the `EliteMap`. Pulling an arm corresponds to selecting the elite agent from that niche and executing it.
- **Reward**: The "reward" is the outcome of the execution. In our system, we use the `downstream_value` from the `Fitness` scores as a proxy for success (e.g., a value >= 0.5 is a "win," < 0.5 is a "loss").
- **Goal**: The bandit's goal is to maximize the cumulative reward over time by learning which arms (niches) give the best results.

## Thompson Sampling

The `BanditAllocator` uses **Thompson Sampling**, a highly effective and probabilistically elegant bandit algorithm.

Instead of just tracking the average reward of each arm, Thompson Sampling models the reward probability of each arm as a **Beta distribution**.

- The Beta distribution is defined by two parameters: `alpha` and `beta`.
- `alpha` can be thought of as the **number of successes**.
- `beta` can be thought of as the **number of failures**.
- Initially, each new arm starts with `alpha=1` and `beta=1`, which corresponds to a uniform (flat) distribution—the bandit has no prior belief about the arm's quality.

### How it Works

#### 1. Selection (`select_arm`)

To choose an arm to pull, Thompson Sampling performs a simple, powerful procedure:
1.  For each arm (niche), it draws one random sample from that arm's current Beta(`alpha`, `beta`) distribution.
2.  It then selects the arm that produced the **highest random sample**.

This naturally balances exploration and exploitation:
- An arm with a high success rate (high `alpha`, low `beta`) will have a distribution skewed towards 1.0, so it will likely produce a high sample and be chosen often (**exploitation**).
- An arm that has been tried only a few times will have a wide, uncertain distribution. It has a chance of producing a very high sample, giving it a chance to be chosen (**exploration**).

#### 2. Update (`update_arm`)

After an arm is pulled and the reward is observed:
- If the run was a success (reward >= 0.5), the arm's `alpha` is incremented.
- If the run was a failure (reward < 0.5), the arm's `beta` is incremented.

This update makes the distribution for that arm a more accurate reflection of its true success rate, refining the model for the next selection. This process allows the system to automatically and efficiently learn which types of strategies are most effective for real tasks.
