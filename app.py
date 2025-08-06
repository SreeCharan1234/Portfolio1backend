import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
portfolio_data = None
gemini_model = None

# Configure Google AI
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    try:
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Google AI configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure Google AI: {e}")
        gemini_model = None
else:
    logger.warning("Google API key not found")

app = FastAPI(
    title="K Sree Charan Portfolio Chatbot API",
    description="RAG-powered chatbot for portfolio information with image extraction",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    images: List[str] = []
    relevant_sections: List[str] = []

def get_image_paths(section: str, subfolder: str) -> List[str]:
    """Get all image paths for a given section and subfolder"""
    base_path = Path(".")
    section_path = base_path / section / subfolder
    
    if not section_path.exists():
        logger.warning(f"Path does not exist: {section_path}")
        return []
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    images = []
    
    try:
        for file_path in section_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                # Return relative path for static serving
                relative_path = f"/{section}/{subfolder}/{file_path.name}"
                images.append(relative_path)
    except Exception as e:
        logger.error(f"Error reading directory {section_path}: {e}")
    
    return sorted(images)

def load_portfolio_data():
    """Load and process portfolio data"""
    global portfolio_data
    
    json_path = Path("./k_sree_charan_complete_portfolio.json")
    if not json_path.exists():
        raise FileNotFoundError(f"Portfolio data file not found: {json_path}")
    
    with open(json_path, "r", encoding="utf-8") as f:
        portfolio_data = json.load(f)
    
    logger.info("Portfolio data loaded successfully")
    return portfolio_data

def search_portfolio_data(query: str, data: Dict[str, Any]) -> tuple[str, List[str], List[str]]:
    """Search portfolio data and return relevant context, images, and sections"""
    query_lower = query.lower()
    context_parts = []
    images = []
    relevant_sections = []
    
    # Search in different sections
    
    # Basic info
    if any(word in query_lower for word in ['name', 'summary', 'title', 'quote']):
        context_parts.append(f"Name: {data.get('name', '')}")
        context_parts.append(f"Title: {data.get('title', '')}")
        context_parts.append(f"Summary: {data.get('summary', '')}")
        relevant_sections.append('basic_info')
    
    # Contact
    if any(word in query_lower for word in ['contact', 'email', 'phone', 'linkedin', 'github']):
        contact = data.get('contact', {})
        context_parts.append(f"Contact - Email: {contact.get('email', '')}, Mobile: {contact.get('mobile', '')}")
        context_parts.append(f"LinkedIn: {contact.get('linkedin', '')}, GitHub: {contact.get('github', '')}")
        relevant_sections.append('contact')
    
    # Skills
    if any(word in query_lower for word in ['skill', 'technology', 'programming', 'frontend', 'backend']):
        skills = data.get('skills', {})
        frontend_skills = ', '.join([f"{k} ({v})" for k, v in skills.get('frontend', {}).items()])
        backend_skills = ', '.join([f"{k} ({v})" for k, v in skills.get('backend', {}).items()])
        context_parts.append(f"Frontend Skills: {frontend_skills}")
        context_parts.append(f"Backend Skills: {backend_skills}")
        context_parts.append(f"Databases: {', '.join(skills.get('databases', []))}")
        relevant_sections.append('skills')
    
    # Experience
    if any(word in query_lower for word in ['experience', 'work', 'job', 'company', 'maq']):
        for exp in data.get('experience', []):
            context_parts.append(f"Experience: {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('dates', '')})")
            context_parts.append(f"Achievements: {', '.join(exp.get('achievements', []))}")
        relevant_sections.append('experience')
    
    # Education
    if any(word in query_lower for word in ['education', 'degree', 'university', 'college']):
        for edu in data.get('education', []):
            context_parts.append(f"Education: {edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('institution', '')}")
        relevant_sections.append('education')
    
    # Hackathons
    hackathon_keywords = ['hackathon', 'devfest', 'arena', 'microsoft', 'code', 'contest', 'competition']
    if any(word in query_lower for word in hackathon_keywords):
        folder_mappings = {
            'devfest': 'devfest',
            'arena': 'arena', 
            'code-of-duty': 'code-of-duty',
            'code-a-haunt': 'code-a-haunt',
            'microsoft': 'microsoft',
            'kriyeta': 'kriyeta3.0',
            'build-a-thon': 'build-a-thon',
            'codingblocks': 'codingblockslpu',
            'coding blocks': 'codingblockslpu'
        }
        
        for hackathon in data.get('hackathons', []):
            title = hackathon.get('title', '')
            context_parts.append(f"Hackathon: {title}")
            context_parts.append(f"Position: {hackathon.get('position', '')}, Prize: {hackathon.get('prize_money', '')}")
            context_parts.append(f"Description: {hackathon.get('description', '')}")
            
            # Check for images
            title_lower = title.lower()
            for keyword, folder in folder_mappings.items():
                if keyword in query_lower or keyword in title_lower:
                    folder_images = get_image_paths('photo', folder)
                    images.extend(folder_images)
                    break
        
        relevant_sections.append('hackathons')
    
    # Projects
    project_keywords = ['project', 'study-buddy', 'health-buddy', 'agrivision', 'agriculture', 'sarthi']
    if any(word in query_lower for word in project_keywords):
        folder_mappings = {
            'study-buddy': 'study-buddy',
            'health-buddy': 'health-buddy', 
            'agrivision': 'agrivision',
            'agriculture': 'agrivision',
            'sarthi': 'sarthi',
            'surasksha': 'surasksha-suchak'
        }
        
        for project in data.get('projects', []):
            title = project.get('title', '')
            context_parts.append(f"Project: {title}")
            context_parts.append(f"Category: {project.get('category', '')}, Description: {project.get('description', '')}")
            
            # Check for images
            title_lower = title.lower()
            for keyword, folder in folder_mappings.items():
                if keyword in query_lower or keyword in title_lower:
                    folder_images = get_image_paths('projectfolder', folder)
                    images.extend(folder_images)
                    break
        
        relevant_sections.append('projects')
    
    # Remove duplicates from images
    unique_images = list(dict.fromkeys(images))
    
    return "\n".join(context_parts), unique_images[:10], list(set(relevant_sections))

def generate_response_with_gemini(context: str, question: str) -> str:
    """Generate response using Google Gemini API"""
    try:
        global gemini_model
        
        if not gemini_model:
            return "I apologize, but the Google AI service is not available. Please contact the administrator."
        
        prompt = f"""
        You are an AI assistant representing K Sree Charan's portfolio. Use the following context to answer the user's question comprehensively and accurately.
        
        Context:
        {context}
        
        Question: {question}
        
        Guidelines:
        1. Provide detailed, accurate information based on the context
        2. If asked about hackathons, projects, or specific achievements, mention relevant details
        3. Be conversational and professional
        4. If images are available for the topic, mention that visual content is provided
        5. If the question is outside the context, politely redirect to portfolio-related topics
        
        Answer:
        """
        
        response = gemini_model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Error generating response with Gemini: {e}")
        return f"I apologize, but I encountered an error while processing your request. Please try again. Error: {str(e)}"

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    try:
        logger.info("Starting application initialization...")
        global portfolio_data
        portfolio_data = load_portfolio_data()
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        # Set a fallback minimal data structure
        portfolio_data = {
            "name": "K Sree Charan",
            "title": "Full Stack Developer", 
            "hackathons": [],
            "projects": []
        }

# Mount static files
try:
    app.mount("/photo", StaticFiles(directory="./photo"), name="photo")
    app.mount("/projectfolder", StaticFiles(directory="./projectfolder"), name="projectfolder") 
    app.mount("/static", StaticFiles(directory="./static"), name="static")
except RuntimeError as e:
    logger.warning(f"Could not mount static directories: {e}")
    # Create dummy mounts to prevent startup errors
    import tempfile
    temp_dir = tempfile.mkdtemp()
    app.mount("/photo", StaticFiles(directory=temp_dir), name="photo")
    app.mount("/projectfolder", StaticFiles(directory=temp_dir), name="projectfolder")
    app.mount("/static", StaticFiles(directory=temp_dir), name="static")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint for RAG-based responses"""
    try:
        if not portfolio_data:
            raise HTTPException(status_code=500, detail="Portfolio data not loaded. Please check the server configuration.")
        
        query = request.question.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Search portfolio data
        context, images, relevant_sections = search_portfolio_data(query, portfolio_data)
        
        if not context:
            context = "I can help you with information about K Sree Charan's skills, experience, education, hackathons, and projects."
        
        # Generate response using Gemini
        answer = generate_response_with_gemini(context, query)
        
        return ChatResponse(
            answer=answer,
            images=images,
            relevant_sections=relevant_sections
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return ChatResponse(
            answer=f"I apologize, but I encountered an error while processing your request: {str(e)}",
            images=[],
            relevant_sections=[]
        )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "K Sree Charan Portfolio Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat - POST endpoint for chatbot interaction",
            "docs": "/docs - API documentation", 
            "health": "/health - Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    api_key = os.getenv("GOOGLE_API_KEY")
    return {
        "status": "healthy",
        "portfolio_data_loaded": portfolio_data is not None,
        "google_api_key_set": bool(api_key),
        "gemini_model_ready": gemini_model is not None,
        "api_key_length": len(api_key) if api_key else 0,
        "api_key_preview": api_key[:10] + "..." if api_key and len(api_key) > 10 else api_key
    }

@app.get("/debug-env")
async def debug_env():
    """Debug endpoint to check environment variables"""
    import os
    return {
        "all_env_vars": list(os.environ.keys()),
        "google_api_key_exists": "GOOGLE_API_KEY" in os.environ,
        "google_api_key_value": os.getenv("GOOGLE_API_KEY", "NOT_FOUND"),
        "current_directory": os.getcwd(),
        "env_file_exists": Path(".env").exists()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 