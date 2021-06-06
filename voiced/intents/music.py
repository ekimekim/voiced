
import logging
import socket
from contextlib import closing

from .. import sounds
from ..intent import intent


CONTROL_SOCK_PATH = "/tmp/awp.sock"


def write_control(char):
	with closing(socket.socket(socket.AF_UNIX)) as sock:
		sock.connect(CONTROL_SOCK_PATH)
		sock.sendall(char)


@intent("music")
def music(text, command, volume=None):
	char = {
		"favourite": "f",
		"skip": "q",
		"next": "\n",
		"pause": " ",
		"unpause": " ",
		"volume up": "***",
		"volume down": "///",
	}.get(command)
	if char is None:
		logging.warning("Unimplemented command: {}".format(command))
		return sounds.ERROR
	write_control(char)
