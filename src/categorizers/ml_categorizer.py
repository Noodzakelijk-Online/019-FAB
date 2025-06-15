from typing import Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
import joblib
import os

from src.categorizers.base import BaseCategorizer

class MLCategorizer(BaseCategorizer):
    """Categorizes documents using a trained Machine Learning model."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_path = self.config.get("ml_model_path", "models/ml_categorizer_model.joblib")
        self.vectorizer_path = self.config.get("ml_vectorizer_path", "models/tfidf_vectorizer.joblib")
        self.model = None
        self.vectorizer = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
            self.model = joblib.load(self.model_path)
            self.vectorizer = joblib.load(self.vectorizer_path)
            print("ML Categorizer model and vectorizer loaded.")
        else:
            print("ML Categorizer model or vectorizer not found. Model needs to be trained.")
            # In a real scenario, you might trigger a training process or use a fallback.

    def train_model(self, X_train: list, y_train: list):
        """Trains the ML model with provided data."""
        self.vectorizer = TfidfVectorizer(max_features=1000)
        X_train_vectorized = self.vectorizer.fit_transform(X_train)
        
        self.model = LogisticRegression(max_iter=1000) # Increased max_iter for convergence
        self.model.fit(X_train_vectorized, y_train)

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.vectorizer, self.vectorizer_path)
        print("ML Categorizer model trained and saved.")

    def categorize(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.model or not self.vectorizer:
            print("ML model not loaded or trained. Cannot categorize using ML. Returning fallback.")
            return {"category": "Uncategorized", "confidence_score": 0.0}

        ocr_text = processed_data.get("ocr_text", "")
        if not ocr_text:
            return {"category": "Uncategorized", "confidence_score": 0.0}

        text_vectorized = self.vectorizer.transform([ocr_text])
        
        predicted_category = self.model.predict(text_vectorized)[0]
        confidence_score = max(self.model.predict_proba(text_vectorized)[0])

        return {"category": predicted_category, "confidence_score": float(confidence_score)}


