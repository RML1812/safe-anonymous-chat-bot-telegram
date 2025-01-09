import io

import torch
from PIL import Image
from telegram import Message
from telegram.ext import ContextTypes
from transformers import BertTokenizer, pipeline

# Load the model and tokenizer for text detection
model_path = "model-creation/model-export"
bert_model = torch.load(f"{model_path}/model.pth")
tokenizer = BertTokenizer.from_pretrained(model_path)
bert_model.eval()  # Set model to evaluation mode

# Initialize the NSFW detector model
nsfw_model = pipeline("image-classification", model="Falconsai/nsfw_image_detection")


def predict_toxic_text(text, threshold=0.65):
    """
    Predict whether the text is toxic.
    :param text: input text to analyze
    :param threshold: threshold for toxicity classification
    :return: True if toxic, False otherwise
    """
    inputs = tokenizer(
        text, padding=True, truncation=True, max_length=128, return_tensors="pt"
    )
    with torch.no_grad():
        outputs = bert_model(**inputs)
        probabilities = torch.sigmoid(outputs.logits).squeeze().numpy()

    return any(
        prob >= threshold for prob in probabilities
    )  # Returns True if any category is above threshold


async def predict_toxic_photo(context: ContextTypes.DEFAULT_TYPE, message: Message):
    # Get each photo (sorted by resolution, smallest to largest)
    for i, photo in enumerate(message.photo):
        # Get and store a photo
        file = await context.bot.get_file(photo)
        out = io.BytesIO()
        await file.download_to_memory(out)
        out.seek(0)

        try:
            # Ensure the image is compatible and saved in JPEG format
            image = Image.open(io.BytesIO(out.read()))

            # Perform NSFW detection on the image
            predictions = nsfw_model(image)

            for prediction in predictions:
                # Check if the label is 'nsfw' and extract the score
                if prediction["label"] == "nsfw":
                    nsfw_score = prediction["score"]

                    # If the 'nsfw' score exceeds the threshold, consider it NSFW
                    if nsfw_score > 0.65:
                        return True

        except Exception as e:
            print(f"Error processing image: {e}")

    return False
