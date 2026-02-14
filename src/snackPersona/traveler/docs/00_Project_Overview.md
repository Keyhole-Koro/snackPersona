# Project Overview: SnackTraveler

## The Goal: Autonomous and Diverse Web Exploration

SnackTraveler is a system designed to automate the discovery of effective web exploration strategies. The primary goal is to create a robust agent that can adapt its search behavior without requiring constant manual tuning by a human operator.

The system is built on the idea of maintaining a **population of "Traveler" agents**. Each Traveler represents a unique strategy, such as:
- "A fast, news-focused agent that prioritizes recent information in Japanese."
- "A deep, academic-focused agent that follows citations and prefers `.edu` or `.org` domains."
- "A broad, blog-focused agent that aims to find diverse opinions."

Instead of trying to create a single, perfect agent, the system evolves a large, diverse collection of specialized agents and learns when to deploy each one.

## Core Principles

The implementation is guided by several key principles from evolutionary computing and reinforcement learning:

1.  **Embrace Diversity (Quality-Diversity)**: A single "best" strategy rarely exists. The quality of a strategy is context-dependent. Therefore, the system's primary goal is to produce a wide array of high-performing strategies across a spectrum of behaviors. This is achieved through the **MAP-Elites** algorithm.

2.  **Automate Evaluation (Multi-Objective Optimization)**: Manually weighting different performance metrics (like `novelty`, `cost`, `reliability`) is brittle and difficult to maintain. The system uses **Non-Dominated Sorting (NSGA-II)** to evaluate agents on multiple objectives simultaneously, allowing it to find balanced, "Pareto optimal" solutions automatically.

3.  **Balance Exploration and Exploitation (Multi-Armed Bandits)**: The system must both explore new, potentially risky strategies and exploit known, reliable ones.
    - **Exploration** is handled by the evolutionary process (mutation and MAP-Elites), which constantly generates new types of agents.
    - **Exploitation** is handled by a **Thompson Sampling Bandit**, which selects the most promising agent from the existing population when a real task needs to be performed, maximizing efficiency.

By combining these principles, SnackTraveler aims to be a self-tuning, resilient, and highly adaptive system for web exploration.
