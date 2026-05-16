import os

ANIMA_BASE      = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR      = os.path.join(ANIMA_BASE, "memory")
VOICES_DIR      = os.path.join(ANIMA_BASE, "voices")
VRM_DIR         = os.path.join(ANIMA_BASE, "vrm")
PERSONALITY_DIR = os.path.join(ANIMA_BASE, "personality")
STATE_DB        = os.path.join(MEMORY_DIR, "anima_state.db")
CHROMA_DB_DIR   = os.path.join(MEMORY_DIR, "chroma")

os.makedirs(MEMORY_DIR,  exist_ok=True)
os.makedirs(VOICES_DIR,  exist_ok=True)
os.makedirs(VRM_DIR,     exist_ok=True)
