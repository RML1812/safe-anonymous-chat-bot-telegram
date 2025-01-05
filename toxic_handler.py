from telegram import Message
from telegram.ext import ContextTypes
from text_preprocess.text_preprocessing import preprocess_text
from model_handler import predict_toxic_text, predict_toxic_photo
    
async def predict_toxicity(context: ContextTypes.DEFAULT_TYPE, message: Message):
    if message.text:
        text = preprocess_text(message.text)
        return predict_toxic_text(text)
    
    if message.photo:
        if message.caption:
            text = preprocess_text(message.caption)
            if predict_toxic_text(text):
                return True
        
        return await predict_toxic_photo(context, message)
        
        
        