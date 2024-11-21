import re
import os
import string
import json
import pandas as pd
import emoji
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# Load resources
# Load slang word dictionary
slang_path = os.path.join(os.path.dirname(__file__), "combined_slang_words.txt")
with open(slang_path, "r") as f:
    slang_dict = json.load(f)

# Load stop words
stop_words_path = os.path.join(os.path.dirname(__file__), "stopwordbahasa.csv")
stop_words = pd.read_csv(stop_words_path, header=None)[0].tolist()

# Initialize stemmer
factory = StemmerFactory()
stemmer = factory.create_stemmer()

# Functions for each preprocessing step

def lower_text(text):
    """Convert text to lowercase."""
    return text.lower()

def remove_url(text):
    """Remove URLs from the text."""
    return re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE)

def remove_punctuation(text):
    """Remove punctuation from the text."""
    return text.translate(str.maketrans("", "", string.punctuation))

def remove_hashtags(text):
    """Remove hashtags from the text."""
    return re.sub(r"#\w+", "", text)

def remove_whitespace(text):
    """Remove excessive whitespace from the text."""
    return " ".join(text.split())

def remove_encoded_text(text):
    """Remove encoded text formats like emojis and other encoded sequences."""
    return text.encode("ascii", "ignore").decode("ascii")

def remove_emoji(text):
    """Remove emojis from the text using the emoji library."""
    return emoji.replace_emoji(text, replace='')

def replace_slang_words(text, slang_dict):
    """Replace slang words in the text using the slang dictionary."""
    words = text.split()
    return " ".join([slang_dict[word] if word in slang_dict else word for word in words])

def remove_stop_words(text, stop_words):
    """Remove stop words from the text."""
    words = text.split()
    return " ".join([word for word in words if word not in stop_words])

def stem_text(text):
    """Stem the text using Sastrawi stemmer."""
    return stemmer.stem(text)

# Combine all steps into one function
def preprocess_text(text):
    """Perform all preprocessing steps on the given text."""
    text = lower_text(text)
    text = remove_url(text)
    text = remove_punctuation(text)
    text = remove_hashtags(text)
    text = remove_whitespace(text)
    text = remove_encoded_text(text)
    text = remove_emoji(text)
    text = replace_slang_words(text, slang_dict)
    text = remove_stop_words(text, stop_words)
    text = stem_text(text)
    return text
