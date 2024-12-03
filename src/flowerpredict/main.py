import joblib
import os
import logging
from io import BytesIO
import base64
from PIL import Image
import numpy as np
import tempfile
import tensorflow as tf

from fastapi import FastAPI, File, UploadFile, HTTPException
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

# @app.post("/predict")
# def predict_hello(word_data: WordData):
#     return {"response": f"You gave word {word_data.word}"}

@app.post("/predict")
def predict_flower(image_file:  UploadFile = File(...)):
        
    # Check the MIME type
    if image_file.content_type not in ("image/jpeg", "image/jpg"):
        raise HTTPException(status_code=400, detail="Only JPEG files are allowed")
        
    # load .keras model
    model_bytes = load_model() #return joblib.load(data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".keras") as temp_file:
        temp_file.write(model_bytes.read())
        temp_file_path  = temp_file.name

    model = tf.keras.models.load_model(temp_file_path)
    logging.info(f"Model succesfully loaded. Summary: {model.summary()}")

    return {"messsage": "Model loaded successfully"}
#   return {"imagefile name": image_file.name}

