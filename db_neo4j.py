from neo4j import Driver, GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()  # reads variables from a .env file and sets them in os.environ

db_user = os.getenv("NEO4J_USER")
db_password = os.getenv("NEO4J_PASSWORD")
db_uri = os.getenv('NEO4J_URI')

if not db_user or not db_password or not db_uri:
    raise ValueError("NEO4J_USER and NEO4J_PASSWORD environment variables must be set")


AUTH = (db_user, db_password)

def ex_query(query, parameters=None):
    if not db_uri:
        raise ValueError("NEO4J_URI environment variable must be set")
    
    with GraphDatabase.driver(db_uri, auth=AUTH) as driver:
        driver.verify_connectivity()
        print("Connection established.")

        records, summary, keys = driver.execute_query(
            query,
            parameters or {},
            database_="neo4j",
        )
        return records, summary, keys


def execute_create_event_node(event_id: str, start_time: str, stop_time: str | None = None, location: str = "", summary: str = ""):
    query = """
    MERGE (e:Event {event_id: $event_id, location: $location, start_time: $start_time, stop_time: $stop_time, summary: $summary})
    RETURN e
    """
    parameters = {
        "event_id": event_id, 
        "location": location, 
        "start_time": start_time, 
        "stop_time": stop_time or None,  
        "summary": summary
    }
    return ex_query(query, parameters)