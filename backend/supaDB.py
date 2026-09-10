import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Optional, Dict, Any
import json

class SupaDB:
    def __init__(self, client: Optional[Client] = None):
        """Initialize the Supabase client with credentials from environment variables or use provided client"""
        if client is None:
            load_dotenv()
            # Credentials come from the environment only. A service_role key
            # was previously hardcoded here; it bypasses row-level security,
            # is in git history, and needs rotating. See docs/deployment.md.
            self.SUPABASE_URL = os.environ.get("SUPABASE_URL")
            self.SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

            if not self.SUPABASE_URL or not self.SUPABASE_KEY:
                raise ValueError(
                    "Missing Supabase credentials. Set SUPABASE_URL and "
                    "SUPABASE_SERVICE_KEY in the environment or backend/.env"
                )


            self.client: Client = create_client(
                self.SUPABASE_URL, 
                self.SUPABASE_KEY
            )
        else:
            self.client = client
    
    def create_empty_job(self, user_id=None) -> str:
        """
        Creates an empty row in the job table and returns its ID.
        Optionally links the job to a user_id.
        """
        try:
            timestamp = datetime.now().isoformat()
            insert_data = {
                'created_at': timestamp,
                'videoAddress': "",
                'result': {},
                'total value': 0.0,
                'numItems': 0,
                'status': 'pending'
            }
            if user_id:
                insert_data['user_id'] = user_id
            response = self.client.from_('job').insert(insert_data).execute()
            if hasattr(response, 'data') and response.data:
                return response.data[0].get('id')
            else:
                raise Exception("Failed to create job row")
        except Exception as e:
            print(f"Error creating empty job: {str(e)}")
            raise

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches a job from the database by its ID.
        
        Args:
            job_id (str): The ID of the job to fetch
            
        Returns:
            Optional[Dict[str, Any]]: The job data if found, None otherwise
        """
        try:
            response = self.client.from_('job').select('*').eq('id', job_id).execute()
            
            if hasattr(response, 'data') and response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            print(f"Error fetching job {job_id}: {str(e)}")
            raise

    def update_job_status(self, job_id: str, status: str, result: Optional[Dict] = None) -> bool:
        """
        Updates the status and optionally the result of a job.
        
        Args:
            job_id (str): The ID of the job to update
            status (str): The new status ('pending', 'processing', 'completed', 'failed')
            result (Optional[Dict]): The result data to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            update_data = {'status': status}
            if result is not None:
                update_data['result'] = result
                
            response = self.client.from_('job').update(update_data).eq('id', job_id).execute()
            return bool(response.data)
            
        except Exception as e:
            print(f"Error updating job {job_id}: {str(e)}")
            raise

    def update_job_result(self, job_id: str, result: Dict[str, Any]) -> bool:
        """
        Updates the result column of a job with new data.
        
        Args:
            job_id (str): The ID of the job to update
            result (Dict[str, Any]): The new result data to store
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            response = self.client.from_('job').update({
                'result': result
            }).eq('id', job_id).execute()
            
            return bool(response.data)
            
        except Exception as e:
            print(f"Error updating job result for {job_id}: {str(e)}")
            raise

    def complete_job(self, job_id: str, total_value: float, num_items: int, result: Dict[str, Any]) -> bool:
        """
        Completes a job by updating its metrics, result, and status in a single call.
        
        Args:
            job_id (str): The ID of the job to update
            total_value (float): The total value of all items
            num_items (int): The number of items
            result (Dict[str, Any]): The result data to store
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            response = self.client.from_('job').update({
                'total value': total_value,
                'numItems': num_items,
                'result': result,
                'status': 'completed'
            }).eq('id', job_id).execute()
            
            return bool(response.data)
            
        except Exception as e:
            print(f"Error completing job {job_id}: {str(e)}")
            raise

    def update_video_address(self, job_id: str, public_url: str) -> bool:
        """
        Updates the video address for a job.
        
        Args:
            job_id (str): The ID of the job to update
            public_url (str): The public URL of the video
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            response = self.client.from_('job').update({
                'videoAddress': public_url
            }).eq('id', job_id).execute()
            
            return bool(response.data)
            
        except Exception as e:
            print(f"Error updating video address for job {job_id}: {str(e)}")
            raise
