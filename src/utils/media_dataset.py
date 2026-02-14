import json
import os
from typing import List, Optional
from snackPersona.utils.data_models import MediaItem


class MediaDataset:
    """
    Manages a collection of media items (articles, text content) that personas can react to.
    """
    
    def __init__(self, dataset_path: Optional[str] = None):
        """
        Initialize the media dataset.
        
        Args:
            dataset_path: Optional path to a JSON file containing media items.
                         If None, starts with an empty dataset.
        """
        self.media_items: List[MediaItem] = []
        
        if dataset_path and os.path.exists(dataset_path):
            self.load_from_file(dataset_path)
    
    def add_media_item(self, media_item: MediaItem):
        """Add a single media item to the dataset."""
        self.media_items.append(media_item)
    
    def add_media_items(self, media_items: List[MediaItem]):
        """Add multiple media items to the dataset."""
        self.media_items.extend(media_items)
    
    def get_media_item(self, media_id: str) -> Optional[MediaItem]:
        """Get a media item by its ID."""
        for item in self.media_items:
            if item.id == media_id:
                return item
        return None
    
    def get_all_media_items(self) -> List[MediaItem]:
        """Get all media items in the dataset."""
        return self.media_items.copy()
    
    def get_media_by_category(self, category: str) -> List[MediaItem]:
        """Get all media items in a specific category."""
        return [item for item in self.media_items if item.category == category]
    
    def save_to_file(self, filepath: str):
        """
        Save the dataset to a JSON file.
        
        Args:
            filepath: Path where the JSON file should be saved.
        """
        data = [item.model_dump() for item in self.media_items]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: str):
        """
        Load media items from a JSON file.
        
        Args:
            filepath: Path to the JSON file containing media items.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.media_items = [MediaItem(**item) for item in data]
    
    def __len__(self) -> int:
        """Return the number of media items in the dataset."""
        return len(self.media_items)
    
    def __iter__(self):
        """Make the dataset iterable."""
        return iter(self.media_items)
