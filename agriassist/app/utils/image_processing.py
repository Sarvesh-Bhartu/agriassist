from PIL import Image
import io
from typing import Tuple


class ImageProcessor:
    """Image processing utilities"""
    
    MAX_SIZE = (1920, 1920)  # Max dimensions
    QUALITY = 85  # JPEG quality
    
    @staticmethod
    def compress_image(image_bytes: bytes) -> bytes:
        """Compress and resize image"""
        
        try:
            # Open image
            img = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if needed (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = rgb_img
            
            # Resize if needed
            img.thumbnail(ImageProcessor.MAX_SIZE, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=ImageProcessor.QUALITY, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            raise ValueError(f"Image processing failed: {str(e)}")
    
    @staticmethod
    def validate_image(image_bytes: bytes) -> Tuple[bool, str]:
        """Validate if bytes represent a valid image"""
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            
            # Check format
            if img.format not in ['JPEG', 'JPG', 'PNG', 'WEBP']:
                return False, "Unsupported image format. Use JPEG, PNG, or WEBP"
            
            return True, "Valid image"
            
        except Exception as e:
            return False, f"Invalid image: {str(e)}"
