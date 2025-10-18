"""
Chat History Manager for Pixly
Stores conversation history in ChromaDB with timestamps and game context
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings


class ChatHistoryManager:
    """Manages chat history storage and retrieval using ChromaDB"""
    
    def __init__(self, persist_directory: str = "./vector_db", max_history: int = 30):
        """
        Initialize chat history manager
        
        Args:
            persist_directory: Directory for ChromaDB persistence
            max_history: Maximum number of chat messages to store per game
        """
        self.max_history = max_history
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
    
    def _get_collection_name(self, game: str) -> str:
        """Generate collection name for game's chat history"""
        return f"{game.lower().replace(' ', '_')}_chat_history"
    
    def _get_or_create_collection(self, game: str):
        """Get or create ChromaDB collection for a game's chat history"""
        collection_name = self._get_collection_name(game)
        try:
            collection = self.client.get_collection(name=collection_name)
        except:
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"game": game, "type": "chat_history"}
            )
        return collection
    
    def add_message(self, game: str, user_message: str, assistant_response: str) -> None:
        """
        Add a chat exchange to history
        
        Args:
            game: Name of the game
            user_message: User's input message
            assistant_response: Assistant's response
        """
        collection = self._get_or_create_collection(game)
        timestamp = datetime.now()
        
        # Create unique ID using timestamp
        message_id = f"{game}_{timestamp.timestamp()}"
        
        # Store the full conversation exchange as one document
        conversation_text = f"User: {user_message}\nAssistant: {assistant_response}"
        
        collection.add(
            documents=[conversation_text],
            metadatas=[{
                "game": game,
                "timestamp": timestamp.isoformat(),
                "user_message": user_message,
                "assistant_response": assistant_response,
                "unix_timestamp": timestamp.timestamp()
            }],
            ids=[message_id]
        )
        
        # Maintain max history limit
        self._trim_history(game)
    
    def _trim_history(self, game: str) -> None:
        """Remove oldest messages if exceeding max_history limit"""
        collection = self._get_or_create_collection(game)
        
        # Get all messages sorted by timestamp
        all_messages = collection.get(
            include=["metadatas"]
        )
        
        if len(all_messages["ids"]) > self.max_history:
            # Sort by unix timestamp
            messages_with_time = [
                (msg_id, meta["unix_timestamp"]) 
                for msg_id, meta in zip(all_messages["ids"], all_messages["metadatas"])
            ]
            messages_with_time.sort(key=lambda x: x[1])
            
            # Delete oldest messages
            to_delete = len(all_messages["ids"]) - self.max_history
            ids_to_delete = [msg[0] for msg in messages_with_time[:to_delete]]
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
    
    def get_recent_history(
        self, 
        game: str, 
        limit: Optional[int] = None,
        hours_ago: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get recent chat history for a game
        
        Args:
            game: Name of the game
            limit: Maximum number of messages to retrieve (default: all up to max_history)
            hours_ago: Only get messages from last N hours (optional)
        
        Returns:
            List of chat exchanges with timestamps
        """
        collection = self._get_or_create_collection(game)
        
        try:
            all_data = collection.get(include=["metadatas", "documents"])
            
            if not all_data["ids"]:
                return []
            
            # Filter by time if specified
            messages = []
            cutoff_time = None
            if hours_ago:
                cutoff_time = (datetime.now() - timedelta(hours=hours_ago)).timestamp()
            
            for meta, doc in zip(all_data["metadatas"], all_data["documents"]):
                if cutoff_time and meta["unix_timestamp"] < cutoff_time:
                    continue
                
                messages.append({
                    "user_message": meta["user_message"],
                    "assistant_response": meta["assistant_response"],
                    "timestamp": meta["timestamp"],
                    "unix_timestamp": meta["unix_timestamp"]
                })
            
            # Sort by timestamp (newest first)
            messages.sort(key=lambda x: x["unix_timestamp"], reverse=True)
            
            # Apply limit
            if limit:
                messages = messages[:limit]
            
            # Return in chronological order (oldest first for context)
            return list(reversed(messages))
            
        except Exception as e:
            print(f"Error retrieving chat history: {e}")
            return []
    
    def get_history_context(
        self, 
        game: str, 
        limit: int = 5,
        hours_ago: Optional[int] = None
    ) -> str:
        """
        Get formatted chat history as context string for Gemini
        
        Args:
            game: Name of the game
            limit: Number of recent messages to include
            hours_ago: Only include messages from last N hours
        
        Returns:
            Formatted string of recent chat history
        """
        history = self.get_recent_history(game, limit=limit, hours_ago=hours_ago)
        
        if not history:
            return ""
        
        context_parts = ["Previous conversation history:"]
        for msg in history:
            timestamp = datetime.fromisoformat(msg["timestamp"])
            time_str = timestamp.strftime("%Y-%m-%d %H:%M")
            context_parts.append(f"[{time_str}] User: {msg['user_message']}")
            context_parts.append(f"[{time_str}] Assistant: {msg['assistant_response']}")
        
        return "\n".join(context_parts)
    
    def search_history(
        self, 
        game: str, 
        query: str, 
        n_results: int = 5
    ) -> List[Dict[str, str]]:
        """
        Search chat history using semantic search
        
        Args:
            game: Name of the game
            query: Search query
            n_results: Number of results to return
        
        Returns:
            List of relevant chat exchanges
        """
        collection = self._get_or_create_collection(game)
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["metadatas", "documents", "distances"]
            )
            
            if not results["ids"][0]:
                return []
            
            messages = []
            for meta, doc, distance in zip(
                results["metadatas"][0], 
                results["documents"][0],
                results["distances"][0]
            ):
                messages.append({
                    "user_message": meta["user_message"],
                    "assistant_response": meta["assistant_response"],
                    "timestamp": meta["timestamp"],
                    "relevance_score": 1 - distance  # Convert distance to similarity
                })
            
            return messages
            
        except Exception as e:
            print(f"Error searching chat history: {e}")
            return []
    
    def clear_history(self, game: str) -> None:
        """Clear all chat history for a game"""
        collection_name = self._get_collection_name(game)
        try:
            self.client.delete_collection(name=collection_name)
        except:
            pass
    
    def get_stats(self, game: str) -> Dict[str, any]:
        """Get statistics about chat history for a game"""
        collection = self._get_or_create_collection(game)
        
        try:
            all_data = collection.get(include=["metadatas"])
            
            if not all_data["ids"]:
                return {
                    "total_messages": 0,
                    "oldest_message": None,
                    "newest_message": None
                }
            
            timestamps = [meta["unix_timestamp"] for meta in all_data["metadatas"]]
            
            return {
                "total_messages": len(all_data["ids"]),
                "oldest_message": datetime.fromtimestamp(min(timestamps)).isoformat(),
                "newest_message": datetime.fromtimestamp(max(timestamps)).isoformat()
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {"total_messages": 0}
