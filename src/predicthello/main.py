import joblib
import os
import logging

from fastapi import FastAPI
from datetime import datetime
from sklearn.linear_model import LogisticRegression

from models import ImageData, Prediction
from utils import latest_model_version, load_model, deserialize_grayscale

# Set the logging level for this script
logging.basicConfig(level=logging.INFO)

# Set the logging level for all azure-* libraries
azure_logger = logging.getLogger('azure')
azure_logger.setLevel(logging.WARNING)

app = FastAPI()

@app.post("/predict")
def predict_hello(image: ImageData) -> Prediction:
    
    img, _ = deserialize_grayscale(image.image)
    pixel_data = [x / 255 for x in img.getdata()]
    logging.info(f"Received base64 data: {image.image[:50]}...")
    logging.info(f"Image mode is {img.mode}")
    logging.info(f"Predicting on image with {len(pixel_data)} pixels")
    logging.info(f"Pixel data: {pixel_data[:30]}...")

    latest_version = latest_model_version()
    model: LogisticRegression = load_model(latest_version)
    
    prediction = model.predict([pixel_data])[0]
    logging.info(f"Prediction: {prediction}")
    return Prediction(
        label=prediction,
        prediction="Hello" if prediction == 1 else "World",
        version=latest_version,
        version_iso=datetime.fromtimestamp(latest_version).isoformat()
    )
