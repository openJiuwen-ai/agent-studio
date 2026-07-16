# coding=utf-8
"""
TaskInfo: local replacement for jiuwen.prompt.tune.template.utils.TaskInfo.

Simple data class for storing optimization task metadata.
"""


class TaskInfo:
    """Definition of prompt optimization base task info."""

    def __init__(self, task_id: str, name: str, desc: str, create_time: str):
        """
        Args:
            task_id: Unique task identifier
            name: Task display name
            desc: Task description
            create_time: Creation timestamp string (YYYY-MM-DD HH:MM:SS)
        """
        self.task_id = task_id
        self.name = name
        self.desc = desc
        self.create_time = create_time
        self.run_time = 0

    def __repr__(self):
        return (
            f"TaskInfo(task_id={self.task_id!r}, name={self.name!r}, "
            f"desc={self.desc!r}, create_time={self.create_time!r})"
        )
