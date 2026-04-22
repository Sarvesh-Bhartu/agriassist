import os
import uuid
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

class SupabaseStorageService:
    def __init__(self):
        self.client: Optional[Client] = None
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
            try:
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
                print("✅ Supabase Storage initialized")
            except Exception as e:
                print(f"❌ Failed to initialize Supabase client: {e}")

    async def upload_file(self, bucket_name: str, file_data: bytes, file_name: str, content_type: str) -> Optional[str]:
        """
        Uploads a file to a Supabase bucket and returns the public URL.
        """
        if not self.client:
            print("⚠️ Supabase client not initialized. Falling back to None.")
            return None

        try:
            # Clean filename and prepend UUID to avoid collisions
            safe_filename = f"{uuid.uuid4().hex}_{file_name.replace(' ', '_')}"
            
            # Upload to Supabase
            response = self.client.storage.from_(bucket_name).upload(
                path=safe_filename,
                file=file_data,
                file_options={"content-type": content_type}
            )
            
            # Get Public URL
            # Note: The bucket must be PUBLIC for this to work without signed URLs
            public_url = self.client.storage.from_(bucket_name).get_public_url(safe_filename)
            return public_url
            
        except Exception as e:
            print(f"❌ Supabase Upload Error: {e}")
            return None

storage_service = SupabaseStorageService()
