#!/usr/bin/env python3
"""
S3-Guardian: Containerized Schedule-Driven Backup Sidecar
A microservice that automatically backs up data volumes to S3.
I hope you enjoy!
"""

import os
import sys
import time
import tarfile
import logging
from datetime import datetime
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import schedule

# Configure logging for simplicity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('S3-Guardian')


class S3Guardian:
    """Main backup system"""
    
    def __init__(self):
        """Initialize with environment variables set in .env"""
        self.validate_environment()
        
        # S3 Configuration
        self.s3_bucket = os.getenv('S3_BUCKET')
        self.s3_prefix = os.getenv('S3_PREFIX', 'backups')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.s3_endpoint_url = os.gentenv('S3_ENDPOINT_URL')
        
        # Backup Configuration
        self.target_path = Path(os.getenv('TARGET_PATH'))
        self.backup_name = os.getenv('BACKUP_NAME', self.target_path.name)
        self.backup_interval = os.getenv('BACKUP_INTERVAL', '6h')
        self.retention_days = int(os.getenv('RETENTION_DAYS', '30'))
        self.compression_level = int(os.getenv('COMPRESSION_LEVEL', '6'))
        
        # Temporary directory for staging backups
        self.temp_dir = Path('/tmp/s3-guardian')
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            region_name=self.aws_region,
            endpoint_url=self.s3_endpoint_url,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        logger.info(f"S3-Guardian initialized")
        logger.info(f"Target: {self.target_path}")
        logger.info(f"S3 Bucket: {self.s3_bucket}/{self.s3_prefix}")
        logger.info(f"Interval: {self.backup_interval}")
        logger.info(f"Retention: {self.retention_days} days")
    
    def validate_environment(self):
        """Validate required environment variables"""
        required_vars = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'S3_BUCKET',
            'TARGET_PATH',
            'S3_ENDPOINT_URL',
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            sys.exit(1)
        
        target_path = Path(os.getenv('TARGET_PATH'))
        if not target_path.exists():
            logger.error(f"Target path does not exist: {target_path}")
            sys.exit(1)
    
    def compress_directory(self, source_path: Path, output_file: Path) -> bool:
        """
        Compress a directory into a tar.gz file
        
        Args:
            source_path: Path to compress
            output_file: Output .tar.gz file path
            
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Compressing {source_path} to {output_file}")
            
            with tarfile.open(output_file, f'w:gz', compresslevel=self.compression_level) as tar:
                tar.add(source_path, arcname=source_path.name)
            
            file_size_mb = output_file.stat().st_size / (1024 * 1024)
            logger.info(f"Compression complete. Size: {file_size_mb:.2f} MB")
            return True
            
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return False
    
    def upload_to_s3(self, file_path: Path, s3_key: str) -> bool:
        """
        Upload a file to S3 with progress tracking
        
        Args:
            file_path: Local file to upload
            s3_key: S3 object key
            
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Uploading {file_path.name} to s3://{self.s3_bucket}/{s3_key}")
            
            file_size = file_path.stat().st_size
            
            # Upload with metadata
            extra_args = {
                'Metadata': {
                    'backup-name': self.backup_name,
                    'source-path': str(self.target_path),
                    'timestamp': datetime.utcnow().isoformat(),
                }
            }
            
            self.s3_client.upload_file(
                str(file_path),
                self.s3_bucket,
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Upload complete: {file_size / (1024 * 1024):.2f} MB")
            return True
            
        except NoCredentialsError:
            logger.error("AWS credentials not found or invalid")
            return False
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            return False
    
    def cleanup_temp_files(self, file_path: Path):
        """Remove temporary backup file"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period from S3"""
        try:
            logger.info(f"Checking for backups older than {self.retention_days} days")
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=f"{self.s3_prefix}/{self.backup_name}/"
            )
            
            if 'Contents' not in response:
                logger.info("No backups found for cleanup")
                return
            
            cutoff_time = datetime.utcnow().timestamp() - (self.retention_days * 86400)
            deleted_count = 0
            
            for obj in response['Contents']:
                if obj['LastModified'].timestamp() < cutoff_time:
                    self.s3_client.delete_object(
                        Bucket=self.s3_bucket,
                        Key=obj['Key']
                    )
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {obj['Key']}")
            
            if deleted_count > 0:
                logger.info(f"Cleanup complete: {deleted_count} old backups removed")
            else:
                logger.info("No old backups to remove")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def perform_backup(self):
        """Execute the complete backup workflow"""
        logger.info("=" * 60)
        logger.info("Starting backup process")
        logger.info("=" * 60)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{self.backup_name}_{timestamp}.tar.gz"
        temp_file = self.temp_dir / backup_filename
        s3_key = f"{self.s3_prefix}/{self.backup_name}/{backup_filename}"
        
        try:
            # Step 1: Compress
            if not self.compress_directory(self.target_path, temp_file):
                logger.error("Backup failed at compression stage")
                return False
            
            # Step 2: Upload to S3
            if not self.upload_to_s3(temp_file, s3_key):
                logger.error("Backup failed at upload stage")
                return False
            
            # Step 3: Cleanup temporary file
            self.cleanup_temp_files(temp_file)
            
            # Step 4: Remove old backups
            self.cleanup_old_backups()
            
            logger.info("=" * 60)
            logger.info("Backup completed successfully")
            logger.info(f"Backup location: s3://{self.s3_bucket}/{s3_key}")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            self.cleanup_temp_files(temp_file)
            return False
    
    def parse_interval(self, interval_str: str) -> dict:
        """
        Parse interval string (e.g., '6h', '30m', '1d') into schedule parameters
        
        Args:
            interval_str: Interval string
            
        Returns:
            dict with 'unit' and 'value'
        """
        interval_str = interval_str.lower().strip()
        
        if interval_str.endswith('h'):
            return {'unit': 'hours', 'value': int(interval_str[:-1])}
        elif interval_str.endswith('m'):
            return {'unit': 'minutes', 'value': int(interval_str[:-1])}
        elif interval_str.endswith('d'):
            return {'unit': 'days', 'value': int(interval_str[:-1])}
        else:
            logger.error(f"Invalid interval format: {interval_str}")
            sys.exit(1)
    
    def run(self):
        """Start the backup scheduler"""
        logger.info("S3-Guardian starting up...")
        
        # Perform initial backup immediately
        logger.info("Performing initial backup...")
        self.perform_backup()
        
        # Schedule recurring backups
        interval = self.parse_interval(self.backup_interval)
        
        if interval['unit'] == 'hours':
            schedule.every(interval['value']).hours.do(self.perform_backup)
        elif interval['unit'] == 'minutes':
            schedule.every(interval['value']).minutes.do(self.perform_backup)
        elif interval['unit'] == 'days':
            schedule.every(interval['value']).days.do(self.perform_backup)
        
        logger.info(f"Scheduler configured: backup every {interval['value']} {interval['unit']}")
        logger.info("S3-Guardian is now running. Press Ctrl+C to stop.")
        
        # Run scheduler loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Shutdown signal received. Stopping S3-Guardian...")
            sys.exit(0)


def main():
    """Entry point"""
    guardian = S3Guardian()
    guardian.run()


if __name__ == '__main__':
    main()
