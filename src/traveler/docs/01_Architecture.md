# System Architecture

SnackTraveler is designed as a modular, event-driven system. While the current implementation is a local simulation, the components are designed to map to a scalable, cloud-native architecture (e.g., using services like AWS Lambda, SQS, and DynamoDB).

The architecture is built around two main feedback loops:
1.  **The Evolutionary Loop (Exploration)**: This loop continuously generates and evaluates new agents to populate and improve the `EliteMap`. Its goal is to explore the space of possible strategies.
2.  **The Bandit Loop (Exploitation)**: This loop is triggered by a real task. It uses the `BanditAllocator` to select the best agent from the `EliteMap` based on past performance, executes it, and updates its performance model.

![Architecture Diagram](https://i.imgur.com/your-diagram-image-url.png)
*(Conceptual diagram - a real diagram would be hosted externally)*

## Core Components

- **`TravelerGenome`**: A Pydantic data model defining the "genes" of an agent. It's a set of parameters that dictates the agent's behavior.
    - *Code*: `utils/data_models.py`

- **`Traveler Executor`**: The worker that performs the web exploration. It takes a `TravelerGenome`, executes the search (e.g., calls LLMs, search APIs), and returns the raw results.
    - *Code*: `executor/traveler.py` (mock implementation)

- **`Evaluation Service`**: A service that processes the raw results from the Executor. It calculates:
    1.  **Fitness**: A multi-dimensional score of how well the agent performed (novelty, cost, etc.).
    2.  **Feature Descriptors**: The behavioral characteristics of the agent, used to determine its niche on the map.
    - *Code*: `evaluation/fitness.py`, `evaluation/features.py`

- **`EliteMap`**: The data store for the MAP-Elites algorithm. It's a grid where each cell (niche) stores the single best-performing agent found for that niche's behavior. This ensures diversity is maintained.
    - *Code*: `map_elites/elite_map.py`

- **`Bandit Allocator`**: The decision-maker for the exploitation loop. It treats each niche in the `EliteMap` as an "arm" of a multi-armed bandit and uses Thompson Sampling to select which strategy to deploy.
    - *Code*: `bandit/thompson_sampling.py`

- **Service Handlers**: These functions orchestrate the flow between the components. They represent the logic that would reside in serverless functions or event consumers in a distributed system.
    - `generation_scheduler_handler`: Creates new offspring for the evolutionary loop.
    - `bandit_allocator_handler`: Selects an agent for a task.
    - `evaluation_and_map_management_handler`: Processes results and updates the system's state.
    - *Code*: `services/handlers.py`

- **`main.py`**: The entry point for the simulation. It wires all the components together and runs the main evolutionary and bandit loops to demonstrate the system in action.
