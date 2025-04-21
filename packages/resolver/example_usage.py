#!/usr/bin/env python3
"""
Example usage of the agent URI resolver.

This script demonstrates how to use the agent resolver to:
1. Resolve agent:// URIs to descriptors and endpoints
2. Handle caching and different resolution methods
3. Handle errors in the resolution process
"""

import sys
import logging
from pprint import pprint

from agent_resolver import (
    AgentResolver,
    CacheProvider,
    ResolverError,
    ResolverNotFoundError,
    ResolverTimeoutError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Create sample data for mocked responses
SAMPLE_DESCRIPTOR = {
    "name": "acme-planner",
    "version": "1.0.0",
    "capabilities": [
        {
            "name": "generate-itinerary",
            "description": "Creates a travel itinerary"
        },
        {
            "name": "plan-tasks",
            "description": "Creates a task schedule"
        }
    ],
    "endpoints": {
        "https": "https://planner.acme.ai/api/agent",
        "wss": "wss://planner.acme.ai/ws"
    }
}

SAMPLE_REGISTRY = {
    "agents": {
        "planner": "https://planner.acme.ai/agent.json",
        "translator": "https://translator.acme.ai/agent.json"
    }
}


class MockResolver(AgentResolver):
    """A mock resolver that doesn't make actual HTTP requests."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def _fetch_json(self, url, **kwargs):
        """Override _fetch_json to return mock data based on URL."""
        logger.info(f"Mock fetching: {url}")
        
        # Handle domain root case (planner.acme.ai)
        if url == "https://planner.acme.ai/agent.json":
            return SAMPLE_DESCRIPTOR
        
        # For registry at acme.ai
        elif url == "https://acme.ai/.well-known/agents.json":
            return SAMPLE_REGISTRY
        
        # For well-known path at planner subdomain
        elif url == "https://planner.acme.ai/.well-known/agent.json":
            return SAMPLE_DESCRIPTOR
            
        # For path-based resolution with capability path
        elif url == "https://planner.acme.ai/generate-itinerary/agent.json":
            return SAMPLE_DESCRIPTOR
        
        # Default not found response
        else:
            raise ResolverNotFoundError(f"Resource not found: {url}")


def main():
    """Run the example."""
    # Create a resolver with default in-memory cache
    resolver = MockResolver(
        timeout=10,
        user_agent="AgentURI-Example/1.0"
    )
    
    # Example URIs to resolve
    uris = [
        "agent://planner.acme.ai/generate-itinerary",
        "agent://acme.ai/planner/generate-itinerary",
        "agent+wss://realtime.acme.ai/chat",
        "agent://nonexistent.example.com/"  # This will fail
    ]
    
    for uri in uris:
        logger.info(f"\n\nResolving URI: {uri}")
        
        try:
            # Attempt to resolve the URI
            descriptor, metadata = resolver.resolve(uri)
            
            # Print the resolution metadata
            print("\nResolution Metadata:")
            pprint(metadata)
            
            # Print descriptor info if available
            if descriptor:
                print("\nAgent Descriptor:")
                print(f"Name: {descriptor.name}")
                print(f"Version: {descriptor.version}")
                print(f"Capabilities: {[c.name for c in descriptor.capabilities]}")
                
                # Print endpoint information if available
                if hasattr(descriptor, 'endpoints') and descriptor.endpoints:
                    print("\nEndpoints:")
                    if descriptor.endpoints.https:
                        print(f"HTTPS: {descriptor.endpoints.https}")
                    if descriptor.endpoints.wss:
                        print(f"WebSocket: {descriptor.endpoints.wss}")
            else:
                print("\nNo descriptor found, but endpoint available from transport binding")
                print(f"Endpoint: {metadata.get('endpoint')}")
                
        except ResolverNotFoundError:
            logger.error(f"Agent not found: {uri}")
        except ResolverTimeoutError:
            logger.error(f"Resolution timed out: {uri}")
        except ResolverError as e:
            logger.error(f"Resolution error: {str(e)}")


class MockCacheResolver(MockResolver):
    """A mock resolver that demonstrates caching behavior."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Counter for fetch calls to demonstrate caching
        self.fetch_count = 0
        # Track if the cache is active
        self.cache_hit = False
    
    def _fetch_json(self, url, **kwargs):
        """Track number of fetches to demonstrate caching."""
        headers = kwargs.get('headers', {})
        
        # Check if this might be a conditional request
        has_etag = 'If-None-Match' in headers
        has_modified = 'If-Modified-Since' in headers
        
        if has_etag or has_modified:
            self.cache_hit = True
            logger.info(f"Cache hit detected for: {url}")
        else:
            self.fetch_count += 1
            logger.info(f"Fetch #{self.fetch_count}: {url}")
            
        return super()._fetch_json(url, **kwargs)


def example_with_custom_cache():
    """Example using a custom cache configuration."""
    # Create a custom SQLite-based cache
    cache = CacheProvider(
        cache_name="example_cache",
        backend="sqlite",
        expire_after=60 * 60,  # 1 hour
    )
    
    # Create mock resolver with custom cache
    resolver = MockCacheResolver(cache_provider=cache)
    
    # Example URI (use a URI we know will resolve successfully)
    uri = "agent://acme.ai/planner/generate-itinerary"
    
    try:
        # First request - simulated fetch from network
        print("\nMaking first request (uncached)...")
        descriptor1, metadata1 = resolver.resolve(uri)
        print(f"First request fetch count: {resolver.fetch_count}")
        print(f"Result: {descriptor1.name} via {metadata1['resolution_method']}")
        
        # Reset fetch count for clarity
        resolver.fetch_count = 0
        
        # Second request - should use cache
        print("\nMaking second request (should use cache)...")
        descriptor2, metadata2 = resolver.resolve(uri)
        print(f"Second request fetch count: {resolver.fetch_count}")
        print(f"Result: {descriptor2.name}")
        
        # Clear cache
        resolver.clear_cache()
        print("\nCache cleared")
        
        # Reset fetch count for clarity
        resolver.fetch_count = 0
        
        # Third request - simulated fetch from network again
        print("\nMaking third request (after cache clear)...")
        descriptor3, metadata3 = resolver.resolve(uri)
        print(f"Third request fetch count: {resolver.fetch_count}")
        print(f"Result: {descriptor3.name}")
        
    except ResolverError as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    try:
        main()
        
        print("\n\n--- Custom Cache Example ---\n")
        example_with_custom_cache()
        
    except KeyboardInterrupt:
        logger.info("Example interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)
