import time
import logging
import tensorflow as tf
import keras
import tempfile
import os

from keras.preprocessing import image
from datetime import datetime
from utils import (
    n_images_waiting,
    latest_model_version,
    load_model,
    load_valdata,
    get_all_from_queue,
    upload
)


#BLOB_CONTAINER_NAME = "uploaded-files"
IMAGE_RES = 224

# Set the logging level for this script
logging.basicConfig(level=logging.INFO)

# Set the logging level for all azure-* libraries
azure_logger = logging.getLogger("azure")
azure_logger.setLevel(logging.WARNING)

## 0. Load the validation data and rename the folders to get them same order as tin the model
load_valdata()


flower_list = ['dandelion', 'daisy', 'tulips', 'sunflowers', 'roses']
os.rename('./val/dandelion', './val/0_dandelion')
os.rename('./val/daisy', './val/1_daisy')
os.rename('./val/tulips', './val/2_tulips')
os.rename('./val/sunflowers', './val/3_sunflowers')
os.rename('./val/roses', './val/4_roses')



while True:
    n_images = n_images_waiting()
    if n_images > 1:

        # 1. Load .keras model
        latest_version = latest_model_version()
        logging.info(f"Latest version: {latest_version}")
        model_bytes = load_model(latest_version)
        logging.info(f"Size of model_bytes: {len(model_bytes)} bytes")
        logging.info(f"First 100 bytes of model_bytes: {model_bytes[:100]}")



        with tempfile.NamedTemporaryFile(delete=False, suffix=".keras") as temp_file:
            # Read the BytesIO object's content as bytes
            temp_file.write(model_bytes)
            temp_file_path = temp_file.name

        logging.info(f"Temporary model file path: {temp_file_path}")
        logging.info(f"Size of temp_file: {os.path.getsize(temp_file_path)} bytes")
        logging.info(f"File extension is: {os.path.splitext(temp_file_path)[-1]}")


        model = tf.keras.models.load_model(temp_file_path)
        logging.info(f"Model: {model.summary(show_trainable=True)}")

        # Use current UNIX time as the version of the model
        model_version = int(time.time())
        iso_time = datetime.fromtimestamp(model_version).isoformat()
        logging.info(f" Found {n_images} in Queue at {model_version} ({iso_time}).")

        # 2a. Read all the messages from queue and load corresponding images from blob
        # then delete messages from queue and images from blob
        # If pricess fails, the images are lost
        data_pairs = get_all_from_queue()

        # Separate images and labels 
        images = [pair[0] for pair in data_pairs] # List of image arrays
        labels = [pair[1] for pair in data_pairs] # List of labels

        for i, img in enumerate(images):
            logging.info(f"Image {i} shape: {img.shape}, dtype: {img.dtype}")
        for i, lbl in enumerate(labels):
            logging.info(f"Label {i}: {lbl}")

        logging.info(f"len(data_pairs): {len(data_pairs)}.")

        # If queue reading was succesful, train the model
        if len(data_pairs) > 0:
            logging.info(f"Finetuning starts.")

            # 2b. Convert to tf.data.Dataset
            train_ds = tf.data.Dataset.from_tensor_slices((images, labels))
            train_ds = train_ds.batch(len(data_pairs)).shuffle(len(data_pairs))
            logging.info(f"Train dataset length: {len(train_ds)}")


            # 3. Create validation dataset from loaded validation data
            val_ds = keras.utils.image_dataset_from_directory(
                './val/',
                validation_split=None, 
                seed=123,
                image_size=(IMAGE_RES, IMAGE_RES),
                batch_size=32
                )
            
            # 4. Image preprocessing
            def format_train_image(image,label):
                image = tf.image.resize(image, (IMAGE_RES, IMAGE_RES))/255.0
                return image, label
            
            def format_val_image(image,label):
                image = tf.image.resize(image, (IMAGE_RES, IMAGE_RES))/255.0
                return image, label
            
            train_batches = train_ds.map(format_train_image).prefetch(tf.data.AUTOTUNE)
            val_batches = val_ds.map(format_val_image).prefetch(tf.data.AUTOTUNE)

            logging.info(f"Number of training batches: {len(list(train_batches))}")
            logging.info(f"Number of validation batches: {len(list(val_batches))}")


            # 5. Train the model
            history = model.fit(train_batches,
                                epochs=3,
                                batch_size=len(data_pairs)
                                )
            
            # 6. Evaluate the model
            model.evaluate(val_batches, verbose=2)

            # 7. Upload the model to Azure Storage
            model.save("temp_model.keras")
            logging.info(f"Saved model path: temp_model.keras")
            logging.info(f"Size of saved model: {os.path.getsize('temp_model.keras')} bytes")
            
            try:
                loaded_model = tf.keras.models.load_model("temp_model.keras")
                logging.info("Saved model reloaded successfully")
                logging.info(f"Reloaded model summary: {loaded_model.summary(show_trainable=True)}")
            except Exception as e:
                logging.error(f"Error reloading saved model: {e}")

            upload("temp_model.keras", f"models/model_{model_version}.keras")
        
    else:
        logging.info("No images in queue.")