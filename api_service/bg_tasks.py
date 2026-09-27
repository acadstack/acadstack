from apscheduler.schedulers.background import BackgroundScheduler

class BgTasks:
    """
    Provides background tasks scheduling.
    """
    def __init__(self, config) -> None:
        """Constructor for the class

        Args:
            config (dict): A dict object containing the configuration settings.
            For example, the flask app config dictionary.
        """
        self.scheduler = BackgroundScheduler()
        self.config = config
    
    def start(self):
        """Must be called after adding jobs.
        """
        self.scheduler.start()
    
    def add_job(self, func, args_dict):
        """Adds a job to background tasks scheduler.

        Args:
            func (function): Function to schedule. It must
            accept at least a named argument 'config'.
            args_dict (dict): dictionary of kwargs to be
            passed to the scheduled function.
        """
        if "kwargs" not in args_dict:
            args_dict["kwargs"] = dict()
        args_dict["kwargs"]["config"] = self.config
        self.scheduler.add_job(func, **args_dict)
    
        