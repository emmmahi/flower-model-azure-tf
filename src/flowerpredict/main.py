import joblib
import os
import logging
from io import BytesIO
import base64
from PIL import Image
import numpy as np

#import tensorflow as tf
from fastapi import FastAPI
from datetime import datetime


from models import ImageData, Prediction, WordData
from utils import latest_model_version, load_model, deserialize_grayscale

# Set the logging level for this script
logging.basicConfig(level=logging.INFO)

IMAGE_RES = 224

def format_image(image):
    image=tf.image.resize(image, (IMAGE_RES, IMAGE_RES))/255.0
    return image

# Set the logging level for all azure-* libraries
azure_logger = logging.getLogger('azure')
azure_logger.setLevel(logging.WARNING)

app = FastAPI()

@app.post("/predict")
def predict_hello(word_data: WordData):
    return {"response": f"You gave word {word_data.word}"}


