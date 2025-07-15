#!/usr/bin/env python3
"""
job_utils.py

Shared utilities for Heroku scheduled jobs:
- Email notifications for failures
- Job duration monitoring
- Data validation and fallback
- Weekly scheduling logic
"""

import os
import sys
import time
import smtplib
import logging
import datetime
import traceback
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from functools import wraps
from typing import Optional, Dict, Any, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('job_logs.log', mode='a')
    ]
)

class JobMonitor:
    """Monitor job execution with error handling, timing, and notifications."""
    
    def __init__(self, job_name: str, email_recipient: str = None):
        self.job_name = job_name
        # Default email if not provided and not in environment
        self.email_recipient = (
            email_recipient or 
            os.getenv('NOTIFICATION_EMAIL') or 
            'yourcovidrisk@gmail.com'
        )
        self.logger = logging.getLogger(f'job.{job_name}')
        self.start_time = None
        self.duration = None
        
    def should_run_weekly(self, target_weekday: int = 0) -> bool:
        """
        Check if job should run today based on weekly schedule.
        
        Args:
            target_weekday: Day of week to run (0=Monday, 6=Sunday)
        
        Returns:
            True if today is the target weekday, False otherwise
        """
        today = datetime.date.today()
        is_target_day = today.weekday() == target_weekday
        
        self.logger.info(f"Weekly schedule check: Today is {today.strftime('%A')} "
                        f"(weekday {today.weekday()}), target is weekday {target_weekday}")
        
        if not is_target_day:
            self.logger.info(f"Skipping {self.job_name} - not scheduled for today")
            
        return is_target_day
    
    def send_failure_email(self, error_message: str, traceback_str: str = None):
        """Send email notification for job failure."""
        if not self.email_recipient:
            self.logger.warning("No email recipient configured for notifications")
            return
            
        try:
            # Use Gmail SMTP configuration
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USER', 'yourcovidrisk@gmail.com')
            smtp_pass = os.getenv('SMTP_PASS')
            
            if not smtp_user or not smtp_pass:
                self.logger.error("SMTP credentials not configured")
                return
                
            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = self.email_recipient
            msg['Subject'] = f"🚨 COVID Risk Job Failure: {self.job_name}"
            
            duration_text = f"{self.duration:.2f} seconds" if self.duration is not None else "Not completed"
            body = f"""
Job: {self.job_name}
Status: FAILED
Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Duration: {duration_text}

Error Message:
{error_message}

Traceback:
{traceback_str or 'Not available'}

Please check the Heroku logs for more details:
heroku logs --app mycovidrisk --source app
            """.strip()
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                
            self.logger.info(f"Failure notification sent to {self.email_recipient}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
    
    def send_success_email(self, summary: str = None):
        """Send email notification for job success."""
        if not self.email_recipient:
            return
            
        # Skip success emails only if explicitly disabled
        if os.getenv('SEND_SUCCESS_EMAILS', 'true').lower() in ['false', '0', 'no']:
            return
            
        try:
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.sendgrid.net')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SENDGRID_USERNAME') or os.getenv('SMTP_USER')
            smtp_pass = os.getenv('SENDGRID_PASSWORD') or os.getenv('SMTP_PASS')
            
            if not smtp_user or not smtp_pass:
                return
                
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = self.email_recipient
            msg['Subject'] = f"✅ COVID Risk Job Success: {self.job_name}"
            
            duration_text = f"{self.duration:.2f} seconds" if self.duration is not None else "Unknown duration"
            body = f"""
Job: {self.job_name}
Status: SUCCESS
Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Duration: {duration_text}

{summary or 'Job completed successfully.'}
            """.strip()
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                
        except Exception as e:
            self.logger.error(f"Failed to send success email: {e}")

