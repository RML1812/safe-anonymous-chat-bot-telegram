import torch
from PIL import Image
from transformers import BertTokenizer, pipeline

# Load the model and tokenizer for text detection
model_path = "model-creation/model-export"
bert_model = torch.load(f"{model_path}/model.pth")
tokenizer = BertTokenizer.from_pretrained(model_path)
bert_model.eval()  # Set model to evaluation mode

# Define category labels and their respective thresholds
category_columns = ['Hate Speech', 'Abusive Speech', 'SARA', 'Radicalism', 'Defamation']
thresholds = {
    'Hate Speech': 0.25,
    'Abusive Speech': 0.30,
    'SARA': 0.60,
    'Radicalism': 0.50,
    'Defamation': 0.20
}

# Initialize the NSFW detector model
nsfw_model = pipeline("image-classification", model="Falconsai/nsfw_image_detection")


def predict_toxic_text(text: str) -> bool:
    """
    Predict whether the text is toxic using category-specific thresholds.
    :param text: input text to analyze
    :return: True if toxic in any category, False otherwise
    """
    inputs = tokenizer(
        text, padding=True, truncation=True, max_length=128, return_tensors="pt"
    )
    with torch.no_grad():
        outputs = bert_model(**inputs)
        probabilities = torch.sigmoid(outputs.logits).squeeze().numpy()

    # Apply category-specific thresholds
    for i, prob in enumerate(probabilities):
        category = category_columns[i]
        if prob >= thresholds[category]:
            return True
    return False


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
