# hybrid_npc_chat.py
from llms.groq import chat
from db_neo4j import ex_query
from npc_chat import get_npc_context, build_npc_system_prompt
from query_rag import query_rag, DATABASE_SCHEMA
# from query_rag import generate_cypher_query
import json


def classify_question(user_message: str) -> dict:
    """
    Avgör om frågan behöver databas-lookup eller bara personlighet/minnen.
    """
    prompt = f"""
Classify this question/statement into one of these categories:

1. FACTUAL - Needs database verification:
   - Questions about who, what, when, where
   - Statements about relationships ("X is your father")
   - Claims about facts that could be true or false
   - Asking about events, times, locations, people present
   
2. EMOTIONAL - About feelings, opinions, interpretations:
   - How did you feel...
   - What do you think about...
   - Why did you...
   - Your subjective experience
   
3. GENERAL - Small talk, greetings, no specific info needed

IMPORTANT: If someone makes a statement about a fact or relationship, classify as FACTUAL 
so it can be verified against the database.

Examples:
- "So Alrik is your father" → FACTUAL (needs verification)
- "Who was at dinner?" → FACTUAL (needs database query)
- "How did you feel?" → EMOTIONAL (use memories)
- "Hello" → GENERAL (no lookup needed)

Question/Statement: "{user_message}"

Return JSON: {{"type": "FACTUAL|EMOTIONAL|GENERAL", "reason": "brief explanation"}}
"""
    
    response = chat(prompt)
    
    # Parse JSON
    try:
        # Ta bort markdown om det finns
        if "```" in response:
            response = response.split("```")[1].replace("json", "").strip()
        return json.loads(response)
    except:
        # Fallback - leta efter nyckelord
        msg_lower = user_message.lower()
        if any(word in msg_lower for word in ["is your", "was your", "who", "what", "when", "where", "which"]):
            return {"type": "FACTUAL", "reason": "Contains factual keywords"}
        return {"type": "GENERAL", "reason": "Failed to parse, defaulting to general"}

# def query_for_context(user_message: str, npc_name: str) -> list:
#     """
#     Generera och kör query för att få relevant kontext.
#     """
#     print(f"🔍 Fetching context from database...")
    
#     # Förbättrad prompt som hanterar påståenden
#     query_prompt = f"""
# {DATABASE_SCHEMA}

# The NPC "{npc_name}" is being asked/told: "{user_message}"

# Generate a Cypher query to verify or find relevant information.

# If it's a statement (e.g., "X is your father"), find the ACTUAL relationship.
# If it's a question, find the requested information.

# Focus on data related to {npc_name}.

# Return ONLY the Cypher query, no explanation.
# """
    
#     cypher = chat(query_prompt).strip()
    
#     # Ta bort markdown
#     if cypher.startswith("```"):
#         lines = cypher.split("\n")
#         cypher = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    
#     print(f"📝 Query: {cypher}")
    
#     try:
#         records, _, _ = ex_query(cypher)
#         results = [dict(r) for r in records]
#         print(f"✅ Found {len(results)} results")
#         return results
#     except Exception as e:
#         print(f"❌ Query failed: {e}")
#         return []
    
  
def chat_with_npc_hybrid(npc_name: str, user_message: str) -> str:
    """
    Hybrid NPC chat: Kombinerar personlighet med dynamic query RAG.
    """
    print(f"\n{'='*60}")
    print(f"💬 {npc_name} | Question: {user_message}")
    print('='*60)
    
    # 1. Klassificera frågan
    classification = classify_question(user_message)
    print(f"\n🏷️  Type: {classification['type']} - {classification['reason']}")
    
    # 2. Hämta NPC base context
    npc_context = get_npc_context(npc_name)
    if not npc_context:
        return f"Error: NPC '{npc_name}' not found"
    
    # 3. Om FACTUAL - hämta extra kontext via query
    additional_context = ""
    if classification['type'] == 'FACTUAL':
        # query_results = query_for_context(user_message, npc_name)
        query_results = query_rag(user_message)
        
        if query_results:
          additional_context = f"""

          VERIFIED DATA FROM DATABASE:
          {json.dumps(query_results, indent=2)}

          IMPORTANT: Use this data to verify facts. If the user made an incorrect statement, 
          correct them naturally in character. For example, if they say "your father" but 
          the database shows "UNCLE_OF", correct them: "My uncle, not father."
          """
        else:
            additional_context = "NO VERIFIED DATA FROM DATABASE FOUND, YOU CAN'T DISPUTE OR ACCEPT THE FACT. DON'T SAY ANYTHING YOU CAN'T VERIFY SPECIFICALLY"
    
    # 4. Bygg prompt
    base_prompt = build_npc_system_prompt(npc_context)
    
    full_prompt = f"""{base_prompt}
{additional_context}

User says: "{user_message}"

Respond in character as {npc_name}. 
- If the user stated a fact, verify it against the database data above
- If they're wrong, correct them naturally in character
- If they're right, confirm or elaborate
- Stay true to your personality and how you'd react to being corrected or questioned
"""
    print('full prompt: ', full_prompt)
    
    # 5. Få svar från LLM
    # print("\n💭 Generating response...\n")
    response = chat(full_prompt)
    
    return response




def interactive_hybrid_chat(npc_name: str):
    """
    Interaktiv chat med hybrid RAG.
    """
#     print(f"""
# ╔════════════════════════════════════════════════════════════╗
# ║     Hybrid NPC Chat with Query RAG                        ║
# ║     Chatting with: {npc_name:<39} ║
# ╚════════════════════════════════════════════════════════════╝

# The NPC will:
# - Use their personality and memories for emotional questions
# - Query the database for factual questions
# - Combine both for complex questions

# Type 'exit' to quit.
# """)
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            # print(f"\n{npc_name}: Farewell.\n")1
            break
        
        if not user_input:
            continue
        
        response = chat_with_npc_hybrid(npc_name, user_input)
        print(f"\n{npc_name}: {response}\n")
        print("-" * 60)


if __name__ == "__main__":
    # Test med olika typer av frågor
    test_questions = [
        "Who was at dinner with you?",  # FACTUAL
        "How did you feel about your uncle?",  # EMOTIONAL
        "Hello, how are you?",  # GENERAL
        "What happened in the Great hall at 20:00?",  # FACTUAL
    ]
    
    npc_name = "Elin von Dahlen"
    
    # print("Testing with sample questions...\n")
    # for q in test_questions:
    #     response = chat_with_npc_hybrid(npc_name, q)
    #     print(f"\n{npc_name}: {response}\n")
    #     print("=" * 60)
    #     input("Press Enter for next...")
    
    # Interactive mode
    interactive_hybrid_chat(npc_name)