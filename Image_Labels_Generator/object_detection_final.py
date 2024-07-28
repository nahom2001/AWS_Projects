import boto3
import json
import matplotlib.pyplot as plt
from PIL import Image
import io
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class AWSImageProcessor:
    def __init__(self, region_name):
        self.region_name = region_name
        self.rekognition_client = boto3.client('rekognition', region_name=self.region_name)
        self.s3_client = boto3.client('s3', region_name=self.region_name)

    def detect_labels(self, bucket_name, object_key):
        """Detects labels in an image stored in S3."""
        try:
            response = self.rekognition_client.detect_labels(
                Image={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': object_key
                    }
                },
                MaxLabels=10,
                MinConfidence=70
            )
            return response.get('Labels', [])
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return []

    def fetch_image(self, bucket_name, object_key):
        """Fetches the image from S3."""
        try:
            s3_response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            image_data = s3_response['Body'].read()
            return Image.open(io.BytesIO(image_data))
        except Exception as e:
            print(f"Error fetching image: {str(e)}")
            return None

    def save_labeled_image(self, image, labels, output_path):
        """Saves the image with bounding boxes and labels."""
        plt.figure(figsize=(12, 8))
        plt.imshow(image)
        ax = plt.gca()

        for label in labels:
            for instance in label.get('Instances', []):
                box = instance['BoundingBox']
                left = box['Left'] * image.width
                top = box['Top'] * image.height
                width = box['Width'] * image.width
                height = box['Height'] * image.height

                rect = plt.Rectangle((left, top), width, height, edgecolor='red', facecolor='none', linewidth=2)
                ax.add_patch(rect)
                ax.text(left, top - 10, f"{label['Name']} ({label['Confidence']:.2f}%)", fontsize=10, color='black',
                        bbox=dict(facecolor='white', alpha=0.5))

        plt.axis('off')
        plt.savefig(output_path, bbox_inches='tight')
        print(f"Image saved as {output_path}")

    def save_metadata(self, labels, output_path):
        """Saves the metadata to a text file."""
        metadata_list = []
        for label in labels:
            for instance in label.get('Instances', []):
                box = instance['BoundingBox']
                metadata_list.append({
                    'Name': label['Name'],
                    'Confidence': label['Confidence'],
                    'BoundingBox': {
                        'Left': box['Left'] * 100,  # Percent
                        'Top': box['Top'] * 100,
                        'Width': box['Width'] * 100,
                        'Height': box['Height'] * 100
                    }
                })
        with open(output_path, 'w') as file:
            json.dump(metadata_list, file, indent=4)
        print(f"Metadata saved as {output_path}")

    def get_timestamped_filenames(self, base_filename):
        """Generates a timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_filename}_{timestamp}"

# Example usage
if __name__ == "__main__":
    # Initialize AWSImageProcessor without hardcoded credentials
    aws_processor = AWSImageProcessor(region_name="us-east-1")

    bucket_name = "firstprojectreko"
    image_key = "good_image.jpg"
    
    base_filename = image_key.rsplit('.', 1)[0]  # Use image key without extension

    timestamped_image_filename = aws_processor.get_timestamped_filenames(base_filename) + ".png"
    timestamped_metadata_filename = aws_processor.get_timestamped_filenames(base_filename) + ".txt"

    labels = aws_processor.detect_labels(bucket_name, image_key)
    image = aws_processor.fetch_image(bucket_name, image_key)
    
    if image:
        aws_processor.save_labeled_image(image, labels, timestamped_image_filename)
        aws_processor.save_metadata(labels, timestamped_metadata_filename)
