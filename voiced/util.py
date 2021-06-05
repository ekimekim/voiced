
import gevent
from gevent.subprocess import PIPE, Popen


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


def run_command(*args, **options):
	"""Runs Popen(args, **options), blocking until it exits.
	This is similar to subprocess.chcek_call(), but with the following extra behaviour:
	* All args are coerced to string
	* If stdout not given in options, stdout is captured and returned
	* If stderr not given in options, stderr is captured and included
	  in the error message if exit status is non-zero.
	* If stdin is a string, it will be passed as input.
	"""
	options.setdefault("stdout", PIPE)
	options.setdefault("stderr", PIPE)
	if isinstance(options.get("stdin"), str):
		input = options["stdin"]
		options["stdin"] = PIPE
	else:
		input = None

	proc = Popen(map(str, args), **options)
	try:
		stdout, stderr = proc.communicate(input)
		if proc.wait() != 0:
			raise Exception("{} exited with status: {}{}".format(
				args[0],
				proc.returncode,
				"" if stderr is None else "\n{}".format(stderr),
			))
	finally:
		try:
			if proc.poll() is None:
				proc.kill()
		except EnvironmentError:
			pass

	return stdout
