from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls, model_name: str = 'all-MiniLM-L6-v2'):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            try:
                logger.info(f"Loading embedding model: {model_name}")
                cls._model = SentenceTransformer(model_name)
                logger.info(f"Embedding model '{model_name}' loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load embedding model '{model_name}': {e}", exc_info=True)
                # Depending on the application's needs, you might want to raise the exception
                # or handle it by setting _model to None and letting methods fail gracefully.
                cls._model = None # Ensure model is None if loading failed
                # raise e # Or re-raise to make the application aware of the failure
        return cls._instance

    def get_embedding(self, text: str) -> list[float] | None:
        """Generates an embedding for the given text."""
        if self._model is None:
            logger.error("Embedding model is not loaded. Cannot generate embedding.")
            return None
        if not text or not isinstance(text, str):
            logger.warning("Invalid input text for embedding. Must be a non-empty string.")
            return None
        try:
            embedding = self._model.encode(text, convert_to_tensor=False) # Get numpy array
            return embedding.tolist() # Convert to list of floats
        except Exception as e:
            logger.error(f"Error generating embedding for text '{text[:50]}...': {e}", exc_info=True)
            return None

# Example usage (optional, for testing):
if __name__ == '__main__':
    # Configure basic logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Test service instantiation and model loading
    service1 = EmbeddingService()
    service2 = EmbeddingService() # Should return the same instance

    print(f"Service1 is Service2: {service1 is service2}")

    if service1._model:
        # Test embedding generation
        text1 = "This is a test sentence."
        embedding1 = service1.get_embedding(text1)
        if embedding1:
            print(f"Embedding for '{text1}': {embedding1[:5]}... (length: {len(embedding1)})")

        text2 = "Another example sentence for semantic comparison."
        embedding2 = service1.get_embedding(text2)
        if embedding2:
            print(f"Embedding for '{text2}': {embedding2[:5]}... (length: {len(embedding2)})")
        
        # Test invalid input
        invalid_embedding = service1.get_embedding("")
        print(f"Embedding for empty string: {invalid_embedding}")

        invalid_embedding_type = service1.get_embedding(123)
        print(f"Embedding for non-string input: {invalid_embedding_type}")
    else:
        print("Embedding model failed to load. Cannot run embedding tests.")

    # Test with a different model name (will still use the first loaded model due to singleton pattern)
    # To truly test with a different model, you'd need to reset _instance and _model or change the pattern.
    # service_alt_model = EmbeddingService(model_name='paraphrase-MiniLM-L3-v2') 
    # print(f"Service1 is Service_alt_model: {service1 is service_alt_model}") # Still True
