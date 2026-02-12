#!/usr/bin/env python3
"""
Example script demonstrating how to use the media dataset functionality.
"""

from snackPersona.utils.data_models import MediaItem
from snackPersona.utils.media_dataset import MediaDataset
from snackPersona.evaluation.diversity import DiversityEvaluator

# Example 1: Creating a media dataset programmatically
print("=== Example 1: Creating a Media Dataset ===")
dataset = MediaDataset()

# Add media items
media1 = MediaItem(
    id="test_001",
    title="Understanding Machine Learning",
    content="Machine learning is transforming how computers process information...",
    category="technology"
)

media2 = MediaItem(
    id="test_002",
    title="The Art of Programming",
    content="Programming is both a science and an art form...",
    category="technology"
)

dataset.add_media_item(media1)
dataset.add_media_item(media2)

print(f"Dataset contains {len(dataset)} items")
print(f"First item: {dataset.get_media_item('test_001').title}")

# Example 2: Saving and loading a dataset
print("\n=== Example 2: Saving and Loading ===")
dataset.save_to_file("/tmp/my_media_dataset.json")
print("Dataset saved to /tmp/my_media_dataset.json")

new_dataset = MediaDataset("/tmp/my_media_dataset.json")
print(f"Loaded dataset contains {len(new_dataset)} items")

# Example 3: Evaluating diversity of reactions
print("\n=== Example 3: Diversity Evaluation ===")

# Simulate some reactions
reactions = [
    {"author": "Alice", "content": "This is amazing! I love how AI can help us create art."},
    {"author": "Bob", "content": "The technical implementation is quite elegant and efficient."},
    {"author": "Charlie", "content": "But what are the ethical implications? We should consider this carefully."},
    {"author": "Dana", "content": "Important topic. What evidence do we have that this approach works?"}
]

diversity_score = DiversityEvaluator.calculate_overall_diversity(reactions)
print(f"Overall diversity score: {diversity_score:.3f}")

lexical = DiversityEvaluator.calculate_lexical_diversity([r['content'] for r in reactions])
print(f"Lexical diversity: {lexical:.3f}")

semantic = DiversityEvaluator.calculate_semantic_diversity(reactions)
print(f"Semantic diversity: {semantic:.3f}")

# Example 4: Loading the sample dataset
print("\n=== Example 4: Using the Sample Dataset ===")
try:
    sample_dataset = MediaDataset("snackPersona/sample_media_dataset.json")
    print(f"Sample dataset contains {len(sample_dataset)} items:")
    for item in sample_dataset:
        print(f"  - {item.title} ({item.category})")
except FileNotFoundError:
    print("Sample dataset not found. Run from repository root.")

print("\n=== Examples Complete ===")
