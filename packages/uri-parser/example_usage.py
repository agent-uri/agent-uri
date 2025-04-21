"""
Example usage of the Agent URI Parser.
"""

from agent_uri.parser import parse_agent_uri, AgentUri

def main():
    """Demonstrate basic usage of the AgentUri parser."""
    print("Agent URI Parser Example")
    print("-----------------------")
    
    # Example 1: Parse a basic agent URI
    uri1 = "agent://acme.ai/planning/generate-itinerary"
    print(f"\nParsing: {uri1}")
    parsed1 = parse_agent_uri(uri1)
    print(f"Authority: {parsed1.authority}")
    print(f"Path: {parsed1.path}")
    print(f"Full URI (round-trip): {parsed1}")
    
    # Example 2: Parse a URI with transport binding
    uri2 = "agent+https://example.com/assistant?query=hello"
    print(f"\nParsing: {uri2}")
    parsed2 = parse_agent_uri(uri2)
    print(f"Transport: {parsed2.transport}")
    print(f"Authority: {parsed2.authority}")
    print(f"Query parameters: {parsed2.query}")
    print(f"Full URI (round-trip): {parsed2}")
    
    # Example 3: Create an AgentUri from components
    print("\nCreating from components:")
    agent_uri = AgentUri(
        transport="wss",
        authority="example.com:8080",
        path="path/to/agent",
        query={"param1": "value1", "param2": "value2"},
        fragment="section",
        host="example.com",
        port=8080
    )
    print(f"Constructed URI: {agent_uri}")
    print(f"Dictionary representation: {agent_uri.to_dict()}")

if __name__ == "__main__":
    main()
