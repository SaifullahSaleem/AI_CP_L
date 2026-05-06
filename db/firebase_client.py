"""
Firebase Firestore client for chat persistence.
Handles saving and loading chat threads.
"""

import firebase_admin
from firebase_admin import credentials, firestore
from app.core.config import settings


# ── Globals ──────────────────────────────────────────────────────────
_db = None


def _get_db():
    """Lazy-init Firebase and return Firestore client."""
    global _db
    if _db is not None:
        return _db

    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    _db = firestore.client()
    return _db


# ── Public helpers ───────────────────────────────────────────────────
def save_chat(thread_id: str, messages: list[dict]):
    """
    Save chat messages to Firestore.

    Document path: chats/{thread_id}
    Data: { messages: [...] }
    """
    db = _get_db()
    doc_ref = db.collection("chats").document(thread_id)
    doc_ref.set({"messages": messages})


def load_chat(thread_id: str) -> list[dict]:
    """
    Load chat messages from Firestore.

    Returns empty list if thread doesn't exist.
    """
    db = _get_db()
    doc_ref = db.collection("chats").document(thread_id)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        return data.get("messages", [])
    return []
