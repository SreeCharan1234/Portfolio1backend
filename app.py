import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flasgger import Swagger, swag_from
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


app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Configure CORS
CORS(app, origins=["*"], allow_headers=["*"], methods=["*"])

# Configure Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Portfolio Chatbot API",
        "description": "RAG-powered chatbot API for portfolio information",
        "version": "1.0.0"
    },
    "host": "localhost:8003",
    "basePath": "/",
    "schemes": ["http", "https"],
    "consumes": ["application/json"],
    "produces": ["application/json"]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

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
    """Load and process portfolio data with fallback options"""
    global portfolio_data
    
    # Try multiple JSON file locations
    json_files = ["./sreedata.json"]
    
    for json_path_str in json_files:
        json_path = Path(json_path_str)
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    portfolio_data = json.load(f)
                logger.info(f"Portfolio data loaded successfully from {json_path}")
                return portfolio_data
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format in {json_path}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error reading {json_path}: {e}")
                continue
    
    # If no file found, raise error with helpful message
    raise FileNotFoundError(f"Portfolio data file not found. Tried: {', '.join(json_files)}")

def search_portfolio_data(query: str, data: Dict[str, Any]) -> tuple[str, List[str], List[str]]:
    """Search portfolio data and return relevant context, images, and sections"""
    query_lower = query.lower()
    context_parts = []
    images = []
    relevant_sections = []
    
    # Basic info - Enhanced for your JSON structure
    if any(word in query_lower for word in ['name', 'summary', 'title', 'quote', 'about', 'intro']):
        context_parts.append(f"Name: {data.get('name', '')}")
        context_parts.append(f"Title: {data.get('title', '')}")
        
        # Add experience summary
        exp_summary = data.get('experienceSummary', {})
        if exp_summary:
            context_parts.append(f"Experience Summary: {exp_summary.get('yearsExperience', '')} years experience")
            context_parts.append(f"Projects Completed: {exp_summary.get('projectsCompleted', '')}")
            context_parts.append(f"Technologies Known: {exp_summary.get('technologiesKnown', '')}")
            context_parts.append(f"Hackathons Participated: {exp_summary.get('hackathonsParticipated', '')}")
        
        relevant_sections.append('basic_info')
    
    # Contact - Updated for your structure
    if any(word in query_lower for word in ['contact', 'email', 'phone', 'location', 'reach']):
        contact = data.get('contact', {})
        context_parts.append(f"Email: {contact.get('email', '')}")
        context_parts.append(f"Phone: {contact.get('phone', '')}")
        context_parts.append(f"Location: {contact.get('location', '')}")
        relevant_sections.append('contact')
    
    # Skills - Enhanced for your detailed skill structure
    if any(word in query_lower for word in ['skill', 'technology', 'programming', 'frontend', 'backend', 'database', 'tools', 'mobile']):
        skills = data.get('skills', {})
        technologies = data.get('technologies', [])
        
        # Add main technologies
        if technologies:
            context_parts.append(f"Main Technologies: {', '.join(technologies)}")
        
        # Add detailed skills with proficiency
        for skill_category, skill_dict in skills.items():
            if isinstance(skill_dict, dict):
                skill_list = [f"{skill} ({proficiency})" for skill, proficiency in skill_dict.items()]
                category_name = skill_category.replace('_', ' ').title()
                context_parts.append(f"{category_name}: {', '.join(skill_list)}")
        
        # Add proficiency legend
        legend = data.get('proficiencyLegend', {})
        if legend:
            legend_text = ', '.join([f"{level}: {range_val}" for level, range_val in legend.items()])
            context_parts.append(f"Proficiency Legend: {legend_text}")
        
        relevant_sections.append('skills')
    
    # Work Experience - Updated for your structure
    if any(word in query_lower for word in ['experience', 'work', 'job', 'company', 'maq', 'career', 'role']):
        work_exp = data.get('workExperience', [])
        for exp in work_exp:
            context_parts.append(f"Role: {exp.get('role', '')} ({exp.get('type', '')}) at {exp.get('company', '')}")
            context_parts.append(f"Duration: {exp.get('years', '')}, Location: {exp.get('location', '')}")
            
            achievements = exp.get('achievements', [])
            if achievements:
                context_parts.append(f"Achievements: {', '.join(achievements)}")
            
            technologies = exp.get('technologies', [])
            if technologies:
                context_parts.append(f"Technologies Used: {', '.join(technologies)}")
        
        relevant_sections.append('experience')
    
    # Education - Updated for your structure
    if any(word in query_lower for word in ['education', 'degree', 'university', 'college', 'qualification']):
        education = data.get('education', [])
        for edu in education:
            degree = edu.get('degree') or edu.get('qualification', '')
            field = edu.get('field', '')
            institution = edu.get('institution', '')
            years = edu.get('years', '')
            grade = edu.get('grade', '')
            
            context_parts.append(f"Education: {degree} in {field} from {institution} ({years})")
            if grade:
                context_parts.append(f"Grade: {grade}")
            
            achievements = edu.get('achievements', [])
            if achievements:
                context_parts.append(f"Achievements: {', '.join(achievements)}")
        
        relevant_sections.append('education')
    
    # Certifications
    if any(word in query_lower for word in ['certification', 'certificate', 'aws', 'react', 'python', 'course']):
        certifications = data.get('certifications', [])
        for cert in certifications:
            context_parts.append(f"Certification: {cert.get('name', '')} by {cert.get('issuer', '')} ({cert.get('year', '')})")
        
        relevant_sections.append('certifications')
    
    # Projects - Enhanced for your detailed project structure
    project_keywords = ['project', 'agrivision', 'health-buddy', 'study-buddy', 'sarthi', 'suraksha', 'code-off-duty']
    if any(word in query_lower for word in project_keywords):
        projects = data.get('projects', [])
        
        project_folder_mappings = {
            'agrivision': 'agrivision',
            'health-buddy': 'health-buddy',
            'health buddy': 'health-buddy',
            'study-buddy': 'study-buddy',
            'study buddy': 'study-buddy',
            'sarthi': 'sarthi',
            'suraksha': 'surasksha-suchak',
            'code-off-duty': 'code-off-duty',
            'code off duty': 'code-off-duty'
        }
        
        for project in projects:
            name = project.get('name', '')
            category = project.get('category', '')
            description = project.get('description', '')
            duration = project.get('duration', '')
            team_size = project.get('teamSize', '')
            
            context_parts.append(f"Project: {name} ({category})")
            context_parts.append(f"Description: {description}")
            context_parts.append(f"Duration: {duration}, Team Size: {team_size}")
            
            # Add technologies and features
            technologies = project.get('technologies', [])
            if technologies:
                context_parts.append(f"Technologies: {', '.join(technologies)}")
            
            features = project.get('features', [])
            if features:
                context_parts.append(f"Features: {', '.join(features)}")
            
            # Add GitHub and deployment links
            github_link = project.get('githubLink', '')
            deployment_link = project.get('deploymentLink', '')
            if github_link:
                context_parts.append(f"GitHub: {github_link}")
            if deployment_link:
                context_parts.append(f"Live Demo: {deployment_link}")
            
            # Check for project images
            name_lower = name.lower().replace(' ', '-')
            for keyword, folder in project_folder_mappings.items():
                if keyword in query_lower or keyword in name_lower:
                    project_images = get_image_paths('projects', folder)
                    images.extend(project_images)
                    break
        
        relevant_sections.append('projects')
    
    # Hackathons - Enhanced for your detailed hackathon structure
    hackathon_keywords = ['hackathon', 'devfest', 'arena', 'microsoft', 'code', 'contest', 'competition', 'kriyeta', 'build-a-thon']
    if any(word in query_lower for word in hackathon_keywords):
        hackathons_data = data.get('hackathons', {})
        
        # Add summary information
        if isinstance(hackathons_data, dict):
            context_parts.append(f"Total Hackathons Participated: {hackathons_data.get('totalParticipated', '')}")
            context_parts.append(f"Wins/Top Places: {hackathons_data.get('winsOrTopPlaces', '')}")
            context_parts.append(f"Team Members Worked With: {hackathons_data.get('teamMembers', '')}")
            
            hackathon_events = hackathons_data.get('events', [])
        else:
            hackathon_events = hackathons_data if isinstance(hackathons_data, list) else []
        
        hackathon_folder_mappings = {
            'devfest': 'devfest',
            'microsoft': 'microsoft',
            'kriyeta': 'kriyeta3.0',
            'build-a-thon': 'build-a-thon',
            'build a thon': 'build-a-thon',
            'code-a-haunt': 'code-a-haunt',
            'code a haunt': 'code-a-haunt',
            'arena': 'arena',
            'code-of-duty': 'code-of-duty',
            'code of duty': 'code-of-duty',
            'coding blocks': 'codingblockslpu',
            'codingblocks': 'codingblockslpu'
        }
        
        for hackathon in hackathon_events:
            event = hackathon.get('event', '')
            result = hackathon.get('result', '')
            month_year = hackathon.get('monthYear', '')
            host = hackathon.get('host', '')
            team_size = hackathon.get('teamSize', '')
            
            context_parts.append(f"Hackathon: {event}")
            context_parts.append(f"Result: {result} ({month_year})")
            context_parts.append(f"Host: {host}, Team Size: {team_size}")
            
            # Add technologies and awards
            technologies = hackathon.get('technologies', [])
            if technologies:
                context_parts.append(f"Technologies: {', '.join(technologies)}")
            
            awards = hackathon.get('awards', [])
            if awards:
                context_parts.append(f"Awards: {', '.join(awards)}")
            
            # Add team members
            members = hackathon.get('members', [])
            if members:
                context_parts.append(f"Team Members: {', '.join(members)}")
            
            # Check for hackathon images
            event_lower = event.lower().replace(' ', '-')
            for keyword, folder in hackathon_folder_mappings.items():
                if keyword in query_lower or keyword in event_lower:
                    hackathon_images = get_image_paths('hackathons', folder)
                    images.extend(hackathon_images)
                    break
        
        relevant_sections.append('hackathons')
    
    # Remove duplicates from images and limit to 15 for better performance
    unique_images = list(dict.fromkeys(images))
    
    return "\n".join(context_parts), unique_images[:15], list(set(relevant_sections))

