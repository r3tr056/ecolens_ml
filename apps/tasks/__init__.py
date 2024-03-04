from celery.result import AsyncResult

def get_task_result(result_id):
    """ Collect Results from all Async Tasks """
    result = AsyncResult(result_id)
    if result.ready():
        if result.successful():
            return result.result
        else:
            raise Exception(f"Error while performing google search : {result.result}")
    else:
        return False