def monitored_job(job_name: str, 
                  weekly_schedule: bool = False, 
                  target_weekday: int = 0,
                  max_duration_minutes: int = 30,
                  email_recipient: str = None):
    """
    Decorator for monitoring scheduled jobs.
    
    Args:
        job_name: Name of the job for logging/notifications
        weekly_schedule: If True, only run on target weekday
        target_weekday: Day of week to run (0=Monday, 6=Sunday)
        max_duration_minutes: Maximum expected duration before warning
        email_recipient: Email for notifications (overrides env var)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = JobMonitor(job_name, email_recipient)
            
            # Check weekly schedule if enabled
            if weekly_schedule and not monitor.should_run_weekly(target_weekday):
                return
            
            monitor.logger.info(f"Starting {job_name}")
            monitor.start_time = time.time()
            
            try:
                # Execute the job
                result = func(*args, **kwargs)
                
                # Calculate duration
                monitor.duration = time.time() - monitor.start_time
                
                # Check if duration is unusually long
                if monitor.duration > (max_duration_minutes * 60):
                    monitor.logger.warning(f"Job took {monitor.duration:.2f}s "
                                         f"(>{max_duration_minutes}m)")
                
                monitor.logger.info(f"Job completed successfully in {monitor.duration:.2f}s")
                
                # Send success notification if configured
                summary = f"Duration: {monitor.duration:.2f} seconds"
                if hasattr(result, 'get') and isinstance(result, dict):
                    summary += f"\nResult: {result}"
                    
                monitor.send_success_email(summary)
                
                return result
                
            except Exception as e:
                # Calculate duration even for failures
                monitor.duration = time.time() - monitor.start_time
                
                error_msg = str(e)
                tb_str = traceback.format_exc()
                
                monitor.logger.error(f"Job failed after {monitor.duration:.2f}s: {error_msg}")
                monitor.logger.error(f"Traceback:\n{tb_str}")
                
                # Send failure notification
                monitor.send_failure_email(error_msg, tb_str)
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator

class DataValidator:
    """Validate data updates and implement fallback mechanisms."""
    
    @staticmethod
    def validate_csv_file(file_path: str, 
                         required_columns: list = None,
                         min_rows: int = 1,
                         max_change_percent: float = 50.0) -> Dict[str, Any]:
        """
        Validate a CSV file for basic sanity checks.
        
        Args:
            file_path: Path to CSV file
            required_columns: List of required column names
            min_rows: Minimum number of data rows expected
            max_change_percent: Maximum percentage change from previous version
            
        Returns:
            Dictionary with validation results
        """
        import csv
        import pandas as pd
        
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        if not os.path.exists(file_path):
            result['valid'] = False
            result['errors'].append(f"File does not exist: {file_path}")
            return result
        
        try:
            # Read CSV
            df = pd.read_csv(file_path)
            result['stats']['rows'] = len(df)
            result['stats']['columns'] = list(df.columns)
            
            # Check minimum rows
            if len(df) < min_rows:
                result['valid'] = False
                result['errors'].append(f"Too few rows: {len(df)} < {min_rows}")
            
            # Check required columns
            if required_columns:
                missing_cols = set(required_columns) - set(df.columns)
                if missing_cols:
                    result['valid'] = False
                    result['errors'].append(f"Missing columns: {missing_cols}")
            
            # Check for completely empty data
            if df.empty or df.isnull().all().all():
                result['valid'] = False
                result['errors'].append("File contains no valid data")
            
            # Compare with previous version if exists
            prev_file = file_path.replace('_current.csv', '_previous.csv')
            if os.path.exists(prev_file):
                try:
                    prev_df = pd.read_csv(prev_file)
                    
                    # Compare row counts
                    if len(prev_df) > 0:
                        change_percent = abs(len(df) - len(prev_df)) / len(prev_df) * 100
                        if change_percent > max_change_percent:
                            result['warnings'].append(
                                f"Large change in row count: {change_percent:.1f}%"
                            )
                    
                    # Compare numeric columns for dramatic changes
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    for col in numeric_cols:
                        if col in prev_df.columns:
                            old_mean = prev_df[col].mean()
                            new_mean = df[col].mean()
                            if old_mean != 0:
                                change = abs(new_mean - old_mean) / abs(old_mean) * 100
                                if change > max_change_percent:
                                    result['warnings'].append(
                                        f"Large change in {col}: {change:.1f}%"
                                    )
                
                except Exception as e:
                    result['warnings'].append(f"Could not compare with previous: {e}")
            
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Error reading CSV: {e}")
        
        return result
    
    @staticmethod
    def backup_and_fallback(file_path: str, backup_days: int = 7) -> bool:
        """
        Create backup and implement fallback if current file is invalid.
        
        Args:
            file_path: Path to file to backup/restore
            backup_days: Number of days of backups to keep
            
        Returns:
            True if fallback was used, False if current file is OK
        """
        if not os.path.exists(file_path):
            return False
        
        # Create backup directory
        backup_dir = os.path.join(os.path.dirname(file_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamped backup
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.basename(file_path)
        backup_path = os.path.join(backup_dir, f"{timestamp}_{base_name}")
        
        try:
            import shutil
            shutil.copy2(file_path, backup_path)
            
            # Clean old backups
            import glob
            pattern = os.path.join(backup_dir, f"*_{base_name}")
            backups = sorted(glob.glob(pattern))
            
            # Keep only recent backups
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=backup_days)
            
            for backup in backups[:-10]:  # Always keep at least 10 most recent
                try:
                    backup_time = datetime.datetime.strptime(
                        os.path.basename(backup).split('_')[0], '%Y%m%d'
                    )
                    if backup_time < cutoff_date:
                        os.remove(backup)
                except:
                    pass  # Skip if can't parse date
            
            return False  # No fallback needed, backup created successfully
            
        except Exception as e:
            logging.error(f"Error creating backup: {e}")
            return False