def generate_response_with_gemini(context: str, question: str,relevant_sections: List[str]) -> str:
    """Generate response using Google Gemini API"""
    try:
        global gemini_model
        
        if not gemini_model:
            return generate_fallback_response(context, question)
        
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
        for this you can get the answer {relevant_sections}
        Answer:
        """
        
        response = gemini_model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Error generating response with Gemini: {e}")
        # Check if it's a quota exceeded error
        if "quota" in str(e).lower() or "429" in str(e):
            return generate_fallback_response(context, question)
        return f"I apologize, but I encountered an error while processing your request. Please try again. Error: {str(e)}"

def generate_fallback_response(context: str, question: str) -> str:
    """Generate a fallback response when Gemini API is unavailable"""
    if not context:
        return """Hello! I'm K Sree Charan's portfolio assistant. I can help you learn about:
        
        🎯 Professional Experience at MAQ Software Solutions
        💻 Technical Skills and Technologies
        🚀 Projects (AgriVision, Health Buddy, Study Buddy, Sarthi, and more)
        🏆 Hackathon Achievements and Awards
        🎓 Education and Certifications
        📧 Contact Information
        
        Please ask me about any of these topics!"""
    
    # Simple keyword-based responses
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['experience', 'work', 'job', 'maq']):
        return f"""Based on my portfolio data, here's information about K Sree Charan's work experience:

