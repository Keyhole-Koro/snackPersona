# Usage Guide

This guide explains how to set up the necessary dependencies, run the main simulation, and execute the unit tests for the SnackTraveler project.

All commands should be run from the project's root directory (`snack/`).

## Dependency Setup

The project has one external dependency: `pydantic`.

It is highly recommended to use a Python virtual environment to manage dependencies and avoid conflicts with system-wide packages.

### 1. Create a Virtual Environment

If you don't have one already, create a virtual environment. The standard name for this is `venv`.

```bash
python3 -m venv venv
```
*(Note: On some systems like Debian/Ubuntu, you may first need to install the venv package itself via `sudo apt install python3.12-venv`)*

### 2. Activate the Virtual Environment

Before installing packages or running the script, you need to activate the environment.

**On Linux/macOS:**
```bash
source venv/bin/activate
```
You will know it's active because your shell prompt will be prefixed with `(venv)`.

**On Windows:**
```bash
venv\Scripts\activate
```

### 3. Install Dependencies

Once the virtual environment is active, install `pydantic`.

```bash
pip install pydantic
```

## Running the Simulation

The `main.py` script runs the entire proof-of-concept simulation. It will execute the evolutionary loop for several generations to populate the elite map and then run several "exploitation" tasks using the bandit allocator.

To run the simulation, execute the `snackTraveler` package as a module using the `-m` flag. This ensures that Python's imports work correctly.

```bash
python3 -m snackTraveler.main
```

You will see output detailing the progress of each generation and each bandit run.

## Running the Unit Tests

The project includes a suite of unit tests to verify the correctness of all core components. The tests are located in the `snackTraveler/tests/` directory.

To run all tests, use Python's built-in `unittest` discovery feature.

```bash
python3 -m unittest discover snackTraveler/tests
```

If all tests are successful, you will see an `OK` message at the end of the output.
