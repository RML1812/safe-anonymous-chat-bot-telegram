import torch
from transformers import BertTokenizer, BertForSequenceClassification

# Load the model and tokenizer
model_path = "model-creation/model-export"
model = BertForSequenceClassification.from_pretrained(model_path)
tokenizer = BertTokenizer.from_pretrained(model_path)
model.eval()  # Set model to evaluation mode

def predict_toxicity(text, threshold=0.5):
    """
    Predict whether the text is toxic.
    :param text: input text to analyze
    :param threshold: threshold for toxicity classification
    :return: True if toxic, False otherwise
    """
    inputs = tokenizer(text, padding=True, truncation=True, max_length=128, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        probabilities = torch.sigmoid(outputs.logits).squeeze().numpy()
        
    return any(prob >= threshold for prob in probabilities)  # Returns True if any category is above threshold