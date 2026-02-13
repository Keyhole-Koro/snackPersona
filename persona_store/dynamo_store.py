import json
import logging
from typing import List, Optional, Dict
from decimal import Decimal

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.utils.dynamo_client import get_table
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class DynamoDBStore:
    def __init__(self, table_name=None):
        self.table = get_table()
        # Mock storage_dir for compatibility if needed, but we don't use it.
        self.storage_dir = "dynamodb"

    def list_generations(self) -> List[int]:
        """Return a sorted list of available generation IDs from DynamoDB."""
        try:
            # Query GSI1 where GSI1PK="STATS" (sorted by SK or GSI1SK)
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={':pk': 'STATS'},
                ScanIndexForward=True
            )
            gens = [int(item['generation']) for item in response.get('Items', [])]
            return sorted(list(set(gens)))
        except ClientError as e:
            logger.error(f"Failed to list generations: {e}")
            return []

    def save_generation(self, generation_id: int, population: List[PersonaGenotype], stats: Optional[Dict] = None):
        """
        Saves generation data to DynamoDB.
        - Persists Archive (for reloading)
        - Persists Stats (for backend)
        - Persists Personas (for backend/frontend profile view)
        """
        try:
            with self.table.batch_writer() as batch:
                # 1. Save Archive
                archive_data = [p.model_dump() for p in population]
                batch.put_item(Item={
                    'PK': 'ARCHIVE',
                    'SK': f"GEN#{generation_id}",
                    'data': json.dumps(archive_data),
                    'generation': generation_id
                })

                # 2. Save Stats
                if stats:
                    batch.put_item(Item={
                        'PK': f"STATS#{generation_id}",
                        'SK': f"STATS#{generation_id}",
                        'GSI1PK': 'STATS',
                        'GSI1SK': str(generation_id).zfill(6),
                        'generation': generation_id,
                        'population_diversity': Decimal(str(stats.get('diversity', 0.0))),
                        'fitness_mean': Decimal(str(stats.get('fitness_mean', 0.0))),
                        'raw_stats': json.dumps(stats)
                    })

                # 3. Save Personas (Profiles)
                for p in population:
                    # PK=PERSONA, SK=PERSONA#<Name>
                    # GSI1PK=PERSONA, GSI1SK=<Name>
                    item = {
                        'PK': f"PERSONA#{p.name}",
                        'SK': f"PERSONA#{p.name}",
                        'GSI1PK': 'PERSONA',
                        'GSI1SK': p.name,
                        'id': p.name,
                        'name': p.name,
                        'bio': p.bio,
                        'is_active': True
                    }
                    batch.put_item(Item=item)
            
            logger.info(f"Saved generation {generation_id} to DynamoDB")
            
        except ClientError as e:
            logger.error(f"Failed to save generation {generation_id}: {e}")

    def load_generation(self, generation_id: int) -> List[PersonaGenotype]:
        """Load a list of PersonaGenotypes from DynamoDB archive."""
        try:
            response = self.table.get_item(
                Key={'PK': 'ARCHIVE', 'SK': f"GEN#{generation_id}"}
            )
            item = response.get('Item')
            if item and 'data' in item:
                data = json.loads(item['data'])
                return [PersonaGenotype(**p) for p in data]
        except ClientError as e:
            logger.error(f"Failed to load generation {generation_id}: {e}")
        return []

    def save_transcripts(self, generation_id: int, transcripts: List[List[dict]]):
        """Save conversation transcripts."""
        # Optional: Save to S3 or DynamoDB Archive
        pass
