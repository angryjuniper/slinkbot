"""
Health Manager for monitoring service health and alerting.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from database.models import ServiceHealth, get_db
from services.base import BaseService
from utils.logging_config import get_logger

logger = get_logger(__name__)


class HealthManager:
    """Manages service health monitoring and alerting."""
    
    def __init__(self, services: Dict[str, BaseService]):
        """
        Initialize health manager.
        
        Args:
            services: Dictionary of service name -> service instance
        """
        self.services = services
        self.alert_cooldown = timedelta(hours=1)  # Minimum time between alerts
        self.health_check_timeout = 10  # seconds
    
    async def check_all_services(self) -> Dict[str, bool]:
        """
        Check health of all monitored services.
        
        Returns:
            Dictionary of service name -> health status
        """
        health_status = {}
        
        logger.debug(f"Checking health of {len(self.services)} services")
        
        # Check all services concurrently
        tasks = []
        service_names = []
        
        for service_name, service in self.services.items():
            task = asyncio.create_task(self._check_single_service(service_name, service))
            tasks.append(task)
            service_names.append(service_name)
        
        # Wait for all health checks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for service_name, result in zip(service_names, results):
            if isinstance(result, Exception):
                logger.error(f"Health check exception for {service_name}: {result}")
                health_status[service_name] = False
                await self._update_service_health(service_name, False, str(result))
            else:
                health_status[service_name] = result
        
        # Log summary
        healthy_count = sum(1 for status in health_status.values() if status)
        total_count = len(health_status)
        logger.info(f"Service health check complete: {healthy_count}/{total_count} healthy")
        
        return health_status
    
    async def _check_single_service(self, service_name: str, service: BaseService) -> bool:
        """
        Check health of a single service.
        
        Args:
            service_name: Name of the service
            service: Service instance
            
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Use asyncio.wait_for to enforce timeout
            is_healthy = await asyncio.wait_for(
                service.health_check(),
                timeout=self.health_check_timeout
            )
            
            await self._update_service_health(service_name, is_healthy)
            return is_healthy
            
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for {service_name}")
            await self._update_service_health(service_name, False, "Health check timeout")
            return False
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            await self._update_service_health(service_name, False, str(e))
            return False
    
    async def _update_service_health(self, service_name: str, is_healthy: bool, 
                                   error_message: Optional[str] = None):
        """
        Update service health in database.
        
        Args:
            service_name: Name of the service
            is_healthy: Whether the service is healthy
            error_message: Optional error message if unhealthy
        """
        try:
            with next(get_db()) as session:
                # Get existing health record or create new one
                service_health = session.query(ServiceHealth).filter(
                    ServiceHealth.service_name == service_name
                ).first()
                
                current_time = datetime.utcnow()
                
                if not service_health:
                    # Create new health record
                    service_health = ServiceHealth(
                        service_name=service_name,
                        is_healthy=is_healthy,
                        last_check=current_time,
                        last_error=error_message,
                        error_count=0 if is_healthy else 1,
                        consecutive_failures=0 if is_healthy else 1,
                        last_success=current_time if is_healthy else None
                    )
                    session.add(service_health)
                else:
                    # Update existing record
                    was_healthy = service_health.is_healthy
                    service_health.is_healthy = is_healthy
                    service_health.last_check = current_time
                    
                    if is_healthy:
                        # Service is healthy
                        if not was_healthy:
                            logger.info(f"Service {service_name} recovered")
                        
                        service_health.consecutive_failures = 0
                        service_health.last_success = current_time
                        service_health.last_error = None
                    else:
                        # Service is unhealthy
                        if was_healthy:
                            logger.warning(f"Service {service_name} became unhealthy")
                        
                        service_health.error_count += 1
                        service_health.consecutive_failures += 1
                        service_health.last_error = error_message
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update service health for {service_name}: {e}")
    
    async def get_services_needing_alerts(self) -> List[ServiceHealth]:
        """
        Get services that need health alerts sent.
        
        Returns:
            List of ServiceHealth objects that need alerts
        """
        try:
            with next(get_db()) as session:
                cutoff_time = datetime.utcnow() - self.alert_cooldown
                
                # Find unhealthy services that haven't been alerted recently
                services = session.query(ServiceHealth).filter(
                    ServiceHealth.is_healthy == False,
                    ServiceHealth.consecutive_failures >= 3,  # Only alert after multiple failures
                    ServiceHealth.last_check >= cutoff_time  # Only recent failures
                ).all()
                
                # Filter out services that have been alerted too recently
                # This would be enhanced to track last alert time in a future version
                return services
                
        except Exception as e:
            logger.error(f"Failed to get services needing alerts: {e}")
            return []
    
    def get_service_status_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary of all service statuses.
        
        Returns:
            Dictionary of service summaries
        """
        try:
            with next(get_db()) as session:
                services = session.query(ServiceHealth).all()
                
                summary = {}
                for service in services:
                    summary[service.service_name] = {
                        'healthy': service.is_healthy,
                        'last_check': service.last_check,
                        'error_count': service.error_count,
                        'consecutive_failures': service.consecutive_failures,
                        'last_error': service.last_error,
                        'last_success': service.last_success
                    }
                
                return summary
                
        except Exception as e:
            logger.error(f"Failed to get service status summary: {e}")
            return {}
    
    def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """
        Get health status for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            ServiceHealth object if found, None otherwise
        """
        try:
            with next(get_db()) as session:
                return session.query(ServiceHealth).filter(
                    ServiceHealth.service_name == service_name
                ).first()
                
        except Exception as e:
            logger.error(f"Failed to get service health for {service_name}: {e}")
            return None
    
    def get_unhealthy_services(self) -> List[ServiceHealth]:
        """
        Get all currently unhealthy services.
        
        Returns:
            List of ServiceHealth objects for unhealthy services
        """
        try:
            with next(get_db()) as session:
                return session.query(ServiceHealth).filter(
                    ServiceHealth.is_healthy == False
                ).all()
                
        except Exception as e:
            logger.error(f"Failed to get unhealthy services: {e}")
            return []
    
    def get_health_statistics(self) -> Dict[str, Any]:
        """
        Get health monitoring statistics.
        
        Returns:
            Dictionary with health statistics
        """
        try:
            with next(get_db()) as session:
                total_services = session.query(ServiceHealth).count()
                healthy_services = session.query(ServiceHealth).filter(
                    ServiceHealth.is_healthy == True
                ).count()
                
                # Services with recent failures
                recent_failures = session.query(ServiceHealth).filter(
                    ServiceHealth.consecutive_failures > 0
                ).count()
                
                # Services that have never been healthy
                never_healthy = session.query(ServiceHealth).filter(
                    ServiceHealth.last_success.is_(None)
                ).count()
                
                return {
                    'total_services': total_services,
                    'healthy_services': healthy_services,
                    'unhealthy_services': total_services - healthy_services,
                    'services_with_recent_failures': recent_failures,
                    'services_never_healthy': never_healthy,
                    'health_percentage': (healthy_services / total_services * 100) if total_services > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get health statistics: {e}")
            return {}
    
    async def force_health_check(self, service_name: str) -> bool:
        """
        Force a health check for a specific service.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if healthy, False otherwise
        """
        if service_name not in self.services:
            logger.error(f"Service {service_name} not found")
            return False
        
        service = self.services[service_name]
        return await self._check_single_service(service_name, service)
    
    def cleanup_old_health_records(self, days: int = 90) -> int:
        """
        Clean up old health records.
        
        Args:
            days: Number of days to keep records
            
        Returns:
            Number of records cleaned up
        """
        try:
            with next(get_db()) as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Keep the most recent record for each service, but delete old ones
                # This is a simplified approach - in practice you might want more sophisticated cleanup
                
                # For now, we'll just clean up very old error records
                # In a full implementation, you might keep a rolling window of health data
                
                # This is a placeholder - implement based on specific requirements
                logger.info("Health record cleanup completed (placeholder)")
                return 0
                
        except Exception as e:
            logger.error(f"Error cleaning up health records: {e}")
            return 0