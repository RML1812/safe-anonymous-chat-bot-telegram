import torch
from PIL import Image
from transformers import BertTokenizer, pipeline

# Load the model and tokenizer for text detection
model_path = "model-creation/model-export"
bert_model = torch.load(f"{model_path}/model.pth")
tokenizer = BertTokenizer.from_pretrained(model_path)
bert_model.eval()  # Set model to evaluation mode

# Initialize the NSFW detector model
nsfw_model = pipeline("image-classification", model="Falconsai/nsfw_image_detection")


def predict_toxic_text(text: str, threshold=0.7) -> bool:
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


def predict_toxic_image(image: any) -> bool:
    try:
        # Check if parameter is already an instance of Image.Image
        if not isinstance(image, Image.Image):
            image = Image.open(image)

        # Perform NSFW detection on the image
        predictions = nsfw_model(image)

        for prediction in predictions:
            # Check if the label is 'nsfw' and extract the score
            if prediction["label"] == "nsfw":
                nsfw_score = prediction["score"]

                # If the 'nsfw' score exceeds the threshold, consider it NSFW
                if nsfw_score > 0.7:
                    return True

    except Exception as e:
        print(f"Error processing image: {e}")

    return False
