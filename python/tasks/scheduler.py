"""
Background task scheduler for managing periodic tasks.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass, field

from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TaskInfo:
    """Information about a scheduled task."""
    func: Callable
    interval: int  # seconds
    last_run: datetime = field(default_factory=datetime.utcnow)
    running: bool = False
    error_count: int = 0
    last_error: Optional[str] = None
    run_immediately: bool = False
    max_retries: int = 3
    backoff_multiplier: float = 2.0


class TaskScheduler:
    """Manages background tasks with configurable intervals and error handling."""
    
    def __init__(self):
        """Initialize the task scheduler."""
        self.tasks: Dict[str, TaskInfo] = {}
        self.running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self.check_interval = 10  # seconds between task checks
    
    def register_task(self, 
                     name: str, 
                     func: Callable, 
                     interval_seconds: int, 
                     run_immediately: bool = False,
                     max_retries: int = 3) -> None:
        """
        Register a background task.
        
        Args:
            name: Unique name for the task
            func: Async function to execute
            interval_seconds: How often to run the task (in seconds)
            run_immediately: Whether to run the task immediately on first check
            max_retries: Maximum number of retries on failure
        """
        if name in self.tasks:
            logger.warning(f"Task {name} is already registered, replacing")
        
        task_info = TaskInfo(
            func=func,
            interval=interval_seconds,
            run_immediately=run_immediately,
            max_retries=max_retries
        )
        
        # If run_immediately is True, set last_run to past time
        if run_immediately:
            task_info.last_run = datetime.utcnow() - timedelta(seconds=interval_seconds)
        
        self.tasks[name] = task_info
        logger.info(f"Registered task: {name} (interval: {interval_seconds}s, immediate: {run_immediately})")
    
    def unregister_task(self, name: str) -> bool:
        """
        Unregister a task.
        
        Args:
            name: Name of the task to unregister
            
        Returns:
            True if task was removed, False if not found
        """
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Unregistered task: {name}")
            return True
        return False
    
    async def start(self) -> None:
        """Start the task scheduler."""
        if self.running:
            logger.warning("Task scheduler is already running")
            return
        
        self.running = True
        logger.info("Task scheduler started")
        
        try:
            while self.running:
                await self._check_and_run_tasks()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("Task scheduler cancelled")
        except Exception as e:
            logger.error(f"Task scheduler error: {e}")
        finally:
            self.running = False
            logger.info("Task scheduler stopped")
    
    async def stop(self) -> None:
        """Stop the task scheduler."""
        if not self.running:
            return
        
        logger.info("Stopping task scheduler...")
        self.running = False
        
        # Cancel the scheduler task if it exists
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Wait for any running tasks to complete (with timeout)
        running_tasks = [name for name, task in self.tasks.items() if task.running]
        if running_tasks:
            logger.info(f"Waiting for {len(running_tasks)} tasks to complete...")
            # Give tasks up to 30 seconds to complete
            for _ in range(30):
                if not any(task.running for task in self.tasks.values()):
                    break
                await asyncio.sleep(1)
        
        logger.info("Task scheduler stopped")
    
    async def _check_and_run_tasks(self) -> None:
        """Check which tasks need to run and execute them."""
        current_time = datetime.utcnow()
        
        for task_name, task_info in self.tasks.items():
            # Skip if task is already running
            if task_info.running:
                continue
            
            # Check if it's time to run
            time_since_last = (current_time - task_info.last_run).total_seconds()
            
            # Apply exponential backoff for failing tasks
            effective_interval = task_info.interval
            if task_info.error_count > 0:
                backoff_factor = task_info.backoff_multiplier ** min(task_info.error_count, 5)
                effective_interval = min(task_info.interval * backoff_factor, 3600)  # Max 1 hour
            
            if time_since_last >= effective_interval:
                # Create task to run in background
                asyncio.create_task(self._run_task(task_name, task_info))
    
    async def _run_task(self, task_name: str, task_info: TaskInfo) -> None:
        """
        Run a single task.
        
        Args:
            task_name: Name of the task
            task_info: Task information object
        """
        task_info.running = True
        task_info.last_run = datetime.utcnow()
        
        try:
            logger.debug(f"Running task: {task_name}")
            start_time = time.time()
            
            # Run the task function
            if asyncio.iscoroutinefunction(task_info.func):
                await task_info.func()
            else:
                # Run synchronous function in executor
                await asyncio.get_event_loop().run_in_executor(None, task_info.func)
            
            execution_time = time.time() - start_time
            
            # Task completed successfully
            task_info.error_count = 0
            task_info.last_error = None
            
            logger.debug(f"Task {task_name} completed successfully in {execution_time:.2f}s")
            
        except Exception as e:
            task_info.error_count += 1
            task_info.last_error = str(e)
            
            logger.error(f"Task {task_name} failed (attempt {task_info.error_count}): {e}")
            
            # If max retries exceeded, increase interval significantly
            if task_info.error_count >= task_info.max_retries:
                logger.warning(f"Task {task_name} has failed {task_info.error_count} times, backing off")
        
        finally:
            task_info.running = False
    
    def get_task_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all registered tasks.
        
        Returns:
            Dictionary containing task status information
        """
        status = {}
        current_time = datetime.utcnow()
        
        for task_name, task_info in self.tasks.items():
            # Calculate next run time considering backoff
            effective_interval = task_info.interval
            if task_info.error_count > 0:
                backoff_factor = task_info.backoff_multiplier ** min(task_info.error_count, 5)
                effective_interval = min(task_info.interval * backoff_factor, 3600)
            
            next_run = task_info.last_run + timedelta(seconds=effective_interval)
            overdue = current_time > next_run and not task_info.running
            
            status[task_name] = {
                'interval': task_info.interval,
                'effective_interval': effective_interval,
                'last_run': task_info.last_run,
                'next_run': next_run,
                'running': task_info.running,
                'error_count': task_info.error_count,
                'last_error': task_info.last_error,
                'overdue': overdue,
                'max_retries': task_info.max_retries
            }
        
        return status
    
    def get_task_info(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific task.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Task information dictionary or None if not found
        """
        if task_name not in self.tasks:
            return None
        
        all_status = self.get_task_status()
        return all_status.get(task_name)
    
    async def run_task_immediately(self, task_name: str) -> bool:
        """
        Run a specific task immediately (bypass schedule).
        
        Args:
            task_name: Name of the task to run
            
        Returns:
            True if task was started, False if not found or already running
        """
        if task_name not in self.tasks:
            logger.error(f"Task {task_name} not found")
            return False
        
        task_info = self.tasks[task_name]
        
        if task_info.running:
            logger.warning(f"Task {task_name} is already running")
            return False
        
        logger.info(f"Running task {task_name} immediately")
        asyncio.create_task(self._run_task(task_name, task_info))
        return True
    
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self.running
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get scheduler statistics.
        
        Returns:
            Dictionary with scheduler statistics
        """
        total_tasks = len(self.tasks)
        running_tasks = sum(1 for task in self.tasks.values() if task.running)
        failing_tasks = sum(1 for task in self.tasks.values() if task.error_count > 0)
        overdue_tasks = sum(1 for task_name in self.tasks.keys() 
                          if self.get_task_status()[task_name]['overdue'])
        
        return {
            'scheduler_running': self.running,
            'total_tasks': total_tasks,
            'running_tasks': running_tasks,
            'failing_tasks': failing_tasks,
            'overdue_tasks': overdue_tasks,
            'check_interval': self.check_interval
        }