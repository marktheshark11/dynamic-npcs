from llms.groq import chat
from db_neo4j import ex_query
from typing import List, Dict, Any, Optional


def get_npc_context(npc_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve all context for an NPC from Neo4j database.
    Returns personality, traits, memories, and related events.
    """
    query = """
    MATCH (npc:NPC {name: $npc_name})
    OPTIONAL MATCH (npc)-[:HAS_PERSONALITY]->(p:Personality)
    OPTIONAL MATCH (p)-[:HAS_TRAIT]->(t:Trait)
    OPTIONAL MATCH (npc)-[:HAS_MEMORY]->(m:Memory)
    OPTIONAL MATCH (m)-[:MEMORY_OF]->(e:Event)
    RETURN 
        npc,
        p as personality,
        collect(DISTINCT t.trait) as traits,
        collect(DISTINCT {
            memory_id: m.memory_id,
            memory: m.memory,
            event_id: e.event_id,
            event_location: e.location,
            event_time: e.start_time + ' - ' + e.stop_time,
            event_summary: e.summary
        }) as memories
    """
    
    records, summary, keys = ex_query(query, {"npc_name": npc_name})
    
    if not records:
        return None
    
    record = records[0]
    context = {
        "npc": dict(record["npc"]),
        "personality": dict(record["personality"]) if record["personality"] else None,
        "traits": record["traits"],
        "memories": [m for m in record["memories"] if m["memory_id"]]
    }
    return context


def build_npc_system_prompt(context: Dict[str, Any]) -> str:
    """
    Build a system prompt that instructs the LLM to roleplay as the NPC.
    """
    npc = context["npc"]
    personality = context["personality"]
    traits = context["traits"]
    memories = context["memories"]
    
    prompt = f"""You are {npc['name']}, a {npc.get('age', 'unknown age')} year old {npc.get('role', 'person')}.

PERSONALITY:
{personality['summary'] if personality else 'No personality data available.'}

YOUR TRAITS:
{', '.join(traits) if traits else 'No specific traits defined.'}

YOUR BEHAVIOR PATTERNS:
- Lying style: {personality['lie_style'] if personality else 'Unknown'}
- Conflict style: {personality['conflict_style'] if personality else 'Unknown'}
- Stress response: {personality['stress_response'] if personality else 'Unknown'}

YOUR MEMORIES AND EXPERIENCES:
"""
    
    for i, mem in enumerate(memories, 1):
        prompt += f"\n{i}. {mem['memory']}"
        if mem.get('event_summary'):
            prompt += f"\n   (Event: {mem['event_summary']})"
    
    prompt += """

INSTRUCTIONS:
- Stay in character at all times
- Draw from your memories and personality when responding
- Be consistent with your traits and behavioral patterns
- If asked about events, refer to your memories
- You may be evasive, lie, or reveal information based on your personality
- Respond naturally as this character would in conversation
"""
    print(prompt)
    return prompt


def chat_with_npc(npc_name: str, user_message: str) -> str:
    """
    Have a conversation with an NPC.
    
    Args:
        npc_name: Name of the NPC to chat with
        user_message: The user's message
    
    Returns:
        The NPC's response
    """
    # Get NPC context from database
    context = get_npc_context(npc_name)
    
    if not context:
        return f"Error: NPC '{npc_name}' not found in database."
    
    # Build system prompt with NPC's context
    system_prompt = build_npc_system_prompt(context)
    
    # Combine system prompt with user message
    full_prompt = system_prompt + "\n\nUser: " + user_message + "\n\nYou:"
    print(full_prompt)
    # Get response from LLM
    response = chat(full_prompt)
    
    return response


def interactive_npc_chat(npc_name: str):
    """
    Start an interactive chat session with an NPC.
    """
    print(f"\n=== Starting conversation with {npc_name} ===")
    print("Type 'exit' to end the conversation\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print(f"\n{npc_name}: Goodbye.\n")
            break
        
        if not user_input:
            continue
        
        # Get NPC response
        response = chat_with_npc(npc_name, user_input)
        
        print(f"\n{npc_name}: {response}\n")


if __name__ == "__main__":
    # Example: Chat with Elin von Dahlen
    interactive_npc_chat("Elin von Dahlen")
