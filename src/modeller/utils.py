import os
import logging
#import zlib
#import numpy as np
#import pandas as pd
import pathlib
import zipfile
import json
import keras
from datetime import datetime
import tensorflow as tf
from PIL import Image

from functools import lru_cache
#from base64 import b64decode
from io import BytesIO
#from PIL import Image
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient
#from sklearn.linear_model import LogisticRegression

# Are we running in the cloud?
CLOUD = os.environ.get("USE_AZURE_CREDENTIAL", "false").lower() == "true"

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
    
# Check how many messages are in the queue
def n_images_waiting() -> int:
    with get_queue_service_client() as queue_client:
        queue = queue_client.get_queue_client(os.environ["STORAGE_QUEUE"])
        queue_properties = queue.get_queue_properties()
        message_count = queue_properties.approximate_message_count
        logging.info(f"Labeled images waiting in queue: {message_count}")
        return message_count
    
def latest_model_version() -> int:
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
        blobs = container_client.list_blobs(name_starts_with="models/")
        latest = max([int(x.name.split("_")[1].split(".")[0]) for x in blobs])

        unix_to_iso = datetime.fromtimestamp(latest).isoformat()
        logging.info(f"latest_model_version() seeing: {latest} created at {unix_to_iso}")
        return latest

@lru_cache(maxsize=5)
def load_model(latest_version):
    # Find the latest model from /models folder in the storage container
    # The model name follows the pattern model_{unix_seconds}.joblib
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
        #blob_client = container_client.get_blob_client(f"models/flowers-model_0.keras")
        blob_client = container_client.get_blob_client(f"models/model_{latest_version}.keras")
        logging.info(f"Loading model from Azure Blob Storage")
        logging.info(f"Loading model version {latest_version}")

        blob_data = blob_client.download_blob()
        file_bytes = blob_data.readall()
        logging.info(f"Dowload model size: {len(file_bytes)} bytes")
        return file_bytes

        # model_data = BytesIO()
        # blob_client.download_blob().readinto(model_data)
        # model_data.seek(0)  # Ensure the pointer is at the start
        # return model_data
    


def load_valdata():
    """Load validation iamges from the storage container.
    """
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
        blob_client = container_client.get_blob_client("datasets/val_data.zip")

        os.makedirs('./val/', exist_ok=True)
        target_folder = pathlib.Path('./val/')
        blob_stream = blob_client.download_blob()
        zip_data = blob_stream.readall() # Get the entire blob content as bytes

        # Open the zip file from the in-memory bytes and extract it
        with zipfile.ZipFile(BytesIO(zip_data), mode="r") as archive:
            print(f"Extracting content to {target_folder}...")
            archive.extractall(target_folder)
            print("Extraction complete!")

        return None
    
def format_image(image):
    IMAGE_RES = 224
    image = tf.image.resize(image, (IMAGE_RES, IMAGE_RES)) #/255.0
    return image
     
def get_all_from_queue():
    """Get all the images from the queue.
    """
    logging.info("Getting all images from the queue.")
    with get_queue_service_client() as queue_service_client:
        queue = queue_service_client.get_queue_client(os.environ["STORAGE_QUEUE"])
        messages = queue.receive_messages(messages_per_page=32)
        new_rows = []
        for msg in messages:
            # Get information from the queue message
            message_content = json.loads(msg.content)
            blob_name = message_content.get("blob_name")
            label = message_content.get("label")

            logging.info(f"Processing message {msg}")
            logging.info(f"Message name {blob_name}")
            logging.info(f"Message label {label}")

            # Download corresponding image from blob storage
            with get_blob_service_client() as blob_service_client:
                container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
                blob_client = container_client.get_blob_client(blob_name)

                blob_data = blob_client.download_blob()
                # If it is a binary file, you can read it directly as bytes
                file_bytes = blob_data.readall()
                image = keras.preprocessing.image.load_img(BytesIO(file_bytes))
                image = format_image(image)
                # Delete blob after dowload
                blob_client.delete_blob()
            
            # Add [image, label] pair to training data list
            new_rows.append((image, label))
            # Delete the message from queue
            queue.delete_message(msg)

        logging.info(f" Got {len(new_rows)} images form queue.")
        return new_rows



def upload(temp_model, model_file_path):
    """Append the new data to the dataset.
    """
    logging.info(f"Uploading {type(temp_model)} to {model_file_path}.")
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
        blob_client = container_client.get_blob_client(model_file_path)
        blob_client.upload_blob(temp_model, overwrite=True)
        logging.info(f"Upload complete for {model_file_path}.")

# def images_to_csv(images: list[tuple[Image.Image, int]]) -> str:
#     """Convert a list of images to a CSV string.
#     """
#     new_rows = []
#     for img, label in images:
#         # Convert the image to a binary string
#         pixel_data = [str(int(x / 255)) for x in img.getdata()]
#         pixel_csv = ",".join(pixel_data)
#         new_rows.append(f"{pixel_csv},{label}")
#     logging.info(f"The first incoming row: {new_rows[0][:25]}...")
    
#     # Convert to a single newline-separated string
#     new_rows = "\n".join(new_rows) + "\n"
#     return new_rows

# def deserialize_grayscale(compressed_b64:str, size=(20, 40), has_label=False) -> tuple[Image.Image, int]:
#     """Decompress the base64 string and convert it to an image.
#     """

#     label=None

#     # Base64 => bytes
#     decoded = b64decode(compressed_b64)

#     if has_label:
#         # Extract the label
#         label = int.from_bytes(decoded[-1:], byteorder="big")
#         decoded = decoded[:-1]

#     uncompressed = zlib.decompress(decoded)

#     # Convert back to numpy array
#     img = Image.fromarray(np.frombuffer(uncompressed, dtype=np.bool_).reshape(size))

#     return img, label

# def train_model(dataset: str, model_version: int) -> LogisticRegression:
#     """Train a model on the given dataset.
#     """
#     logging.info(f"Training the model on {len(dataset.splitlines())} samples.")
#     df = pd.read_csv(StringIO(dataset), header=None)
#     logging.info(f"Loaded {len(df)} samples from the dataset.")
#     logging.info(f"Last row: {df.iloc[-1]}")
#     X = df.iloc[:, :-1]
#     y = df.iloc[:, -1]
#     model = LogisticRegression()
#     model.fit(X, y)

#     return model

