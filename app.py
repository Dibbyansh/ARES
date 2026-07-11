# Entry point — interactive CLI for the emergency response system
import json

from coordinator_langgraph import handle_incident_with_langgraph
from tools.rag import load_knowledge_base, knowledge_base_count
from tools.db import load_teams_from_file

if __name__ == "__main__":
    # Print startup banner
    print("=" * 60)
    print("   ARES - Emergency Response System")
    print("=" * 60)
    
    # Load team roster from JSON into the database
    print("\n📋 Loading emergency response teams...")
    with open("teams.json", "r") as file:
        teams_data = json.load(file)["teams"]
    
    load_teams_from_file(teams_data)
    print(f"✓ Loaded {len(teams_data)} teams (fire, medical, police, etc.)")
    
    # Index emergency guidelines into ChromaDB on first run
    print("\n📚 Loading emergency response guidelines...")
    if knowledge_base_count() == 0:
        load_knowledge_base()
        print(f"✓ Loaded {knowledge_base_count()} guidelines")
    else:
        print(f"✓ Knowledge base ready ({knowledge_base_count()} guidelines)")
    
    # Ready for user input
    print("\n" + "=" * 60)
    print("Ready! Type an emergency incident and press Enter.")
    print("Type 'exit' or 'quit' to stop the program.")
    print("=" * 60 + "\n")
    
    # Main REPL loop — read incident, dispatch to coordinator, repeat
    while True:
        try:
            user_input = input("ARES> ").strip()
            
            if not user_input:
                continue
            
            # Exit on quit command
            if user_input.lower() in ["exit", "quit"]:
                print("\n👋 Shutting down ARES. Stay safe!\n")
                break
            
            print()
            
            # Route incident through the LangGraph coordinator
            handle_incident_with_langgraph(user_input)
            
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down ARES. Stay safe!\n")
            break
        except Exception as error:
            print(f"\n❌ Error: {error}")
            print("Please try again or type 'exit' to quit.\n")