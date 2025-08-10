import json
import os
from typing import List, Dict, Tuple, Any
import numpy as np
from sentence_transformers import SentenceTransformer, util

def load_data(file_path: str) -> Dict:
    """
    Load data from a JSON file.
    """
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Try to open and parse the JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {file_path}")
        return {}
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return {}

def preprocess_data(data: Dict) -> Tuple[List[Dict], Dict]:
    """
    Process the JSON data into text chunks for embedding.
    """
    text_chunks = []
    
    # Process personal info
    text_chunks.append({
        "content": f"Name: {data.get('name', '')}\nTitle: {data.get('title', '')}\n" +
                  f"Technologies: {', '.join(data.get('technologies', []))}\n" +
                  f"Contact: {data.get('contact', {}).get('email', '')}, {data.get('contact', {}).get('phone', '')}, {data.get('contact', {}).get('location', '')}",
        "type": "personal_info"
    })
    
    # Process work experience
    for job in data.get('workExperience', []):
        text_chunks.append({
            "content": f"Role: {job.get('role', '')}\nCompany: {job.get('company', '')}\n" +
                      f"Years: {job.get('years', '')}\nLocation: {job.get('location', '')}\n" +
                      f"Achievements: {', '.join(job.get('achievements', []))}\n" +
                      f"Technologies: {', '.join(job.get('technologies', []))}",
            "type": "work_experience",
            "company": job.get('company', '')
        })
    
    # Process education
    for edu in data.get('education', []):
        text_chunks.append({
            "content": f"Degree: {edu.get('degree', '') or edu.get('qualification', '')}\n" +
                      f"Field: {edu.get('field', '')}\nInstitution: {edu.get('institution', '')}\n" +
                      f"Years: {edu.get('years', '')}\nGrade: {edu.get('grade', '')}\n" +
                      f"Achievements: {', '.join(edu.get('achievements', []))}",
            "type": "education",
            "institution": edu.get('institution', '')
        })
    
    # Process projects
    for project in data.get('projects', []):
        text_chunks.append({
            "content": f"Project: {project.get('name', '')}\nCategory: {project.get('category', '')}\n" +
                      f"Description: {project.get('description', '')}\n" +
                      f"Duration: {project.get('duration', '')}\nTeam Size: {project.get('teamSize', '')}\n" +
                      f"Technologies: {', '.join(project.get('technologies', []))}\n" +
                      f"Features: {', '.join(project.get('features', []))}",
            "type": "project",
            "name": project.get('name', '')
        })
    
    # Process hackathons
    for event in data.get('hackathons', {}).get('events', []):
        text_chunks.append({
            "content": f"Hackathon: {event.get('event', '')}\nResult: {event.get('result', '')}\n" +
                      f"Month/Year: {event.get('monthYear', '')}\nHost: {event.get('host', '')}\n" +
                      f"Team Size: {event.get('teamSize', '')}\n" +
                      f"Technologies: {', '.join(event.get('technologies', []))}\n" +
                      f"Awards: {', '.join(event.get('awards', []))}",
            "type": "hackathon",
            "event": event.get('event', '')
        })
    
    # Process skills
    for category, skills in data.get('skills', {}).items():
        skill_text = f"Skill Category: {category}\n"
        for skill, proficiency in skills.items():
            skill_text += f"{skill}: {proficiency}\n"
        
        text_chunks.append({
            "content": skill_text,
            "type": "skills",
            "category": category
        })
    
    return text_chunks, data

def find_similar_content(query: str, text_chunks: List[Dict], original_data: Dict, model) -> List[Dict]:
    """
    Find chunks of content that are semantically similar to the query.
    """
    if not text_chunks:
        return []
    
    # Encode the query
    query_embedding = model.encode(query)
    
    # Encode all text chunks
    chunk_embeddings = model.encode([chunk["content"] for chunk in text_chunks])
    
    # Calculate cosine similarity
    similarities = np.dot(chunk_embeddings, query_embedding) / (
        np.linalg.norm(chunk_embeddings, axis=1) * np.linalg.norm(query_embedding)
    )
    
    # Get indices of top 3 most similar chunks
    top_indices = np.argsort(similarities)[-5:][::-1]
    
    # Return the top chunks
    return [text_chunks[i] for i in top_indices]

if __name__ == "__main__":
    print("sdf")
    json_file_path = "sreedata.json"
    
    
    user_query = "Tell Me about the study buddy"

    
    sree_data = load_data(json_file_path)
    print("hi")
    text_chunks, original_data = preprocess_data(sree_data)
    print(f"Loaded {len(text_chunks)} text chunks from the file.")
    
    if not text_chunks:
        print(json.dumps({"error": "Failed to load or preprocess data from the file."}, indent=2))
    else:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        similar_content = find_similar_content(user_query, text_chunks, original_data, model)
        
        print(json.dumps(similar_content, indent=1))
