from google import genai
from io import BytesIO
from PIL import Image, ImageEnhance
import base64
from typing import Optional


class ImageTranscriber:
    """
    Handles transcription of handwritten math from images to LaTeX/Markdown format.
    Includes image preprocessing capabilities for better OCR results.
    """
    
    def __init__(self, client: genai.Client):
        """
        Initialize the image transcriber.
        
        Args:
            client: The Gemini AI client instance
        """
        self.client = client
    
    async def transcribe(self, image_file, text_fallback: Optional[str] = None, enhance: bool = True) -> str:
        """
        Transcribes handwritten math with optional image preprocessing.
        
        Args:
            image_file: The image file to transcribe
            text_fallback: Optional fallback text if transcription fails
            enhance: Whether to enhance contrast and sharpness
            
        Returns:
            Transcribed text in LaTeX/Markdown format
            
        Raises:
            ValueError: If image_file is None and no text_fallback is provided
            Exception: If transcription fails
        """
        if not image_file:
            if text_fallback:
                return text_fallback
            raise ValueError('You must input at least an image or text')
        
        try:
            # Open the image using the PIL library
            image = Image.open(image_file)

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Enhance image for better OCR
            if enhance:
                # Increase contrast
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.5)

                # Increase sharpness
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(2.0)

            # Convert image to Bytes
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=95)
            image_bytes = buffer.getvalue()

            # Encode to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Add the images for OCR
            prompt_parts = [
                {
                    'text': 'Transcribe the handwritten maths in this image to LaTex/Markdown.' 
                    'Return ONLY the text, no explanations.'
                },
                {
                    'inline_data': {
                        'mime_type': 'image/jpeg',
                        'data': image_base64
                    }
                }
            ]

            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents={'parts': prompt_parts}
            )
            
            # Return transcribed text or fallback to text_fallback
            return response.text if response.text else (text_fallback or "")
        
        except Exception as e:
            raise Exception(f'Error {str(e)} occurred during transcription')