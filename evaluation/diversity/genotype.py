def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two sets. Returns 0-1."""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def calculate_genotype_distance(g1, g2) -> float:
    """
    Structural distance between two PersonaGenotype instances.

    Compares fields by type:
      - List fields  → 1 - Jaccard similarity
      - String fields → 0 if equal, 1 if different
      - Numeric (age) → normalised absolute difference

    Returns:
        0.0 (identical) to 1.0 (completely different).
    """
    distances = []

    # List fields — Jaccard distance
    for field in ('core_values', 'hobbies', 'goals'):
        s1 = set(getattr(g1, field, []))
        s2 = set(getattr(g2, field, []))
        distances.append(1.0 - jaccard_similarity(s1, s2))

    # String fields — exact match
    for field in ('occupation', 'communication_style', 'topical_focus',
                  'interaction_policy', 'backstory'):
        v1 = getattr(g1, field, '')
        v2 = getattr(g2, field, '')
        distances.append(0.0 if v1 == v2 else 1.0)

    # Numeric — normalised diff (age range roughly 18-80)
    age_diff = abs(g1.age - g2.age) / 62.0
    distances.append(min(age_diff, 1.0))

    # Personality traits — compare shared keys
    all_keys = set(g1.personality_traits.keys()) | set(g2.personality_traits.keys())
    if all_keys:
        trait_diffs = []
        for k in all_keys:
            v1 = g1.personality_traits.get(k, 0.5)
            v2 = g2.personality_traits.get(k, 0.5)
            trait_diffs.append(abs(v1 - v2))
        distances.append(sum(trait_diffs) / len(trait_diffs))
    else:
        distances.append(0.0)

    return sum(distances) / len(distances)
