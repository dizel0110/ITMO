from akcent_graph.celeryapp import app


def get_running_task_count(task_name: str) -> int:
    inspect = app.control.inspect()  # type: ignore[attr-defined]
    task_count = 0
    for __, queue_task_list in inspect.active().items():
        for active_task in queue_task_list:
            if active_task.get('name') == task_name:
                task_count += 1
    return task_count
