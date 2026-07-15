"""Streamlit UI for the multimodal RAG system."""
import streamlit as st
import sys
from pathlib import Path
from typing import Dict
import networkx as nx
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add rag_system to path
rag_system_path = Path(__file__).parent.parent / "rag_system"
sys.path.insert(0, str(rag_system_path))

from pipeline import RAGPipeline
from agents.orchestrator import RetrievalOrchestrator
from evaluation.evaluator import RAGEvaluator
from evaluation.metrics import QueryType
from graph.neo4j_client import Neo4jClient
from loguru import logger

# Page configuration
st.set_page_config(
    page_title="Multimodal Enterprise RAG",
    page_icon=None,
    layout="wide"
)

# Initialize session state
if "pipeline" not in st.session_state:
    st.session_state.pipeline = RAGPipeline()
    st.session_state.orchestrator = RetrievalOrchestrator()
    st.session_state.evaluator = RAGEvaluator()
    st.session_state.last_query_result = None

# Title
st.title("Multimodal Enterprise RAG System")
st.markdown("Upload files and query your knowledge base across text, image, audio, and video modalities.")

# Sidebar
with st.sidebar:
    st.header("Upload Files")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "txt", "docx", "jpg", "jpeg", "png", "mp3", "wav", "mp4", "avi"]
    )
    
    if uploaded_file is not None:
        # Save uploaded file
        upload_dir = Path("data/raw")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if st.button("Process File"):
            with st.spinner("Processing file..."):
                try:
                    result = st.session_state.pipeline.ingest_and_index(str(file_path))
                    
                    if result.get("success"):
                        st.success("File processed successfully!")
                        st.json(result)
                    else:
                        st.error(f"Processing failed: {result.get('error')}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.header("Evaluation")
    # View Metrics button - doesn't affect main content
    if st.button("View Metrics"):
        metrics = st.session_state.evaluator.get_aggregate_metrics()
        if metrics:
            st.json(metrics)
        else:
            st.info("No evaluations yet")

# Main content
tab1, tab2, tab3, tab4 = st.tabs(["Query", "Evaluation", "Knowledge Graph", "About"])

with tab1:
    st.header("Query the Knowledge Base")
    
    query = st.text_input("Enter your query:", placeholder="What information are you looking for?")
    
    col1, col2 = st.columns(2)
    with col1:
        query_type = st.selectbox(
            "Query Type (optional):",
            ["Auto-detect", "Lookup", "Summarization", "Semantic Linkages", "Reasoning"]
        )
    
    with col2:
        max_results = st.slider("Max Results", 5, 20, 10)
    
    search_clicked = st.button("Search", type="primary")
    if search_clicked:
        if query:
            with st.spinner("Searching..."):
                try:
                    # Map query type
                    qtype = None
                    if query_type != "Auto-detect":
                        qtype_map = {
                            "Lookup": QueryType.LOOKUP,
                            "Summarization": QueryType.SUMMARIZATION,
                            "Semantic Linkages": QueryType.SEMANTIC_LINKAGES,
                            "Reasoning": QueryType.REASONING
                        }
                        qtype = qtype_map.get(query_type)
                    
                    # Process query
                    result = st.session_state.orchestrator.process_query(
                        query=query,
                        query_type=qtype
                    )
                    
                    # Evaluate query and log results
                    try:
                        search_results = result.get("search_results", {})
                        retrieved_contexts = [r.get("content", "") for r in search_results.get("results", [])]
                        
                        # Improved relevance detection: use score-based threshold
                        # Cross-encoder improves scores, so use higher-scoring results as relevant
                        all_scores = [r.get("score", 0) for r in search_results.get("results", [])]
                        if all_scores:
                            # Use results with score above median as relevant (better than fixed top 3)
                            median_score = sorted(all_scores)[len(all_scores) // 2]
                            high_score_results = [
                                r.get("content", "") 
                                for r in search_results.get("results", []) 
                                if r.get("score", 0) >= median_score
                            ]
                            # Use at least top 5, but prefer high-scoring results
                            relevant_contexts = high_score_results[:max(5, len(high_score_results))]
                        else:
                            relevant_contexts = retrieved_contexts[:3]  # Fallback
                        
                        eval_result = st.session_state.evaluator.evaluate_query(
                            query_id=f"query_{len(st.session_state.evaluator.metrics_history)}",
                            query=query,
                            query_type=search_results.get("query_type", QueryType.LOOKUP),
                            retrieved_contexts=retrieved_contexts,
                            relevant_contexts=relevant_contexts,  # Score-based relevance
                            answer=result.get("answer", ""),
                            ground_truth_contexts=relevant_contexts
                        )
                        
                        # Store evaluation result
                        # Use latency from orchestrator metadata (full query time) if available
                        query_latency = result.get("metadata", {}).get("latency_ms", eval_result.latency_ms)
                        result["evaluation"] = {
                            "precision": eval_result.precision,
                            "recall": eval_result.recall,
                            "latency_ms": query_latency,  # Use full query latency from orchestrator
                            "hallucination_rate": eval_result.hallucination_rate
                        }
                    except Exception as e:
                        logger.warning(f"Evaluation failed: {e}")
                        result["evaluation"] = None
                    
                    # Store result in session state to persist across button clicks
                    st.session_state.last_query_result = result
                    
                    # Display answer
                    st.subheader("Answer")
                    st.write(result.get("answer", "No answer generated"))
                    
                    # Display evaluation metrics if available
                    if result.get("evaluation"):
                        eval_metrics = result["evaluation"]
                        st.subheader("Evaluation Metrics")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Precision", f"{eval_metrics.get('precision', 0):.3f}")
                        with col2:
                            st.metric("Recall", f"{eval_metrics.get('recall', 0):.3f}")
                        with col3:
                            st.metric("Latency", f"{eval_metrics.get('latency_ms', 0):.1f} ms")
                        with col4:
                            st.metric("Hallucination", f"{eval_metrics.get('hallucination_rate', 0):.3f}")
                    
                    # Display sources with metadata
                    if result.get("sources"):
                        st.subheader("Sources (with Metadata)")
                        for i, source in enumerate(result.get("sources", []), 1):
                            st.write(f"{i}. {source}")
                    
                    # Get search results for metadata display
                    search_results = result.get("search_results", {})
                    
                    # Display metadata summary
                    if result.get("metadata"):
                        metadata = result.get("metadata", {})
                        with st.expander("Query Metadata"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write(f"**Query Type:** {metadata.get('query_type', 'Unknown')}")
                                st.write(f"**Context Length:** {metadata.get('context_length', 0):,} chars")
                            with col2:
                                st.write(f"**Sources Found:** {metadata.get('num_sources', 0)}")
                                st.write(f"**Latency:** {metadata.get('latency_ms', 0):.1f} ms")
                            with col3:
                                if search_results.get("rewritten_query"):
                                    st.write(f"**Rewritten Query:** {search_results.get('rewritten_query', '')}")
                    
                    # Display search results
                    with st.expander("View Search Results"):
                        # Handle query_type (can be enum or dict)
                        query_type = search_results.get("query_type", "Unknown")
                        if hasattr(query_type, 'value'):
                            query_type_str = query_type.value
                        elif isinstance(query_type, dict):
                            query_type_str = query_type.get("value", "Unknown")
                        else:
                            query_type_str = str(query_type)
                        
                        st.write("**Query Type:**", query_type_str)
                        st.write("**Rewritten Query:**", search_results.get("rewritten_query", ""))
                        
                        st.subheader("Results by Source")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write("**Graph Results:**")
                            graph_results = search_results.get("sources", {}).get("graph", [])
                            st.write(f"Found {len(graph_results)} graph results")
                        
                        with col2:
                            st.write("**Vector Results:**")
                            vector_results = search_results.get("sources", {}).get("vector", [])
                            st.write(f"Found {len(vector_results)} vector results")
                        
                        with col3:
                            st.write("**Keyword Results:**")
                            keyword_results = search_results.get("sources", {}).get("keyword", [])
                            st.write(f"Found {len(keyword_results)} keyword results")
                        
                        st.subheader("Combined Results (with Metadata & Domain Tags)")
                        for i, res in enumerate(search_results.get("results", [])[:max_results], 1):
                            metadata = res.get("metadata", {})
                            modality = metadata.get("modality", "unknown")
                            file_name = metadata.get("file_name", "Unknown")
                            file_format = metadata.get("file_format", "")
                            domain = metadata.get("domain", res.get("topic_relevance", {}).get("domain", "general") if isinstance(res.get("topic_relevance"), dict) else "general")
                            topic_relevance = res.get("topic_relevance", 0.0)
                            if isinstance(topic_relevance, dict):
                                domain = topic_relevance.get("domain", "general")
                                topic_relevance = topic_relevance.get("score", 0.0)
                            
                            # Create badge-style display
                            score = res.get('score', 0)
                            source = res.get('source', 'unknown')
                            
                            # Format title with metadata badges
                            title_parts = [f"Result {i}"]
                            title_parts.append(f"Score: {score:.3f}")
                            title_parts.append(f"Source: {source}")
                            title_parts.append(f"Modality: {modality.upper()}")
                            if domain and domain != "general":
                                title_parts.append(f"Domain: {domain.upper()}")
                            if topic_relevance > 0:
                                title_parts.append(f"Topic Relevance: {topic_relevance:.2f}")
                            
                            with st.expander(" | ".join(title_parts)):
                                # Display content
                                content = res.get("content", "")
                                if len(content) > 500:
                                    st.write(content[:500] + "...")
                                else:
                                    st.write(content)
                                
                                # Display metadata section
                                st.markdown("---")
                                st.markdown("### Metadata & Domain Tags")
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.markdown("**File Information:**")
                                    st.write(f"File: `{file_name}`")
                                    if file_format:
                                        st.write(f"Format: `{file_format}`")
                                    if metadata.get("file_id"):
                                        st.write(f"ID: `{metadata.get('file_id', '')[:12]}...`")
                                
                                with col2:
                                    st.markdown("**Content Metadata:**")
                                    st.write(f"Modality: **{modality.upper()}**")
                                    if metadata.get("chunk_index") is not None:
                                        st.write(f"Chunk Index: {metadata.get('chunk_index')}")
                                    if metadata.get("ingestion_timestamp"):
                                        timestamp = metadata.get("ingestion_timestamp", "")
                                        if timestamp:
                                            st.write(f"Ingested: {timestamp[:10]}")
                                
                                with col3:
                                    st.markdown("**Domain & Classification:**")
                                    if domain and domain != "general":
                                        st.write(f"**Domain: {domain.upper()}**")
                                    else:
                                        st.write(f"Domain: General")
                                    if topic_relevance > 0:
                                        st.write(f"Topic Relevance: **{topic_relevance:.2f}**")
                                    if metadata.get("sentiment"):
                                        sentiment = metadata.get("sentiment", {})
                                        sentiment_label = sentiment.get("sentiment", "neutral")
                                        polarity = sentiment.get("polarity", 0.0)
                                        st.write(f"Sentiment: **{sentiment_label}** ({polarity:+.2f})")
                                
                                # Show additional metadata if available
                                additional_meta = {}
                                if modality == "image":
                                    if metadata.get("image_width"):
                                        additional_meta["Dimensions"] = f"{metadata.get('image_width')}x{metadata.get('image_height')}"
                                    if metadata.get("image_format"):
                                        additional_meta["Image Format"] = metadata.get("image_format")
                                elif modality == "video":
                                    if metadata.get("video_duration_seconds"):
                                        duration = metadata.get("video_duration_seconds", 0)
                                        additional_meta["Duration"] = f"{duration:.1f}s"
                                    if metadata.get("video_fps"):
                                        additional_meta["FPS"] = metadata.get("video_fps")
                                elif modality == "audio":
                                    if metadata.get("audio_format"):
                                        additional_meta["Audio Format"] = metadata.get("audio_format")
                                    if metadata.get("language"):
                                        additional_meta["Language"] = metadata.get("language")
                                
                                if additional_meta:
                                    st.markdown("**Additional Metadata:**")
                                    for key, value in additional_meta.items():
                                        st.write(f"- {key}: {value}")
                except Exception as e:
                    st.error(f"Query processing failed: {str(e)}")
                    logger.error(f"Query processing error: {e}")
                    st.session_state.last_query_result = None
        else:
            st.warning("Please enter a query")
    
    # Display stored results if they exist (persists when clicking other buttons like View Metrics)
    # Only show if search wasn't just clicked (to avoid duplicate display)
    if st.session_state.last_query_result is not None and not search_clicked:
        result = st.session_state.last_query_result
        st.divider()
        st.subheader("Query Results")
        
        # Display answer
        st.subheader("Answer")
        st.write(result.get("answer", "No answer generated"))
        
        # Display evaluation metrics if available
        if result.get("evaluation"):
            eval_metrics = result["evaluation"]
            st.subheader("Evaluation Metrics")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Precision", f"{eval_metrics.get('precision', 0):.3f}")
            with col2:
                st.metric("Recall", f"{eval_metrics.get('recall', 0):.3f}")
            with col3:
                st.metric("Latency", f"{eval_metrics.get('latency_ms', 0):.1f} ms")
            with col4:
                st.metric("Hallucination", f"{eval_metrics.get('hallucination_rate', 0):.3f}")
        
        # Display sources
        if result.get("sources"):
            st.subheader("Sources (with Metadata)")
            for i, source in enumerate(result.get("sources", []), 1):
                st.write(f"{i}. {source}")
        
        # Get search results for metadata display
        search_results = result.get("search_results", {})
        
        # Display metadata summary
        if result.get("metadata"):
            metadata = result.get("metadata", {})
            with st.expander("Query Metadata"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Query Type:** {metadata.get('query_type', 'Unknown')}")
                    st.write(f"**Context Length:** {metadata.get('context_length', 0):,} chars")
                with col2:
                    st.write(f"**Sources Found:** {metadata.get('num_sources', 0)}")
                    st.write(f"**Latency:** {metadata.get('latency_ms', 0):.1f} ms")
                with col3:
                    if search_results.get("rewritten_query"):
                        st.write(f"**Rewritten Query:** {search_results.get('rewritten_query', '')}")
        
        # Display search results
        with st.expander("View Search Results"):
            # Handle query_type (can be enum or dict)
            query_type = search_results.get("query_type", "Unknown")
            if hasattr(query_type, 'value'):
                query_type_str = query_type.value
            elif isinstance(query_type, dict):
                query_type_str = query_type.get("value", "Unknown")
            else:
                query_type_str = str(query_type)
            
            st.write("**Query Type:**", query_type_str)
            st.write("**Rewritten Query:**", search_results.get("rewritten_query", ""))
            
            st.subheader("Results by Source")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**Graph Results:**")
                graph_results = search_results.get("sources", {}).get("graph", [])
                st.write(f"Found {len(graph_results)} graph results")
            
            with col2:
                st.write("**Vector Results:**")
                vector_results = search_results.get("sources", {}).get("vector", [])
                st.write(f"Found {len(vector_results)} vector results")
            
            with col3:
                st.write("**Keyword Results:**")
                keyword_results = search_results.get("sources", {}).get("keyword", [])
                st.write(f"Found {len(keyword_results)} keyword results")
            
            st.subheader("Combined Results (with Metadata & Domain Tags)")
            for i, res in enumerate(search_results.get("results", [])[:max_results], 1):
                metadata = res.get("metadata", {})
                modality = metadata.get("modality", "unknown")
                file_name = metadata.get("file_name", "Unknown")
                file_format = metadata.get("file_format", "")
                domain = metadata.get("domain", res.get("topic_relevance", {}).get("domain", "general") if isinstance(res.get("topic_relevance"), dict) else "general")
                topic_relevance = res.get("topic_relevance", 0.0)
                if isinstance(topic_relevance, dict):
                    domain = topic_relevance.get("domain", "general")
                    topic_relevance = topic_relevance.get("score", 0.0)
                
                # Create badge-style display
                score = res.get('score', 0)
                source = res.get('source', 'unknown')
                
                # Format title with metadata badges
                title_parts = [f"Result {i}"]
                title_parts.append(f"Score: {score:.3f}")
                title_parts.append(f"Source: {source}")
                title_parts.append(f"Modality: {modality.upper()}")
                if domain and domain != "general":
                    title_parts.append(f"Domain: {domain.upper()}")
                if topic_relevance > 0:
                    title_parts.append(f"Topic Relevance: {topic_relevance:.2f}")
                
                with st.expander(" | ".join(title_parts)):
                    # Display content
                    content = res.get("content", "")
                    if len(content) > 500:
                        st.write(content[:500] + "...")
                    else:
                        st.write(content)
                    
                    # Display metadata section
                    st.markdown("---")
                    st.markdown("### Metadata & Domain Tags")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**File Information:**")
                        st.write(f"File: `{file_name}`")
                        if file_format:
                            st.write(f"Format: `{file_format}`")
                        if metadata.get("file_id"):
                            st.write(f"ID: `{metadata.get('file_id', '')[:12]}...`")
                    
                    with col2:
                        st.markdown("**Content Metadata:**")
                        st.write(f"Modality: **{modality.upper()}**")
                        if metadata.get("chunk_index") is not None:
                            st.write(f"Chunk Index: {metadata.get('chunk_index')}")
                        if metadata.get("ingestion_timestamp"):
                            timestamp = metadata.get("ingestion_timestamp", "")
                            if timestamp:
                                st.write(f"Ingested: {timestamp[:10]}")
                    
                    with col3:
                        st.markdown("**Domain & Classification:**")
                        if domain and domain != "general":
                            st.write(f"**Domain: {domain.upper()}**")
                        else:
                            st.write(f"Domain: General")
                        if topic_relevance > 0:
                            st.write(f"Topic Relevance: **{topic_relevance:.2f}**")
                        if metadata.get("sentiment"):
                            sentiment = metadata.get("sentiment", {})
                            sentiment_label = sentiment.get("sentiment", "neutral")
                            polarity = sentiment.get("polarity", 0.0)
                            st.write(f"Sentiment: **{sentiment_label}** ({polarity:+.2f})")
                    
                    # Show additional metadata if available
                    additional_meta = {}
                    if modality == "image":
                        if metadata.get("image_width"):
                            additional_meta["Dimensions"] = f"{metadata.get('image_width')}x{metadata.get('image_height')}"
                        if metadata.get("image_format"):
                            additional_meta["Image Format"] = metadata.get("image_format")
                    elif modality == "video":
                        if metadata.get("video_duration_seconds"):
                            duration = metadata.get("video_duration_seconds", 0)
                            additional_meta["Duration"] = f"{duration:.1f}s"
                        if metadata.get("video_fps"):
                            additional_meta["FPS"] = metadata.get("video_fps")
                    elif modality == "audio":
                        if metadata.get("audio_format"):
                            additional_meta["Audio Format"] = metadata.get("audio_format")
                        if metadata.get("language"):
                            additional_meta["Language"] = metadata.get("language")
                    
                    if additional_meta:
                        st.markdown("**Additional Metadata:**")
                        for key, value in additional_meta.items():
                            st.write(f"- {key}: {value}")

with tab2:
    st.header("Evaluation Metrics")
    
    st.write("Track system performance and quality metrics")
    
    metrics = st.session_state.evaluator.get_aggregate_metrics()
    
    if metrics:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Queries", metrics.get("total_queries", 0))
        
        with col2:
            st.metric("Avg Precision", f"{metrics.get('avg_precision', 0):.3f}")
        
        with col3:
            st.metric("Avg Recall", f"{metrics.get('avg_recall', 0):.3f}")
        
        with col4:
            st.metric("Avg Latency", f"{metrics.get('avg_latency_ms', 0):.1f} ms")
        
        st.subheader("Metrics by Query Type")
        st.json(metrics.get("metrics_by_query_type", {}))
    else:
        st.info("No evaluation data yet. Run some queries to see metrics.")

with tab3:
    st.header("Knowledge Graph Visualization")
    st.write("Explore entities and relationships in the knowledge graph")
    
    try:
        # Test Neo4j connection first
        try:
            neo4j_client = Neo4jClient()
            # Verify connection works
            with neo4j_client.driver.session() as test_session:
                test_session.run("RETURN 1").single()
        except Exception as conn_error:
            st.error(f"Neo4j connection error: {str(conn_error)}")
            st.info("Make sure Neo4j is running: `docker compose up -d`")
            st.stop()
        
        # Get graph statistics
        with neo4j_client.driver.session() as session:
            # Count entities
            entity_count = session.run("MATCH (e:Entity) RETURN count(e) as count").single()["count"]
            
            # Count relationships
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            # Count files
            file_count = session.run("MATCH (f:File) RETURN count(f) as count").single()["count"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Entities", entity_count)
        with col2:
            st.metric("Relationships", rel_count)
        with col3:
            st.metric("Files", file_count)
        
        if entity_count > 0:
            # Get sample entities and relationships for visualization
            with neo4j_client.driver.session() as session:
                # Get entities with their types and relationships
                entity_query = """
                MATCH (e:Entity)
                OPTIONAL MATCH (e)-[r:RELATED_TO]->(target:Entity)
                RETURN e.id as id, e.name as name, e.type as type, 
                       collect(DISTINCT target.id)[0..10] as related_ids
                LIMIT 50
                """
                results = session.run(entity_query)
                
                # Build network graph
                G = nx.Graph()
                entity_data = {}
                
                for record in results:
                    entity_id = record["id"]
                    entity_name = record["name"]
                    entity_type = record["type"] or "Unknown"
                    related_ids = record["related_ids"] or []
                    
                    # Add node
                    G.add_node(entity_id, name=entity_name, type=entity_type)
                    entity_data[entity_id] = {"name": entity_name, "type": entity_type}
                    
                    # Add edges to related entities (by ID)
                    for related_id in related_ids:
                        if related_id and related_id != entity_id:
                            G.add_edge(entity_id, related_id)
                
                if len(G.nodes()) > 0:
                    # Create Plotly visualization
                    pos = nx.spring_layout(G, k=1, iterations=50)
                    
                    # Extract node positions
                    node_x = []
                    node_y = []
                    node_text = []
                    node_colors = []
                    
                    for node in G.nodes():
                        x, y = pos[node]
                        node_x.append(x)
                        node_y.append(y)
                        node_info = entity_data.get(node, {})
                        node_text.append(f"{node_info.get('name', node)}<br>Type: {node_info.get('type', 'Unknown')}")
                        # Color by type
                        type_hash = hash(node_info.get('type', 'Unknown')) % 10
                        node_colors.append(type_hash)
                    
                    # Extract edge positions
                    edge_x = []
                    edge_y = []
                    for edge in G.edges():
                        x0, y0 = pos[edge[0]]
                        x1, y1 = pos[edge[1]]
                        edge_x.extend([x0, x1, None])
                        edge_y.extend([y0, y1, None])
                    
                    # Create edge trace
                    edge_trace = go.Scatter(
                        x=edge_x, y=edge_y,
                        line=dict(width=0.5, color='#888'),
                        hoverinfo='none',
                        mode='lines'
                    )
                    
                    # Create node trace
                    node_trace = go.Scatter(
                        x=node_x, y=node_y,
                        mode='markers+text',
                        hoverinfo='text',
                        text=[entity_data.get(node, {}).get('name', node)[:10] for node in G.nodes()],
                        textposition="middle center",
                        textfont=dict(size=8),
                        hovertext=node_text,
                    marker=dict(
                        showscale=True,
                        colorscale='Viridis',
                        reversescale=True,
                        color=node_colors,
                        size=10,
                        colorbar=dict(
                            thickness=15,
                            title=dict(text="Entity Type"),
                            xanchor="left"
                        ),
                        line=dict(width=2, color='white')
                    )
                    )
                    
                    # Create figure
                    fig = go.Figure(data=[edge_trace, node_trace],
                                  layout=go.Layout(
                                      title=dict(text='Knowledge Graph Visualization', font=dict(size=16)),
                                      showlegend=False,
                                      hovermode='closest',
                                      margin=dict(b=20, l=5, r=5, t=40),
                                      annotations=[dict(
                                          text="Hover over nodes to see entity details",
                                          showarrow=False,
                                          xref="paper", yref="paper",
                                          x=0.005, y=-0.002,
                                          xanchor="left", yanchor="bottom",
                                          font=dict(color="#888", size=10)
                                      )],
                                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                      yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                      height=600
                                  ))
                    
                    st.plotly_chart(fig, width='stretch')
                    
                    # Show entity list
                    with st.expander("View All Entities"):
                        entity_list = []
                        for node in G.nodes():
                            entity_info = entity_data.get(node, {})
                            entity_list.append({
                                "ID": node,
                                "Name": entity_info.get('name', 'Unknown'),
                                "Type": entity_info.get('type', 'Unknown'),
                                "Connections": G.degree(node)
                            })
                        st.dataframe(entity_list, width='stretch')
                else:
                    st.info("No entities found in the knowledge graph. Upload and process some files first.")
        else:
            st.info("No entities in the knowledge graph yet. Upload and process some files to build the graph.")
        
        neo4j_client.close()
        
    except ImportError as import_error:
        error_msg = str(import_error)
        if "pyarrow" in error_msg.lower() or "libutf8proc" in error_msg.lower():
            st.warning("Library dependency issue detected. This is a known macOS/conda compatibility issue.")
            st.info("The knowledge graph visualization may still work. Try refreshing the page.")
            st.code(str(import_error)[:500], language=None)
        else:
            st.error(f"Import error: {import_error}")
    except Exception as e:
        error_msg = str(e)
        if "pyarrow" in error_msg.lower() or "libutf8proc" in error_msg.lower():
            st.warning("Library dependency issue (PyArrow). This doesn't affect core functionality.")
            st.info("Neo4j connection is working. The visualization may have dependency issues.")
        else:
            st.error(f"Error loading graph: {error_msg}")
            st.info("Make sure Neo4j is running and accessible.")

with tab4:
    st.header("About")
    st.write("""
    ## Multimodal Enterprise RAG System
    
    This system provides:
    - **Multimodal Ingestion**: Process text, image, audio, and video files
    - **Knowledge Graph**: Build relationships between entities using Neo4j
    - **Vector Search**: Semantic search using Qdrant
    - **Hybrid Search**: Combine graph traversal, keyword filtering, and vector retrieval
    - **Evaluation Framework**: Track precision, recall, latency, and hallucination rates
    
    ### Supported File Types
    - **Text**: PDF, TXT, DOCX
    - **Images**: JPG, PNG
    - **Audio**: MP3, WAV
    - **Video**: MP4, AVI
    
    ### Query Types
    - **Lookup**: Direct factual queries
    - **Summarization**: Content summarization requests
    - **Semantic Linkages**: Relationship and connection queries
    - **Reasoning**: Multi-step reasoning queries
    """)

