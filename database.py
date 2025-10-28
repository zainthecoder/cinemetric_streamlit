"""
Database models and connection setup using SQLAlchemy
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class Persona(Base):
    """Movie character personas for evaluation"""
    __tablename__ = "personas"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    prompt_template = Column(Text, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    image_url = Column(String, nullable=True)
    
    # Relationships
    evaluation_results = relationship("EvaluationResult", back_populates="persona")


class Conversation(Base):
    """Stored conversation data"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    is_multi_turn = Column(Boolean, default=False, nullable=False)
    turns = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluation_results = relationship("EvaluationResult", back_populates="conversation")


class EvaluationResult(Base):
    """Evaluation results from personas"""
    __tablename__ = "evaluation_results"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    metric = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=False)
    turn_evaluations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="evaluation_results")
    persona = relationship("Persona", back_populates="evaluation_results")


# Database initialization
def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, will close in app


# Helper functions
def get_all_personas(db):
    """Get all personas from database"""
    return db.query(Persona).all()


def get_persona_by_id(db, persona_id):
    """Get a specific persona by ID"""
    return db.query(Persona).filter(Persona.id == persona_id).first()


def create_conversation(db, content, is_multi_turn=False, turns=None):
    """Create a new conversation"""
    conversation = Conversation(
        content=content,
        is_multi_turn=is_multi_turn,
        turns=turns
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def create_evaluation_result(db, conversation_id, persona_id, metric, score, explanation, turn_evaluations=None):
    """Create a new evaluation result"""
    result = EvaluationResult(
        conversation_id=conversation_id,
        persona_id=persona_id,
        metric=metric,
        score=score,
        explanation=explanation,
        turn_evaluations=turn_evaluations
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def import_personas_from_json(db, personas_data):
    """Import personas from JSON data"""
    imported_count = 0
    for persona_data in personas_data:
        # Check if persona already exists
        existing = db.query(Persona).filter(Persona.slug == persona_data["slug"]).first()
        if existing:
            print(f"⚠️ Persona '{persona_data['name']}' already exists, skipping...")
            continue
        
        persona = Persona(
            name=persona_data["name"],
            description=persona_data["description"],
            prompt_template=persona_data["prompt_template"],
            slug=persona_data["slug"],
            image_url=persona_data.get("image_url")
        )
        db.add(persona)
        imported_count += 1
    
    db.commit()
    print(f"✅ Imported {imported_count} new personas")
    return imported_count