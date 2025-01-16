import io

import imageio.v3 as iio
import lottie
from PIL import Image
from telegram import Message
from telegram.ext import ContextTypes

from model_handler import predict_toxic_image, predict_toxic_text
from text_preprocess.text_preprocessing import preprocess_text


async def get_to_memory(context: ContextTypes.DEFAULT_TYPE, data) -> io.BytesIO:
    # Download file from bot, saving as BytesIO
    file = await context.bot.get_file(data)
    out = io.BytesIO()
    await file.download_to_memory(out)
    out.seek(0)

    return io.BytesIO(out.read())


async def predict_toxicity(context: ContextTypes.DEFAULT_TYPE, message: Message) -> bool:
    # Processing toxicity detection on message (text, gif, photo, sticker)
    if message.text:
        text = preprocess_text(message.text)
        return predict_toxic_text(text)

    if message.photo:

        if message.caption:
            text = preprocess_text(message.caption)

            if predict_toxic_text(text):
                return True

        for i, photo in enumerate(message.photo):
            if predict_toxic_image(await get_to_memory(context, photo)):
                return True

        return False
    
    if message.animation:
        file = await get_to_memory(context, message.animation)
        frame = iio.imread(file, extension=".mp4", index=0)
        image = Image.fromarray(frame)

        return predict_toxic_image(image)

    if message.sticker:
        sticker = message.sticker

        if message.sticker.is_animated:
            file = await get_to_memory(context, sticker)
            animation = lottie.parsers.tgs.parse_tgs(file)

            image = io.BytesIO()
            lottie.exporters.cairo.export_png(animation, image)
            image.seek(0)

            return predict_toxic_image(io.BytesIO(image.read()))

        elif message.sticker.is_video:
            file = await get_to_memory(context, sticker)
            frame = iio.imread(file, extension=".webm", index=0)
            image = Image.fromarray(frame)

            return predict_toxic_image(image)

        else:
            image = await get_to_memory(context, sticker)

            return predict_toxic_image(image)