{context}

K Sree Charan is currently working as a Full Stack Developer at MAQ Software Solutions since 2025, where he has developed 5+ web applications and improved app performance by 40%. He has also mentored 2 junior developers and works with technologies like Node.js, TypeScript, MongoDB, Express.js, AWS, and AI/ML.

Would you like to know more about specific projects or skills?"""
    
    elif any(word in question_lower for word in ['project', 'agrivision', 'health', 'study']):
        return f"""Here are K Sree Charan's key projects:

{context}

These projects showcase expertise in full-stack development, AI/ML integration, and healthcare technology. Each project includes detailed GitHub repositories and live demonstrations.

Would you like to explore any specific project in detail?"""
    
    elif any(word in question_lower for word in ['hackathon', 'competition', 'award']):
        return f"""K Sree Charan has an impressive track record in hackathons:

{context}

With 8+ hackathon participations and multiple wins including DevFest, Microsoft Hackathon, and Kriyeta 3.0, K Sree Charan has demonstrated consistent excellence in competitive programming and innovation.

Would you like to know more about any specific hackathon or achievement?"""
    
    elif any(word in question_lower for word in ['skill', 'technology', 'tech']):
        return f"""K Sree Charan's technical expertise includes:

{context}

The skills span across frontend development (React, Next.js, TypeScript), backend technologies (Node.js, Python), databases (MongoDB, PostgreSQL), and cloud services (AWS). All skills are rated with proficiency levels for transparency.

