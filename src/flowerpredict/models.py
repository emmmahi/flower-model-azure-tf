from pydantic import BaseModel

class ImageData(BaseModel):
    image: str

class Prediction(BaseModel):
    label: int
    confidence: float
    prediction: str
    version: int
    version_iso: str

class WordData(BaseModel):
    word: str
