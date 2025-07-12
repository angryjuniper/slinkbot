"""
Background task implementations for SlinkBot.
"""

from typing import Dict, Any

from managers.request_manager import RequestManager
from managers.health_manager import HealthManager
from notifications.status_notifier import StatusNotifier
from utils.logging_config import get_logger

logger = get_logger(__name__)


class BackgroundTasks:
    """Container for all background task implementations."""
    
    def __init__(self, 
                 request_manager: RequestManager,
                 health_manager: HealthManager,
                 status_notifier: StatusNotifier):
        """
        Initialize background tasks.
        
        Args:
            request_manager: RequestManager instance
            health_manager: HealthManager instance
            status_notifier: StatusNotifier instance
        """
        self.request_manager = request_manager
        self.health_manager = health_manager
        self.status_notifier = status_notifier
    
    async def check_request_updates(self):
        """Check for request status updates and send notifications."""
        try:
            logger.debug("Checking for request status updates")
            updates = await self.request_manager.check_request_updates()
            
            if updates:
                logger.info(f"Found {len(updates)} request updates")
                await self.status_notifier.send_status_updates(updates)
                
                # Send completion summary if there are any completed requests
                completed_requests = [
                    update['tracked_request'] for update in updates 
                    if update['new_status'] == 5  # Available
                ]
                
                if completed_requests:
                    await self.status_notifier.send_request_completion_summary(completed_requests)
            else:
                logger.debug("No request updates found")
                
        except Exception as e:
            logger.error(f"Error checking request updates: {e}")
            raise
    
    async def health_check_services(self):
        """Perform health checks on all services."""
        try:
            logger.debug("Performing service health checks")
            health_status = await self.health_manager.check_all_services()
            
            # Log overall health status
            healthy_services = sum(1 for status in health_status.values() if status)
            total_services = len(health_status)
            logger.info(f"Service health check complete: {healthy_services}/{total_services} healthy")
            
            # Send alerts for services that need them
            services_needing_alerts = await self.health_manager.get_services_needing_alerts()
            
            for service_health in services_needing_alerts:
                await self.status_notifier.send_health_alert(
                    service_health.service_name,
                    service_health.is_healthy,
                    service_health.last_error
                )
            
            # Send periodic health summary (e.g., once per hour)
            # This could be enhanced to only send summaries at specific intervals
            if total_services > 0 and healthy_services < total_services:
                health_summary = self.health_manager.get_service_status_summary()
                await self.status_notifier.send_batch_health_summary(health_summary)
                
        except Exception as e:
            logger.error(f"Error in health check task: {e}")
            raise
    
    async def process_failed_requests(self):
        """Process failed requests that are ready for retry."""
        try:
            logger.debug("Processing failed requests for retry")
            
            retry_stats = await self.request_manager.process_failed_requests()
            
            if retry_stats['retried'] > 0 or retry_stats['failed_again'] > 0:
                logger.info(f"Retry processing complete: {retry_stats['retried']} retried, "
                          f"{retry_stats['failed_again']} failed again, "
                          f"{retry_stats['max_failures_reached']} max failures reached")
            else:
                logger.debug("No failed requests to process")
                
        except Exception as e:
            logger.error(f"Error processing failed requests: {e}")
            raise
    
    async def cleanup_old_requests(self):
        """Clean up old inactive requests from database."""
        try:
            logger.debug("Cleaning up old requests")
            
            # Clean up requests older than 30 days
            deleted_count = self.request_manager.cleanup_old_requests(days=30)
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old requests")
            else:
                logger.debug("No old requests to clean up")
                
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            raise
    
    async def update_media_availability(self):
        """
        Check if requested media has become available.
        This is a placeholder for future integration with Radarr/Sonarr.
        """
        try:
            logger.debug("Checking media availability (placeholder)")
            
            # Future implementation would:
            # 1. Check Radarr/Sonarr for newly available media
            # 2. Match with pending requests
            # 3. Update request status accordingly
            # 4. Send notifications
            
            # For now, this is just a placeholder
            logger.debug("Media availability check completed (no action taken)")
            
        except Exception as e:
            logger.error(f"Error checking media availability: {e}")
            raise
    
    async def generate_periodic_reports(self):
        """Generate periodic reports and statistics."""
        try:
            logger.debug("Generating periodic reports")
            
            # Get request statistics
            request_stats = self.request_manager.get_request_statistics()
            health_stats = self.health_manager.get_health_statistics()
            
            logger.info(f"Request statistics: {request_stats}")
            logger.info(f"Health statistics: {health_stats}")
            
            # Future enhancement: Send these stats to a dedicated channel
            # or store them for analytics purposes
            
        except Exception as e:
            logger.error(f"Error generating reports: {e}")
            raise
    
    async def database_maintenance(self):
        """Perform database maintenance tasks."""
        try:
            logger.debug("Performing database maintenance")
            
            # Clean up old health records
            # This is a placeholder for more comprehensive maintenance
            self.health_manager.cleanup_old_health_records(days=90)
            
            # Future enhancements could include:
            # - VACUUM operations for SQLite
            # - Index optimization
            # - Backup creation
            # - Database statistics updates
            
            logger.debug("Database maintenance completed")
            
        except Exception as e:
            logger.error(f"Error in database maintenance: {e}")
            raise
    
    async def check_service_connectivity(self):
        """Check connectivity to external services without full health check."""
        try:
            logger.debug("Checking basic service connectivity")
            
            # This could be a lighter-weight check than full health monitoring
            # For example, just checking if services respond to ping
            
            # For now, we'll delegate to the health manager
            health_status = await self.health_manager.check_all_services()
            
            # Log any connectivity issues
            for service_name, is_healthy in health_status.items():
                if not is_healthy:
                    logger.warning(f"Service {service_name} connectivity issue detected")
            
        except Exception as e:
            logger.error(f"Error checking service connectivity: {e}")
            raise
    
    async def sync_request_status(self):
        """
        Synchronize request status with external services.
        This ensures our database stays in sync even if we miss some updates.
        """
        try:
            logger.debug("Synchronizing request status")
            
            # Get all active requests and verify their status
            # This is more comprehensive than the regular update check
            active_requests = self.request_manager.get_requests_by_status(status=1, limit=100)  # Pending
            active_requests.extend(self.request_manager.get_requests_by_status(status=2, limit=100))  # Approved
            active_requests.extend(self.request_manager.get_requests_by_status(status=3, limit=100))  # Processing
            active_requests.extend(self.request_manager.get_requests_by_status(status=4, limit=100))  # Partial
            
            logger.info(f"Synchronizing status for {len(active_requests)} active requests")
            
            # This would be the same logic as check_request_updates but more comprehensive
            # For now, we'll delegate to the regular update check
            await self.check_request_updates()
            
        except Exception as e:
            logger.error(f"Error synchronizing request status: {e}")
            raise