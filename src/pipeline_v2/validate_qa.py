"""
Validation script for playback_history_qa table (APP-13).
Queries top artists and listening counts to verify data integrity.
"""

import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = "secret-compass-181513"
DATASET_V2 = "spotify_v2"
QA_TABLE = f"{PROJECT_ID}.{DATASET_V2}.playback_history_qa"

def validate():
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
    SELECT artist_name, COUNT(*) as play_count
    FROM `{QA_TABLE}`
    WHERE user_id = 'sergebou'
    GROUP BY artist_name
    ORDER BY play_count DESC
    LIMIT 10
    """

    logger.info("Running top artists validation query on QA table...")
    results = client.query(query).result()

    print("\n--- TOP 10 HISTORICAL ARTISTS (QA TABLE) ---")
    for row in results:
        print(f"{row.artist_name}: {row.play_count:,} plays")

    count_query = f"SELECT COUNT(*) as total FROM `{QA_TABLE}` WHERE user_id = 'sergebou'"
    total = list(client.query(count_query).result())[0].total
    print(f"\nTotal verified scrobbles in QA table: {total:,}\n")

if __name__ == "__main__":
    validate()
