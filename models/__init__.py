# models/__init__.py
# Import models so SQLAlchemy knows about them when creating tables
from .user import User
from .pdf_file import PDFFile
from .quiz import Quiz
from .quiz_attempt import QuizAttempt
from .progress import Progress
