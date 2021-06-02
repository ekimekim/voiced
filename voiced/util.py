
import gevent


class kill_on_exit(object):
	"""Context manager for a greenlet that will kill it on context block exit,
	allowing for easy cleanup in the event of errors.
	By default, it will block until the greenlet dies.
	"""
	def __init__(self, greenlet, exception=gevent.GreenletExit, block=True):
		self.greenlet = greenlet
		self.exception = exception
		self.block = block

	def __enter__(self):
		return self.greenlet

	def __exit__(self, *exc_info):
		self.greenlet.kill(exception=self.exception, block=self.block)