Would you like to know more about any specific technology or skill area?"""
    
    else:
        return f"""Based on your question about K Sree Charan's portfolio:

{context}

This information provides a comprehensive overview of the requested topic. K Sree Charan is a skilled Full Stack Developer with expertise in modern technologies, successful project delivery, and competitive programming achievements.

Feel free to ask more specific questions about experience, projects, skills, or achievements!"""

# Initialize portfolio data on startup
def initialize_app():
    """Initialize the application on startup"""
    try:
        logger.info("Starting application initialization...")
        global portfolio_data
        portfolio_data = load_portfolio_data()
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        # Set a fallback data structure matching your JSON format
        portfolio_data = {
            "name": "K Sree Charan",
            "title": "Full Stack Developer at MAQ Software Solutions",
            "technologies": ["Python", "Machine Learning", "React", "Node.js"],
            "experienceSummary": {
                "yearsExperience": "1+",
                "projectsCompleted": "15+",
                "technologiesKnown": "10+",
                "hackathonsParticipated": "10+"
            },
            "workExperience": [],
            "education": [],
            "projects": [],
            "hackathons": {"events": []},
            "contact": {
                "email": "sreecharan9484@gmail.com",
                "phone": "+91 9876543210",
                "location": "Noida, India"
            }
        }

# Routes

@app.route('/')
def root():
    return jsonify({
        "message": "Portfolio Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "docs": "/docs",
            "health": "/health",
            "portfolio_summary": "/portfolio-summary"
        }
    })

@app.route('/chat', methods=['POST'])
@swag_from({
    'tags': ['Chat'],
    'summary': 'Chat endpoint',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['question'],
                'properties': {
                    'question': {
                        'type': 'string',
                        'example': 'Tell me about your experience'
                    }
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Success',
            'schema': {
                'type': 'object',
                'properties': {
                    'answer': {'type': 'string'},
                    'images': {'type': 'array', 'items': {'type': 'string'}},
                    'relevant_sections': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        }
    }
})
def chat():
    try:
        if not portfolio_data:
            print("Portfolio data not loaded")
            return jsonify({"error": "Portfolio data not loaded. Please check the server configuration."}), 500
        
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Question is required"}), 400
        
        query = data['question'].strip()
        if not query:
            return jsonify({"error": "Question cannot be empty"}), 400
        
        # Search portfolio data
        context, images, relevant_sections = search_portfolio_data(query, portfolio_data)
        
        if not context:
            context = "I can help you with information about K Sree Charan's skills, experience, education, hackathons, and projects."
        
        # Generate response using Gemini
        answer = generate_response_with_gemini(context, query,relevant_sections)
        
        return jsonify({
            "answer": answer,
            "images": images,
            "relevant_sections": relevant_sections
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            "answer": f"I apologize, but I encountered an error while processing your request: {str(e)}",
            "images": [],
            "relevant_sections": []
        }), 500

@app.route('/health')
@swag_from({
    'tags': ['System'],
    'summary': 'Health check'
})
def health_check():
    api_key = os.getenv("GOOGLE_API_KEY")
    
    # Check portfolio data structure
    portfolio_structure = {}
    if portfolio_data:
        portfolio_structure = {
            "has_name": bool(portfolio_data.get('name')),
            "has_workExperience": bool(portfolio_data.get('workExperience')),
            "has_projects": bool(portfolio_data.get('projects')),
            "has_hackathons": bool(portfolio_data.get('hackathons')),
            "has_skills": bool(portfolio_data.get('skills')),
            "has_contact": bool(portfolio_data.get('contact')),
            "projects_count": len(portfolio_data.get('projects', [])),
            "hackathons_count": len(portfolio_data.get('hackathons', {}).get('events', [])) if isinstance(portfolio_data.get('hackathons'), dict) else 0
        }
    
    return jsonify({
        "status": "healthy",
        "portfolio_data_loaded": portfolio_data is not None,
        "portfolio_structure": portfolio_structure,
        "google_api_key_set": bool(api_key),
        "gemini_model_ready": gemini_model is not None,
        "api_key_length": len(api_key) if api_key else 0,
        "api_key_preview": api_key[:10] + "..." if api_key and len(api_key) > 10 else api_key
    })

@app.route('/portfolio-summary')
@swag_from({
    'tags': ['Portfolio'],
    'summary': 'Portfolio summary'
})
def portfolio_summary():
    if not portfolio_data:
        return jsonify({"error": "Portfolio data not loaded"}), 500
    
    summary = {
        "name": portfolio_data.get('name', ''),
        "title": portfolio_data.get('title', ''),
        "main_sections": {
            "workExperience": len(portfolio_data.get('workExperience', [])),
            "education": len(portfolio_data.get('education', [])),
            "projects": len(portfolio_data.get('projects', [])),
            "certifications": len(portfolio_data.get('certifications', [])),
            "skills_categories": len(portfolio_data.get('skills', {})),
            "hackathons": len(portfolio_data.get('hackathons', {}).get('events', [])) if isinstance(portfolio_data.get('hackathons'), dict) else 0
        },
        "technologies": portfolio_data.get('technologies', []),
        "experienceSummary": portfolio_data.get('experienceSummary', {})
    }
    
    return jsonify(summary)

@app.route('/debug-env')
@swag_from({
    'tags': ['Debug'],
    'summary': 'Environment debug'
})
def debug_env():
    return jsonify({
        "all_env_vars": list(os.environ.keys()),
        "google_api_key_exists": "GOOGLE_API_KEY" in os.environ,
        "google_api_key_value": os.getenv("GOOGLE_API_KEY", "NOT_FOUND"),
        "current_directory": os.getcwd(),
        "env_file_exists": Path(".env").exists()
    })

# Static file routes
@app.route('/hackathons/<path:filename>')
def serve_hackathon_images(filename):
    """Serve hackathon images"""
    return send_from_directory('hackathons', filename)

@app.route('/projects/<path:filename>')
def serve_project_images(filename):
    """Serve project images"""
    return send_from_directory('projects', filename)

@app.route('/member-photoes/<path:filename>')
def serve_member_photos(filename):
    """Serve member photos"""
    return send_from_directory('member-photoes', filename)

# Backward compatibility routes
@app.route('/photo/<path:filename>')
def serve_photo_images(filename):
    """Serve photo images (backward compatibility)"""
    return send_from_directory('hackathons', filename)

@app.route('/projectfolder/<path:filename>')
def serve_projectfolder_images(filename):
    """Serve project folder images (backward compatibility)"""
    return send_from_directory('projects', filename)

if __name__ == "__main__":
    # Initialize the application
    initialize_app()
    
    # Run the Flask app
    app.run(host="0.0.0.0", port=8003, debug=True)
