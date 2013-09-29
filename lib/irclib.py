# irclib.py --- An IRC library

# Copyright (c) 2012 Jorgen Schaefer

# License: GPL

##################################################################
# Ideas:
# - Mixins!
#   - ChannelTracker: Track channels I am on, and nicks on those channels
#   - NickTracker: Track your own nick

import socket

# Constants
IRC_PORT = 6667

# RFC 2812: "if the bit 2 is set, the user mode 'w' will be set and if
# the bit 3 is set, the user mode 'i' will be set.
BITMODE_W = 1 << 2
BITMODE_I = 1 << 3
DEFAULT_BITMODE = BITMODE_I

CASEMAPPINGS = {
    'ascii': dict((ord(x), y)
                  for (x, y)
                  in zip(u'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                         u'abcdefghijklmnopqrstuvwxyz')),
    'rfc1459': dict((ord(x), y)
                    for (x, y)
                    in zip(u'ABCDEFGHIJKLMNOPQRSTUVWXYZ[]\\^',
                           u'abcdefghijklmnopqrstuvwxyz{}|~')),
    'rfc1459-strict': dict((ord(x), y)
                           for (x, y)
                           in zip(u'ABCDEFGHIJKLMNOPQRSTUVWXYZ{}|',
                                  u'abcdefghijklmnopqrstuvwxyz[]\\')),
}


class IRCConnection(object):
    """
    This class implements the IRC protocol at the lowest level.
    """
    encoding = "utf-8"

    def __init__(self, host, port=IRC_PORT):
        """
        Create a new connection to the given server.
        """
        self.host = host
        self.port = port
        self.socket = socket.create_connection((host, port))
        self.buf = ""

    def disconnect(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except:
            pass

    def read_message(self):
        """
        Read a single line from the server and return the associated
        IRCMessage.
        """
        while "\n" not in self.buf:
            try:
                new = self.socket.recv(4096)
            except socket.error:
                new = ''
            if new == '': # EOF, error
                return None
            self.buf += new.replace("\r", "")
        newline = self.buf.find("\n")
        message = IRCMessage.from_string(self.buf[:newline])
        self.buf = self.buf[newline + 1:]
        return message

    def send_message(self, message):
        """
        Send an IRCMessage object to the server.
        """
        self.socket.send(message.to_string().encode(self.encoding)
                         + "\r\n")

    def login(self, nick, user, realname, mode=DEFAULT_BITMODE, password=None):
        """
        Log in to the IRC server.

        This performs the Connection Registration step of RFC 2812,
        section 3.1.
        """
        if password is not None:
            self.send_message(IRCMessage("PASS", password))
        self.send_message(IRCMessage("NICK", nick))
        self.send_message(IRCMessage("USER", user, str(mode), "*", realname))


class IRCMessage(object):
    """
    An object representing a message used by the IRC protocol, both
    client- and server messages.

    :nick!user@host PRIVMSG #channel :Hello, World

    nick!user@host is the so-called prefix
    PRIVMSG is the command
    "#channel" and "Hello, World" are the params

    Client messages do not have a prefix.
    """
    def __init__(self, command, *params):
        """
        Create a new IRCMessage object with the given command and
        params.

        If you want to set a prefix, simply set the field after this
        object was created. Though you likely are looking for the
        from_string() class method instead.
        """
        self.prefix = None
        self.command = command
        self.params = list(params)

    @classmethod
    def from_string(cls, message):
        """
        Create a new IRCMessage object from a string received by the
        server.
        """
        last_index = message.find(" :")
        if last_index > -1:
            last_param = [message[last_index + 2:]]
            message = message[:last_index]
        else:
            last_param = []
        rest = message.split(" ")
        if len(rest) == 0:
            raise ParseError("Command string does not contain a command")
        if rest[0].startswith(":"):
            prefix = IRCUser.from_string(rest[0][1:])
            rest = rest[1:]
        else:
            prefix = None
        if len(rest) == 0:
            raise ParseError("Command string does not contain a command")
        m = IRCMessage(rest[0], *(rest[1:] + last_param))
        m.prefix = prefix
        return m

    def to_string(self):
        """
        Translate this object into an IRC message string as per the
        IRC protocol.
        """
        result = []
        if self.prefix is not None:
            result.append(u":{prefix}".format(prefix=self.prefix.to_string()))
        result.append(self.command)
        if len(self.params) > 0:
            result.extend(self.params[:-1])
            if " " in self.params[-1]:
                result.append(u":{param}".format(param=self.params[-1]))
            else:
                result.append(self.params[-1])
        return " ".join(result)

    def __repr__(self):
        return u"<IRCMessage {0}>".format(repr(self.to_string()))


class IRCUser(object):
    """
    A class representing IRC users as per the protocol.

    IRC users have a username and a host assigned to them. If no
    username is given, the nick describes a server.
    """
    def __init__(self, nick, user=None, host=None):
        """
        Create a new IRCUser object with the given parameters.
        """
        self.nick = nick
        self.user = user
        self.host = host

    @classmethod
    def from_string(cls, string):
        """
        Create a new IRCUser object from a string as received by the
        server.
        """
        bang = string.find("!")
        at = string.find("@")
        if bang > -1 and at > -1:
            return IRCUser(string[:bang],
                           string[bang + 1:at],
                           string[at + 1:])
        else:
            return IRCUser(string)

    def to_string(self):
        """
        Create a string as expected by the server from this IRCUser.

        Unless you're writing an ircd, this isn't particularly useful.
        """
        if self.user is not None:
            return "{self.nick}!{self.user}@{self.host}".format(self=self)
        else:
            return self.nick

    def __repr__(self):
        return "<IRCUser {0}>".format(repr(self.to_string()))


class ParseError(Exception):
    pass


import logging
import threading
import time


# Methods you should overwrite:
#
# on_connect(self) on_disconnect(self)
# on_NNN(self, sender, *params)
# on_COMMAND(self, sender, *params)
# on_isupport_PARAMETER(self, [value])
# on_ctcp_COMMAND(sender, target, args)
# on_ctcp_reply_COMMAND(sender, target, args)
# on_channel_message(sender, channel, text)
# on_private_message(sender, text)
# on_channel_notice(sender, channel, text)
# on_private_notice(sender, text)

class IRCClient(threading.Thread):
    """
    An IRC client running in a separate thread.
    """
    flood_last_message = 0
    flood_margin = 10
    flood_penalty = 3
    max_message_length = 400

    def __init__(self, host, port, nick, user, realname,
                 mode=DEFAULT_BITMODE, password=None):
        super(IRCClient, self).__init__()
        self.host = host
        self.port = port
        self.nick = nick
        self.user = user
        self.realname = realname
        self.initial_mode = mode
        self.password = password
        self.connection = None
        self.terminated = False
        self.log = logging.getLogger('irclib')
        self.mynick = None
        self.is_registered = False
        # Server info
        self.chantypes = ["#"]
        self.nick_prefixes = ["@", "+"]
        self.casemapping = "rfc1459"
        # Flood protection
        self.sender_thread = None
        self.sendq_lock = threading.Lock()
        self.sendq = []

    def run(self):
        while True:
            try:
                self._run2()
                if self.terminated:
                    return
            except:
                self.log.exception("Exception during IRCClient.run")
                time.sleep(60)

    def _run2(self):
        self.connect()
        self._start_sender_thread()
        while True:
            message = self.connection.read_message()
            if message is None:
                self.is_registered = False
                if self.terminated:
                    return
                self.on_disconnect()
                self.connect()
            else:
                self.handle_message(message)

    def connect(self):
        while True:
            try:
                self.connection = IRCConnection(self.host, self.port)
                self.connection.login(self.nick, self.user, self.realname,
                                      self.initial_mode, self.password)
            except Exception as e:
                self.log.info("Error {} during connect: {}. Waiting 60 "
                              "seconds before retry".format(
                        type(e).__name__, str(e)))
                time.sleep(60)
            else:
                self.sendq = []
                self.on_connect()
                return

    def disconnect(self, reason=None):
        self.terminated = True
        self.connection.send_message(IRCMessage("QUIT",
                                                "Disconnected"
                                                if reason is None
                                                else reason))
        self.connection.disconnect()

    def _start_sender_thread(self):
        """
        Start the thread that calls our queue emptying function
        regularly. This implements the flood protection.
        """
        self.sender_thread = threading.Thread(target=self._send_queue_loop)
        self.sender_thread.daemon = True
        self.sender_thread.start()

    def _send_queue_loop(self):
        """
        Regularly empty the send queue.
        """
        while True:
            self._handle_send_queue()
            time.sleep(1)

    def _handle_send_queue(self):
        """
        Try to send as many items from the send queue as possible, and
        update the flood protection accordingly.

        CAVEAT! This function is called in a different thread, so make
        sure you acquire the appropriate locks.

        See RFC 2812, section 5.8, for the algorithm.

        - If last_message is less than the current time, set equal
        - While last_message is less than now() + margin
          - send message
          - increase last_message by flood_penalty for each message
        """
        now = time.time()
        with self.sendq_lock:
            if self.flood_last_message < now:
                self.flood_last_message = now
            while (len(self.sendq) > 0 and
                   self.flood_last_message < now + self.flood_margin):
                self.connection.send_message(self.sendq.pop(0))
                self.flood_last_message += self.flood_penalty

    def send_message(self, message):
        """
        Enqueue message to be sent.
        """
        with self.sendq_lock:
            self.sendq.append(message)
        # Run the queue emptying algorithm so messages get sent out
        # without delay if we are not flooding.
        self._handle_send_queue()

    def handle_message(self, message):
        """
        Handle a message we received from the server.
        """
        handler = getattr(self, "on_{0}".format(message.command.upper()), None)
        if handler is not None:
            handler(message.prefix, *message.params)

    def is_channel(self, string):
        """
        Return True iff string represents a channel, and not a nick.

        This is server-specific.
        """
        for prefix in self.chantypes:
            if string.startswith(prefix):
                return True
        return False

    def clean_nick(self, nickname):
        """
        Remove any mode-specific prefix(es) from the nick name.

        This is server-specific.
        """
        for prefix in self.nick_prefixes:
            nickname = nickname.lstrip(prefix)
        return nickname

    def stringequal(self, a, b):
        """
        Return a true value if the strings A and B match, according to
        this IRC server's comparison rules.
        """
        return self.lower(a) == self.lower(b)

    def lower(self, string):
        """
        Return a lowercase representation of STRING according to this
        server's case mapping.
        """
        mapping = CASEMAPPINGS.get(self.casemapping, None)
        if mapping is None:
            mapping = CASEMAPPINGS.get('rfc1459')
        return unicode(string).translate(mapping)

    # Sender functions

    def msg(self, target, text):
        """
        Send a message to TARGET containing TEXT.
        """
        while len(text) > self.max_message_length:
            spc_index = text.rfind(" ", None, self.max_message_length)
            if spc_index < 0:
                this_text = text[:self.max_message_length]
                text = text[self.max_message_length:]
            else:
                this_text = text[:spc_index]
                text = text[spc_index + 1:]
            self.send_message(IRCMessage("PRIVMSG", target, this_text))
        if len(text) > 0:
            self.send_message(IRCMessage("PRIVMSG", target, text))

    def join_channel(self, channel, password=None):
        """
        Join CHANNEL.

        Optional PASSWORD is sent to authenticate.
        """
        if password is None:
            self.send_message(IRCMessage("JOIN", channel))
        else:
            self.send_message(IRCMessage("JOIN", channel, password))

    def part_channel(self, channel, reason=None):
        """
        Part from CHANNEL with an optional reason.
        """
        if reason is None:
            self.send_message(IRCMessage("PART", channel))
        else:
            self.send_message(IRCMessage("PART", channel, reason))

    def change_nick(self, newnick):
        self.send_message(IRCMessage("NICK", newnick))

    def ctcp(self, target, command, argument=None):
        if argument is None:
            text = "\x01{0}\x01".format(command)
        else:
            text = "\x01{0} {1}\x01".format(command, argument)
        self.send_message(IRCMessage("PRIVMSG", target, text))

    def ctcp_reply(self, target, command, argument=None):
        if argument is None:
            text = "\x01{0}\x01".format(command)
        else:
            text = "\x01{0} {1}\x01".format(command, argument)
        self.send_message(IRCMessage("NOTICE", target, text))

    # Handler functions
    def __getattr__(self, name):
        """
        We provide a default handler for all methods that start with
        on_. The default handler does nothing.
        """
        if name.startswith("on_"):
            return lambda *args, **kwargs: None
        else:
            raise AttributeError(
                "{classname} object has no attribute {name}".format(
                    classname=type(self).__name__,
                    name=name))

    def on_PING(self, sender, *args):
        """
        Handle a PING message.

        This sends the corresponding PONG message, bypassing our flood
        protection.
        """
        self.connection.send_message(IRCMessage("PONG", *args))

    def on_433(self, sender, mynick, attemptednick, text):
        """ERR_NICKNAMEINUSER"""
        if not self.is_registered:
            self.change_nick(attemptednick + "-")

    def on_001(self, sender, nickname, *args):
        """
        RPL_WELCOME
        """
        self.mynick = nickname
        self.is_registered = True

    def on_005(self, sender, nickname, *args):
        """
        RPL_ISUPPORT

        The last param is "are supported by this server" and can be
        ignored. The other params are tokens that configure this
        server.

        This calls on_isupport_PARAMETER([value]).
        """
        for token in args[:-1]:
            if "=" in token:
                parameter, value = token.split("=", 1)
            else:
                parameter, value = token, None
            handler = getattr(self,
                              "on_isupport_{0}".format(parameter.upper()),
                              None)
            if handler is not None:
                if value is None:
                    handler()
                else:
                    handler(value)

    def on_isupport_CHANTYPES(self, chantypes):
        self.chantypes = list(chantypes)

    def on_isupport_PREFIX(self, value):
        modes, prefixes = value.split(")", 1)
        modes = modes[1:]
        self.nick_prefixes = list(prefixes)

    def on_isupport_CASEMAPPING(self, casemapping):
        self.casemapping = casemapping

    def on_PRIVMSG(self, sender, target, text):
        if text.startswith("\x01"):
            command, args = text.strip("\x01").split(" ", 1)
            command = command.upper()
            args = args.strip()
            handler = getattr(self, "on_ctcp_{0}".format(command),
                              None)
            if handler is not None:
                handler(sender, target, args)
        elif self.is_channel(target):
            self.on_channel_message(sender, target, text)
        else:
            self.on_private_message(sender, text)

    def on_NOTICE(self, sender, target, text):
        if text.startswith("\x01"):
            command, args = text.strip("\x01").split(" ", 1)
            command = command.upper()
            args = args.strip()
            handler = getattr(self, "on_ctcp_reply_{0}".format(command),
                              None)
            if handler is not None:
                handler(sender, target, command, args)
        elif self.is_channel(target):
            self.on_channel_notice(sender, target, text)
        else:
            self.on_private_notice(sender, text)

    def on_NICK(self, sender, newnick):
        if self.stringequal(sender.nick, self.mynick):
            self.mynick = newnick


import shlex

class IRCBot(IRCClient):
    command_char = "!"

    def __init__(self, server, port, nick, user, realname, channels):
        super(IRCBot, self).__init__(server, port, nick, user, realname)
        self.channels = set(channels)

    def on_001(self, sender, *args):
        super(IRCBot, self).on_001(sender, *args)
        for channel in self.channels:
            self.join_channel(channel)

    def join_channel(self, channel, password=None):
        super(IRCBot, self).join_channel(channel, password)
        if password is not None:
            self.channels.add(channel)

    def part_channel(self, channel, reason=None):
        super(IRCBot, self).part_channel(channel, reason)
        try:
            self.channels.remove(channel)
        except KeyError:
            pass

    def on_channel_message(self, sender, channel, text):
        if text.startswith(self.command_char):
            self.handle_command(sender, channel, text)

    def on_private_message(self, sender, text):
        if text.startswith(self.command_char):
            self.handle_command(sender, None, text)

    def reply(self, sender, channel, text):
        if channel is None:
            self.msg(sender.nick, text)
        else:
            self.msg(channel, u"{nick}: {text}".format(nick=sender.nick,
                                                       text=text))

    def handle_command(self, sender, channel, text):
        command_split = text.split(" ", 1)
        if len(command_split) == 1:
            command = command_split[0].lstrip(self.command_char)
            argstring = ""
        else:
            command = command_split[0].lstrip(self.command_char)
            argstring = command_split[1].strip()
        if len(command) == 0:
            # <foo> !
            # That's not a command. honest.
            return
        handler = getattr(self, "cmd_{0}".format(command.upper()), None)
        if handler is None:
            self.reply(sender, channel, "Unknown command {0}".format(command))
            return
        if getattr(handler, 'dont_parse_args', False):
            args = [argstring]
        else:
            args = shlex.split(argstring)
        if not sufficient_args(handler, len(args) + 3): # self, sender, channel
            self.reply(sender, channel,
                       "Wrong number of arguments. Try !help {0}"
                       .format(command))
            return
        try:
            handler(sender, channel, *args)
        except:
            self.reply(sender, channel,
                       "An error occurred during the execution of your "
                       "command. Sorry. Admins notified.")
            logging.exception("Error during the execution of {0}:"
                              .format(repr(text)))

    def cmd_HELP(self, sender, channel, command=None):
        """
        Display a list of commands, or the documentation of a specific command.
        """
        if command is None:
            commands = []
            for attrib in dir(self):
                if not attrib.startswith("cmd_"):
                    continue
                commands.append(attrib[4:].lower())
            self.reply(sender, channel, "Available commands: {0}. Use "
                       "{1}help <command> for more information.".format(
                    ", ".join(commands), self.command_char))
        else:
            method = getattr(self, "cmd_{0}".format(command.upper()), None)
            if method.__doc__ is None:
                self.reply(sender, channel, "Command {0} is not documented."
                           .format(repr(command)))
                return
            docstring = method.__doc__.strip().split("\n")[0]
            self.reply(sender, channel, "{0}{1}: {2}".format(
                    self.command_char, command, docstring))


import inspect
def sufficient_args(fun, arglen):
    argspec = inspect.getargspec(fun)
    min_args = len(argspec.args) - len(argspec.defaults or [])
    max_args = len(argspec.args) if argspec.varargs is None else None
    if arglen < min_args:
        return False
    if max_args is not None and arglen > max_args:
        return False
    return True
