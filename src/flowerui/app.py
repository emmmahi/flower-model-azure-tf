import requests
import os
import logging
import streamlit as st
#import numpy as np
from io import BytesIO
#import base64
import uuid
import json

#from PIL import Image
from azure.storage.queue import QueueServiceClient
from azure.storage.blob import BlobServiceClient  

#from pydantic import BaseModel

from image_utils import to_40x20_binary, serialize_grayscale
#from prediction import predict

# Set the logging level for this script
logging.basicConfig(level=logging.INFO)

# Set the logging level for all azure-* libraries
azure_logger = logging.getLogger('azure')
azure_logger.setLevel(logging.WARNING)

# Decide if we're running in the cloud or locally
CLOUD = os.environ.get("USE_AZURE_CREDENTIAL", "false").lower() == "true"

def get_queue_service_client():
    """
    The STORAGE_CONNECTION_STRING is only set up when running in the cloud. 
    If it's not set, we're running locally with Azurite.
    """
    if CLOUD:
        from azure.identity import DefaultAzureCredential # type: ignore
        credential = DefaultAzureCredential()
        account_url = os.environ["STORAGE_QUEUE_URL"]
        return QueueServiceClient(account_url=account_url, credential=credential)
    else:
        return QueueServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
    
def get_blob_service_client():
    """
    The STORAGE_CONNECTION_STRING is only set up when running in the cloud. 
    If it's not set, we're running locally with Azurite.
    """
    if CLOUD:
        from azure.identity import DefaultAzureCredential # type: ignore
        credential = DefaultAzureCredential()
        account_url = os.environ["STORAGE_BLOB_URL"]
        return BlobServiceClient(account_url=account_url, credential=credential)
    else:
        return BlobServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])


URL = os.environ["PREDICT_FLOWER_URL"]

def call_predict_word(word) -> dict|None:
    try:
        # Lähetetään JSON-muotoinen data POST-pyynnössä
        response = requests.post(URL, json={"word": word})
    except requests.exceptions.ConnectionError as e:
        st.warning("Failed to connect to the backend.")
        return None

    # Käsitellään vastaus
    if response.ok:
        st.write("Prediction: ", response.json())
        return response.json()
    else:
        st.warning("Failed to get prediction from the backend.")
        st.write(response.text)
        return None

def call_predict(image_file) -> dict|None:
    try: 
        files = {"image_file": (image_file.name, image_file, "image/jpeg")}
        response = requests.post(URL, files=files)  #post imagefile to backend

    except requests.exceptions.ConnectionError as e:
        st.warning("Failed to connect to the backend.")
        return None
    
    # Handle response
    if response.ok:
        st.write("Prediction: ", response.json())
    else:
        st.warning("Failed to get prediction from the backend.")
        st.write(response.text)
        return None
    
    return response.json()



word_input = st.text_input("Enter a word", "")

if word_input:
    st.write("You entered:", word_input)
    prediction = call_predict_word(word_input)

st.title("Flower Prediction NEW")

image_file = st.file_uploader("Choose an image", type=['jpeg', 'jpg'])
#button = st.button("Predict")

if image_file is not None:

    # visualize the image
    st.image(image_file, caption="Uploaded image.")

    # predict the image button 
    if st.button("Predict"):
        st.write("You pushed the button")
        prediction = call_predict(image_file)

    st.write("Not happy? Submit photo for training.")

    # submit image for training logic
    flower_list = ['dandelion', 'daisy', 'tulips', 'sunflowers', 'roses']
    label = st.selectbox("Label:", flower_list)
    label_index = flower_list.index(label)

    # Submit button
    # if st.button("Submit for training"):
    #     with get_queue_service_client() as queue_service_client:
    #         with queue_service_client.get_queue_client(os.environ["STORAGE_QUEUE"]) as queue_client:
    #             compressed_b64 = [image_file, label_index]
    #             queue_client.send_message(compressed_b64)

    #             logging.info(f"Message ({label}) as ({compressed_b64}) sent to Queue ({os.environ["STORAGE_QUEUE"]}")")
    #             st.write(f"Sent: {compressed_b64} as {label_index}")

 

# # VERSIO MISSÄ KUVA MENEE JONOON DEKOODATTUNA, ei välttämättä ole toimiva versio
#     if st.button("Submit for training"):
#         # Read image data and encode it as Base64
#         image_data = image_file.read()  # Read image file
#         encoded_image = base64.b64encode(image_data).decode('utf-8')  # Encode to Base64

#         # Create a message payload
#         payload = {
#             "image_data": 1234,
#             "label": label,  # Label selected by the user
#         }

#         # Send the message to Azure Queue
#         with get_queue_service_client() as queue_service_client:
#             queue_client = queue_service_client.get_queue_client(os.environ["STORAGE_QUEUE"])
#             #queue_client.send_message(base64.b64encode(str(payload).encode("utf-8")).decode("utf-8"))
#             queue_client.send_message(payload)

#         st.write(f"Image and label sent to the queue.")


    if st.button("Submit for training"):

        # Upload the image to Azure Blob Storage
        with get_blob_service_client() as blob_service_client:
            #Generate unique filename
            blob_name = f"{uuid.uuid4()}_{image_file.name}"

            #Get the container and blob clients
            container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
            blob_client = container_client.get_blob_client(blob_name)

            # Upload file to Azure Blob Storage
            with BytesIO(image_file.getvalue()) as uploaded_file:
                blob_client.upload_blob(uploaded_file.read(), overwrite=True)

            print(f"File {blob_name} loaded to blob storage.")
        
        # Send image name and label to the queue as json structure
        with get_queue_service_client() as queue_service_client:

            with queue_service_client.get_queue_client(os.environ["STORAGE_QUEUE"]) as queue_client:

                # Construct the queue message with blob URL and label
                message = {
                    "blob_name": blob_name,
                    "label": label_index
                    }
                queue_client.send_message(json.dumps(message))

                logging.info(f"Message ({blob_name}) and {label_index} sent to Queue ({os.environ['STORAGE_QUEUE']})")
                st.write(f"Sent: {blob_name} and {label_index}")



