import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import uuid
from .knowledge_manager import process_game_knowledge
from sentence_transformers import SentenceTransformer
class VectorService:
    def __init__(self, vector_db_dir: str = "vector_db"):
        """Initialize vector service with Chroma and SentenceTransformer embeddings."""
        self.vector_db_dir = vector_db_dir
        self.embedding_model = None
        self.chroma_client = None
        self.collections = {}
        
        # Ensure vector_db directory exists
        os.makedirs(vector_db_dir, exist_ok=True)
        
        # Initialize Chroma client
        self._init_chroma_client()
        
        # Initialize embedding client
        self._init_embedding_model()
    
    def _init_chroma_client(self):
        """Initialize Chroma client."""
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=self.vector_db_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            print("Chroma client initialized successfully")
        except Exception as e:
            print(f"Error initializing Chroma client: {e}")
            self.chroma_client = None
    
    def _init_embedding_model(self):
        """Initialize the sentence transformer embedder"""
        try:
            # api_key = os.getenv('MISTRAL_API_KEY')
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("Embedding model initialized successfully")
        except Exception as e:
            print(f"Error initializing embedding model: {e}")
            self.embedding_model = None
    
    def get_or_create_collection(self, game_name: str, content_type: str) -> Optional[chromadb.Collection]:
        """Get or create a Chroma collection for a specific game and content type."""
        if not self.chroma_client:
            return None
        
        collection_name = f"{game_name.lower()}_{content_type.lower()}"
        
        try:
            # Try to get existing collection
            collection = self.chroma_client.get_collection(collection_name)
            self.collections[collection_name] = collection
            return collection
        except Exception:
            # Collection doesn't exist, create it
            try:
                collection = self.chroma_client.create_collection(
                    name=collection_name.lower(),
                    metadata={"game": game_name, "content_type": content_type}
                )
                self.collections[collection_name] = collection
                return collection
            except Exception as e:
                print(f"Error creating collection {collection_name}: {e}")
                return None
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not self.embedding_model:
            return []
        
        try:
            embeddings = self.embedding_model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return []
    
    def chunk_text(self, text: str, max_length: int = 512) -> List[str]:
        """Split text into chunks for better embedding."""
        if not text:
            return []
        
        # Simple chunking by sentences
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def add_game_knowledge(self, game_name: str) -> bool:
        """Add all knowledge for a game to the vector database."""
        if not self.chroma_client or not self.embedding_model:
            print("Chroma client or embedding model not initialized")
            return False
        
        try:
            # Process knowledge from CSV
            knowledge = process_game_knowledge(game_name)
            
            # Process each content type
            for content_type, entries in knowledge.items():
                if not entries:
                    continue
                
                collection = self.get_or_create_collection(game_name, content_type)
                if not collection:
                    continue
                
                # Prepare data for Chroma
                documents = []
                metadatas = []
                ids = []
                
                for entry in entries:
                    # Chunk the content
                    content = entry.get('content', '')
                    if not content:
                        content = entry.get('description', '')
                    
                    chunks = self.chunk_text(content)
                    
                    for i, chunk in enumerate(chunks):
                        if not chunk.strip():
                            continue
                        
                        doc_id = f"{game_name}_{content_type}_{uuid.uuid4().hex[:8]}_{i}"
                        documents.append(chunk)
                        metadatas.append({
                            'game': game_name,
                            'content_type': content_type,
                            'url': entry.get('url', ''),
                            'title': entry.get('title', ''),
                            'description': entry.get('description', ''),
                            'chunk_index': i,
                            'total_chunks': len(chunks)
                        })
                        ids.append(doc_id)
                
                if documents:
                    # Generate embeddings
                    embeddings = self.generate_embeddings(documents)
                    
                    if embeddings:
                        # Add to collection
                        collection.add(
                            documents=documents,
                            metadatas=metadatas,
                            ids=ids,
                            embeddings=embeddings
                        )
                        print(f"Added {len(documents)} chunks for {game_name} {content_type}")
                    else:
                        print(f"Failed to generate embeddings for {game_name} {content_type}")
            
            return True
            
        except Exception as e:
            print(f"Error adding game knowledge for {game_name}: {e}")
            return False
    
    def search_knowledge(self, game_name: str, query: str, content_types: List[str] = None, 
                        limit: int = 5) -> List[Dict]:
        """Search knowledge base for relevant information."""
        if not self.chroma_client or not self.embedding_model:
            return []
        
        if content_types is None:
            content_types = ['wiki', 'youtube', 'forum']
        
        try:
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])
            if not query_embedding:
                return []
            
            all_results = []
            
            # Search each content type
            for content_type in content_types:
                collection_name = f"{game_name.lower()}_{content_type.lower()}"
                
                if collection_name in self.collections:
                    collection = self.collections[collection_name]
                else:
                    collection = self.chroma_client.get_collection(collection_name)
                    self.collections[collection_name] = collection
                
                # Search collection
                results = collection.query(
                    query_embeddings=query_embedding,
                    n_results=limit,
                    include=['documents', 'metadatas', 'distances']
                )
                
                # Process results
                if results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        all_results.append({
                            'content': doc,
                            'metadata': results['metadatas'][0][i],
                            'distance': results['distances'][0][i],
                            'content_type': content_type
                        })
            
            # Sort by distance (lower is better)
            all_results.sort(key=lambda x: x['distance'])
            
            return all_results[:limit]
            
        except Exception as e:
            print(f"Error searching knowledge for {game_name}: {e}")
            return []
    
    def get_game_stats(self, game_name: str) -> Dict[str, int]:
        """Get statistics for a game's knowledge base."""
        if not self.chroma_client:
            return {}
        
        stats = {}
        content_types = ['wiki', 'youtube', 'forum']
        
        for content_type in content_types:
            collection_name = f"{game_name}_{content_type}"
            try:
                collection = self.chroma_client.get_collection(collection_name)
                count = collection.count()
                stats[content_type] = count
            except Exception:
                stats[content_type] = 0
        
        return stats
    
    def delete_game_knowledge(self, game_name: str) -> bool:
        """Delete all knowledge for a game."""
        if not self.chroma_client:
            return False
        
        try:
            content_types = ['wiki', 'youtube', 'forum']
            for content_type in content_types:
                collection_name = f"{game_name}_{content_type}"
                try:
                    self.chroma_client.delete_collection(collection_name)
                    if collection_name in self.collections:
                        del self.collections[collection_name]
                except Exception:
                    pass  # Collection might not exist
            
            return True
        except Exception as e:
            print(f"Error deleting game knowledge for {game_name}: {e}")
            return False
    
    def list_available_games(self) -> List[str]:
        """List all games with knowledge in the vector database."""
        if not self.chroma_client:
            return []
        
        try:
            collections = self.chroma_client.list_collections()
            games = set()
            
            for collection in collections:
                name = collection.name
                if '_' in name:
                    game_name = name.split('_')[0]
                    games.add(game_name)
            
            return list(games)
        except Exception as e:
            print(f"Error listing available games: {e}")
            return []

# Global instance
vector_service = VectorService()
