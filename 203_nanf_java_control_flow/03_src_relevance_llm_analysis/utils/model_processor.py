"""
Model processing utilities for vulnerability function localization.

This module handles processing models, including tracking progress and
managing the processing of individual entries.

"""

import logging
from colorama import Fore
from tqdm import tqdm

from .data_handler import (
    is_model_completed, find_resume_point, write_to_json
)
from .llm_processor import (
    extract_fields, generate_prompt, interact_with_llm
)


def process_model(model_name, ori_json_data, config):
    """
    Process all entries for a specific model.
    
    Args:
        model_name (str): Name of the model to process
        ori_json_data (list): Original JSON data to process
        config (dict): Configuration parameters
        
    Returns:
        bool: True if processing completed successfully
    """
    total_entries = len(ori_json_data)
    result_dir = config['output']['result_dir']
    
    # Skip if model has completed all entries
    if is_model_completed(model_name, ori_json_data, result_dir):
        logging.info(f"{Fore.GREEN}Skipping {model_name} - already completed all {total_entries} entries")
        return True
    
    # Find resume point
    start_idx = find_resume_point(model_name, ori_json_data, result_dir)
    remaining = total_entries - start_idx
    
    logging.info(f"{Fore.BLUE}Resuming {model_name} from index {start_idx}/{total_entries} "
                f"({remaining} entries remaining)")
    
    # Process remaining entries with progress bar
    with tqdm(total=remaining, desc=f"Processing {model_name}", 
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
        
        for idx, entry in enumerate(ori_json_data[start_idx:], start=start_idx):
            try:
                code, filename, entry_id, sub_id, code_id = extract_fields(entry)
                percent_complete = ((idx+1)/total_entries*100)
                
                # Detailed progress logging
                logging.info(f"Processing {model_name} - Progress: {idx+1}/{total_entries} "
                           f"({percent_complete:.2f}%) "
                           f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}")
                
                # Generate prompt and interact with LLM
                custom_prompt = generate_prompt(code, filename)
                new_entry = interact_with_llm(entry, custom_prompt, model_name, config)
                write_to_json(new_entry, model_name, result_dir)
                
                # Update progress bar
                pbar.update(1)
                
            except Exception as e:
                logging.error(
                    f"{Fore.RED}Failed processing {model_name} - Index: {idx+1}/{total_entries} "
                    f"- ID: {entry_id}, Sub_ID: {sub_id}, Code_ID: {code_id}: {e}"
                )
                continue
    
    # Check if we've completed all entries
    if is_model_completed(model_name, ori_json_data, result_dir):
        logging.info(f"{Fore.GREEN}Completed processing all entries for {model_name}")
        return True
    else:
        logging.warning(f"{Fore.YELLOW}Processing for {model_name} is incomplete. Run again to continue.")
        return False
