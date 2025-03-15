import json
from datetime import datetime
import os
import uuid
from flask import Flask, render_template, request
from azure.storage.blob import BlobServiceClient
from azure.cosmos import cosmos_client, exceptions

app = Flask(__name__)

# Read Azure Storage environment variables
CONN_KEY = os.getenv('APPSETTING_CONN_KEY')
STORAGE_ACCOUNT = os.getenv('APPSETTING_STORAGE_ACCOUNT')
IMAGES_CONTAINER = "images"
COSMOS_URL = os.getenv('APPSETTING_COSMOS_URL')
MasterKey = os.getenv('APPSETTING_MasterKey')
DATABASE_ID = 'lab5messagesdb'
CONTAINER_ID = 'lab5messages'

# Create a connection to Cosmos DB
cosmos_db_client = cosmos_client.CosmosClient(COSMOS_URL, {'masterKey': MasterKey})
cosmos_db = cosmos_db_client.get_database_client(DATABASE_ID)
container = cosmos_db.get_container_client(CONTAINER_ID)

# Create a connection to Azure Blob Storage
blob_service_client = BlobServiceClient(
    account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/",
    credential=CONN_KEY
)

def insert_cosmos(content, img_path):
    """Insert a message into Cosmos DB"""
    new_message = {
        'id': str(uuid.uuid4()),  # Generate unique ID for Cosmos DB
        'content': content,
        'img_path': img_path,
        'timestamp': datetime.now().isoformat(" ", "seconds")
    }
    
    try:
        container.create_item(body=new_message)
    except exceptions.CosmosResourceExistsError:
        print("Resource already exists, didn't insert message.")

def insert_blob(img_path):
    """ Uploads an image to Azure Blob Storage and returns the blob URL """
    filename = img_path.split('/')[-1]  # Extract file name
    blob_client = blob_service_client.get_blob_client(container=IMAGES_CONTAINER, blob=filename)
    
    with open(img_path, mode="rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    
    return f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/{IMAGES_CONTAINER}/{filename}"

@app.route("/handle_message", methods=['POST'])
def handleMessage():
    img_url = ""
    new_message = request.form['msg']
    if 'file' in request.files and request.files['file']:
        image = request.files['file']
        img_path = os.path.join("./static/images", image.filename)
        image.save(img_path)
        img_url = insert_blob(img_path)  # Upload image to Azure and get URL
    
    if new_message:
        insert_cosmos(new_message, img_url)  # Insert message into Cosmos DB
    else:
        insert_cosmos(new_message, "")  # Allow messages without an image
    
    return render_template('handle_message.html', message=new_message)

@app.route("/", methods=['GET'])
def htmlForm():
    data = list(container.read_all_items(max_item_count=10))  # Fetch data from Cosmos DB
    return render_template('home.html', messages=data)

if __name__ == "__main__":
    app.run(debug=True)
