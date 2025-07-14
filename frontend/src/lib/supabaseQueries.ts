import { supabase } from '@/components/supabase';

/**
 * Fetches the latest job result from the job table
 * @returns The result column from the latest job, or null if no jobs exist
 */
export async function getLatestJobResult() {
  try {
    const { data, error } = await supabase
      .from('job')
      .select('result')
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
    
    if (error) {
      console.error('Error fetching latest job result:', error);
      return null;
    }
    
    return data?.result || null;
  } catch (error) {
    console.error('Exception fetching latest job result:', error);
    return null;
  }
}

/**
 * Fetches a job result by job ID
 * @param jobId The ID of the job to fetch
 * @returns The result column from the specified job, or null if not found
 */
export async function getJobResultById(jobId: string) {
  try {
    const { data, error } = await supabase
      .from('job')
      .select('result')
      .eq('id', jobId)
      .single();
    
    if (error) {
      console.error(`Error fetching job result for ID ${jobId}:`, error);
      return null;
    }
    
    return data?.result || null;
  } catch (error) {
    console.error(`Exception fetching job result for ID ${jobId}:`, error);
    return null;
  }
}

/**
 * Fetches results from multiple job IDs and combines them into a single result object
 * @param jobIds Array of job IDs to fetch results from
 * @returns Combined result object with all items from all jobs, or null if no results found
 */
export async function getMultipleJobResults(jobIds: string[]) {
  try {
    const { data, error } = await supabase
      .from('job')
      .select('result')
      .in('id', jobIds);
    
    if (error) {
      console.error('Error fetching multiple job results:', error);
      return null;
    }
    
    if (!data || data.length === 0) {
      console.log('No job results found for the provided IDs');
      return null;
    }
    
    // Combine all results into a single object
    const combinedResults: any = {};
    let itemCounter = 1;
    
    data.forEach((jobData, jobIndex) => {
      const result = jobData.result;
      if (result && typeof result === 'object') {
        // Add items from this job to the combined results
        Object.entries(result).forEach(([key, item]: [string, any]) => {
          // Create a unique key for each item to avoid conflicts
          const uniqueKey = `item_${itemCounter}`;
          combinedResults[uniqueKey] = {
            ...item,
            // Add metadata about which job this item came from
            source_job: jobIds[jobIndex],
            original_key: key
          };
          itemCounter++;
        });
      }
    });
    
    return combinedResults;
  } catch (error) {
    console.error('Exception fetching multiple job results:', error);
    return null;
  }
}

/**
 * Fetches all jobs for a given user from the backend API
 * @param userId The Supabase user ID
 * @returns Array of job objects or []
 */
export async function getUserJobs(userId: string) {
  try {
    const res = await fetch(`/api/user-jobs?user_id=${encodeURIComponent(userId)}`);
    const data = await res.json();
    if (data.status === 'success') {
      return data.jobs || [];
    } else {
      console.error('Error fetching user jobs:', data.error);
      return [];
    }
  } catch (error) {
    console.error('Exception fetching user jobs:', error);
    return [];
  }
}
