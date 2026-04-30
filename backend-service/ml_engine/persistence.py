import pickle
import time
import random
from typing import Any, Dict, Iterator, Optional, List
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol
)
from django.db import transaction, OperationalError
from api.models import AgentCheckpoint, AgentStateWrite

class DjangoCheckpointer(BaseCheckpointSaver):
    """
    LangGraph Checkpointer that uses Django ORM for persistence.
    Caters to concurrency, serialization, and schema versioning.
    Supports intermediate writes for newer LangGraph versions.
    Includes retry logic for SQLite locking issues.
    """
    
    def __init__(self, serde: Optional[SerializerProtocol] = None):
        super().__init__(serde=serde)
        self.version = 1 # Current schema version

    def _execute_with_retry(self, func, *args, **kwargs):
        """Execute a DB function with retries for 'database is locked' errors"""
        max_retries = 5
        for i in range(max_retries):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                if "locked" in str(e).lower() and i < max_retries - 1:
                    time.sleep(0.1 + random.random() * 0.2)
                    continue
                raise

    def get_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        """
        Retrieve a checkpoint tuple from the database.
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")

        try:
            def _get():
                if checkpoint_id:
                    return AgentCheckpoint.objects.filter(thread_id=thread_id, checkpoint_id=checkpoint_id).first()
                else:
                    return AgentCheckpoint.objects.filter(thread_id=thread_id).order_by('-created_at').first()
            
            obj = self._execute_with_retry(_get)

            if obj:
                return CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": obj.checkpoint_id,
                        }
                    },
                    checkpoint=pickle.loads(obj.checkpoint_data),
                    metadata=pickle.loads(obj.metadata_data),
                    parent_config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": obj.parent_id,
                        }
                    } if obj.parent_id else None,
                )
        except Exception as e:
            print(f"[DjangoCheckpointer] Error loading checkpoint: {e}")
            
        return None

    def list(
        self,
        config: dict,
        *,
        limit: int = None,
        before: str = None,
    ) -> Iterator[CheckpointTuple]:
        """
        List checkpoints for a thread.
        """
        thread_id = config["configurable"]["thread_id"]
        
        def _list():
            query = AgentCheckpoint.objects.filter(thread_id=thread_id)
            if limit:
                query = query[:limit]
            return list(query) # Force execution within retry block

        objs = self._execute_with_retry(_list)

        for obj in objs:
            try:
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": obj.checkpoint_id,
                        }
                    },
                    checkpoint=pickle.loads(obj.checkpoint_data),
                    metadata=pickle.loads(obj.metadata_data),
                    parent_config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": obj.parent_id,
                        }
                    } if obj.parent_id else None,
                )
            except Exception as e:
                print(f"[DjangoCheckpointer] Error listing checkpoint {obj.checkpoint_id}: {e}")

    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Any = None,
    ) -> dict:
        """
        Save a checkpoint to the database.
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        parent_id = config["configurable"].get("checkpoint_id")

        try:
            checkpoint_bin = pickle.dumps(checkpoint)
            metadata_bin = pickle.dumps(metadata)
        except Exception as e:
            print(f"[DjangoCheckpointer] Serialization error in put: {e}")
            raise

        try:
            def _put():
                # We use a standalone update_or_create without transaction.atomic()
                # to reduce lock contention in SQLite during rapid agent turns
                AgentCheckpoint.objects.update_or_create(
                    thread_id=thread_id,
                    checkpoint_id=checkpoint_id,
                    defaults={
                        "parent_id": parent_id,
                        "checkpoint_data": checkpoint_bin,
                        "metadata_data": metadata_bin,
                        "version": self.version
                    }
                )
            
            self._execute_with_retry(_put)
            
        except Exception as e:
            print(f"[DjangoCheckpointer] Database error during put: {e}")
            raise

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: dict,
        writes: List[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """
        Store intermediate writes for a task.
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"]["checkpoint_id"]

        try:
            def _put_writes():
                for idx, (channel, value) in enumerate(writes):
                    AgentStateWrite.objects.update_or_create(
                        thread_id=thread_id,
                        checkpoint_id=checkpoint_id,
                        task_id=task_id,
                        idx=idx,
                        defaults={
                            "channel": channel,
                            "value": pickle.dumps(value)
                        }
                    )
            
            self._execute_with_retry(_put_writes)
            
        except Exception as e:
            print(f"[DjangoCheckpointer] Database error during put_writes: {e}")
            raise
