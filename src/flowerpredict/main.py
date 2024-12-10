import joblib
import os
import logging
from io import BytesIO
import base64
from PIL import Image
import numpy as np
import tempfile
import tensorflow as tf
from tensorflow.keras.utils import load_img, img_to_array

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
azure_logger.setLevel(logging.INFO)

app = FastAPI()

# @app.post("/predict")
# def predict_hello(word_data: WordData):
#     return {"response": f"You gave word {word_data.word}"}

@app.post("/predict")
def predict_flower(image_file:  UploadFile = File(...)):
        
    # Check the MIME type
    if image_file.content_type not in ("image/jpeg", "image/jpg"):
        raise HTTPException(status_code=400, detail="Only JPEG files are allowed")
    
    latest_version = latest_model_version()
    logging.info(f"Latest version: {latest_version}")
    # load .keras model (now just my first model, no  versioning)
    model_bytes = load_model(latest_version) #return model_data
    model_bytes.seek(0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".keras") as temp_file:
        temp_file.write(model_bytes.read())
        temp_file_path  = temp_file.name

    model = tf.keras.models.load_model(temp_file_path)
    logging.info(f"Model succesfully loaded. Summary: {model.summary()}")

    # load image file
    image_bytes = image_file.file.read()
    #logging.info(image_bytes)
    test_image = load_img(BytesIO(image_bytes))
    test_image = img_to_array(test_image)  
    test_image = format_image(test_image)

    # predict image
    output = model.predict(tf.expand_dims(test_image, axis=0), batch_size=1)
    logging.info(f"Output: {output}")

    # calculate prediction probability and select corresponding flower label
    output = tf.nn.softmax(output)
    logging.info(f"Output: {output}")
    output_index = tf.argmax(output, axis=1)
    #flower_list = ['roses', 'daisy', 'dandelion', 'sunflowers', 'tulips']
    #flower_list = ['daisy', 'dandelion', 'roses', 'sunflowers', 'tulips']
    flower_list = ['dandelion', 'daisy', 'tulips', 'sunflowers', 'roses']
    prediction = flower_list[int(output_index)]
    logging.info(f"Output: {output}")

    return Prediction(
        label=output_index,
        confidence=float(output[0][int(output_index)]),
        prediction=prediction,
        version=0,
        version_iso=datetime.fromtimestamp(latest_version).isoformat()
    )
#{"messsage": "Model loaded successfully"}
#   return {"imagefile name": image_file.name}

