# Persona Store

**Module:** `snackPersona/persona_store/store.py`

This module handles the persistence of persona data (genotypes). It saves and loads generations of personas to/from JSON files in a specified directory.

## Sequence Diagram (Save/Load)

```mermaid
sequenceDiagram
    participant Engine
    participant Store
    participant FileSystem

    Engine->>Store: save_generation(gen_id, population)
    Store->>Store: Serialize population to JSON
    Store->>FileSystem: Write "gen_{gen_id}.json"
    
    Engine->>Store: load_generation(gen_id)
    Store->>FileSystem: Read "gen_{gen_id}.json"
    FileSystem-->>Store: JSON Data
    Store->>Store: Deserialize to List[PersonaGenotype]
    Store-->>Engine: Population List
```

## Implementation Details

- **PersonaStore Class**: The main class for storage operations.
- **Storage Strategy**:
    - Each generation is saved as a separate JSON file (`gen_X.json`).
    - The file contains a list of serialized `PersonaGenotype` objects.
- **Dependencies**: Requires `snackPersona.utils.data_models` for `PersonaGenotype` deserialization.
