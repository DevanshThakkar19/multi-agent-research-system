"""Generate answers from retrieved context."""
from typing import Dict, List, Optional
from openai import OpenAI
from loguru import logger

from ..utils.config import settings
from ..evaluation.metrics import QueryType

# Try to import Phoenix / OpenInference instrumentation
# IMPORTANT: Instrumentation must happen at module level BEFORE any OpenAI client is created
_PHOENIX_INSTRUMENTED = False
try:
    from phoenix.otel import register as phoenix_register
    from openinference.instrumentation.openai import OpenAIInstrumentor
    PHOENIX_AVAILABLE = True
    
    # Try to instrument OpenAI at module level (only once)
    try:
        tracer_provider = phoenix_register()
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        _PHOENIX_INSTRUMENTED = True
        logger.info("Phoenix monitoring enabled - OpenAI instrumented at module level")
    except Exception as e:
        logger.warning(f"Phoenix instrumentation failed (Phoenix may not be running): {e}")
        logger.info("Start Phoenix first: python start_phoenix.py")
        PHOENIX_AVAILABLE = False
except ImportError:
    PHOENIX_AVAILABLE = False
    logger.info("Phoenix/OpenInference not available, monitoring disabled")


class AnswerGenerator:
    """Generate answers using LLM with retrieved context."""
    
    def __init__(self):
        # OpenAI client is created AFTER instrumentation (which happens at module level)
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    def generate_answer(
        self,
        query: str,
        context: str,
        query_type: QueryType,
        temperature: float = 0.7
    ) -> Dict:
        """
        Generate answer from query and context.
        
        Args:
            query: User query
            context: Retrieved context
            query_type: Type of query
            temperature: Sampling temperature
        
        Returns:
            Dictionary with answer and metadata
        """
        system_prompt = self._get_system_prompt(query_type)
        user_prompt = self._create_user_prompt(query, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Post-process answer
            processed_answer = self._post_process_answer(answer, query_type)
            
            # Extract sources
            sources = self._extract_sources(context)
            
            return {
                "answer": processed_answer,
                "sources": sources,
                "metadata": {
                    "model": self.model,
                    "query_type": query_type.value,
                    "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None
                }
            }
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            raise
    
    def _get_system_prompt(self, query_type: QueryType) -> str:
        """Get system prompt based on query type."""
        base_prompt = """You are a helpful assistant that answers questions based on provided context.
Your answers should be:
- Accurate and based only on the provided context
- Clear and well-structured
- Concise but complete
- Extract and use information directly from the context

IMPORTANT: Carefully read the context provided. If the context mentions the answer (even partially), extract and present that information. Only say "the context does not contain information" if you have thoroughly searched the context and found absolutely no relevant information."""
        
        type_specific = {
            QueryType.LOOKUP: "For factual lookup queries, provide direct, precise answers.",
            QueryType.SUMMARIZATION: "For summarization queries, provide comprehensive summaries covering key points.",
            QueryType.SEMANTIC_LINKAGES: "For relationship queries, explain connections and relationships clearly.",
            QueryType.REASONING: "For reasoning queries, show your reasoning process step by step."
        }
        
        return f"{base_prompt}\n\n{type_specific.get(query_type, '')}"
    
    def _create_user_prompt(self, query: str, context: str) -> str:
        """Create user prompt with query and context."""
        # Check if query is about audio transcription (including video audio)
        audio_keywords = ["audio", "said", "transcription", "transcribe", "transcript", "spoken", "speech", "what was", "what does", "video say", "video said", "video talk", "give transcript", "show transcript", "talk", "talks"]
        is_audio_query = any(keyword in query.lower() for keyword in audio_keywords)
        
        audio_instructions = ""
        if is_audio_query:
            audio_instructions = """
CRITICAL FOR AUDIO/VIDEO QUERIES:
- Look for ALL segments marked as "[Source: ... | Audio Transcription]" OR "[Source: ... | Video Content]"
- If the context contains transcribed text from audio/video, that IS the answer
- Combine ALL audio/video transcription segments into ONE complete answer
- Present them in order as a continuous transcript
- Do NOT skip any transcription segments
- The complete transcription IS the answer to "what was said" or "what does the video say"
- Even if marked as "Video Content", if it contains transcribed text, that is the answer
"""
        
        return f"""Context:
{context}

Question: {query}
{audio_instructions}
         Instructions:
         1. Carefully read through the entire context above
         2. Extract ALL information that relates to the question - be comprehensive
         3. For audio/video-related queries (e.g., "what was said", "what does the video say", "transcription"):
            - If the context contains transcribed text from audio/video files, that IS the answer
            - Find ALL segments marked as "Audio Transcription" OR "Video Content" and combine them
            - Video Content that contains transcribed text should be treated as the answer
            - Present the COMPLETE transcribed text as the answer - include all relevant sentences
            - Multiple transcription segments should be combined in order into one coherent response
            - Do not truncate or shorten the answer - provide the full transcription
         4. If you find relevant information, provide a clear and COMPLETE answer based on that information
         5. If the context explicitly mentions the answer (even if phrased differently), extract and present it fully
         6. Only say the context doesn't contain information if you have thoroughly searched and found nothing relevant
         7. IMPORTANT: Provide the same complete answer regardless of whether the query ends with a question mark or not

         Answer the question based on the provided context:"""
    
    def _post_process_answer(self, answer: str, query_type: QueryType) -> str:
        """Post-process answer to improve quality."""
        # Remove any hallucination markers
        answer = answer.replace("[I don't have enough information]", "")
        answer = answer.replace("[Not in context]", "")
        
        # Ensure answer ends with proper punctuation
        if answer and answer[-1] not in ".!?":
            answer += "."
        
        return answer.strip()
    
    def _extract_sources(self, context: str) -> List[str]:
        """Extract source information from context."""
        sources = []
        lines = context.split("\n")
        
        for line in lines:
            if line.startswith("[Source:"):
                source = line.replace("[Source:", "").replace("]", "").strip()
                if source not in sources:
                    sources.append(source)
        
        return sources

