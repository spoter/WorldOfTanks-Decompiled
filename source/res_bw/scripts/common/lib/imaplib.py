# Embedded file name: scripts/common/Lib/imaplib.py
"""IMAP4 client.

Based on RFC 2060.

Public class:           IMAP4
Public variable:        Debug
Public functions:       Internaldate2tuple
                        Int2AP
                        ParseFlags
                        Time2Internaldate
"""
__version__ = '2.58'
import binascii, errno, random, re, socket, subprocess, sys, time
__all__ = ['IMAP4',
 'IMAP4_stream',
 'Internaldate2tuple',
 'Int2AP',
 'ParseFlags',
 'Time2Internaldate']
CRLF = '\r\n'
Debug = 0
IMAP4_PORT = 143
IMAP4_SSL_PORT = 993
AllowedVersions = ('IMAP4REV1', 'IMAP4')
_MAXLINE = 10000
Commands = {'APPEND': ('AUTH', 'SELECTED'),
 'AUTHENTICATE': ('NONAUTH',),
 'CAPABILITY': ('NONAUTH',
                'AUTH',
                'SELECTED',
                'LOGOUT'),
 'CHECK': ('SELECTED',),
 'CLOSE': ('SELECTED',),
 'COPY': ('SELECTED',),
 'CREATE': ('AUTH', 'SELECTED'),
 'DELETE': ('AUTH', 'SELECTED'),
 'DELETEACL': ('AUTH', 'SELECTED'),
 'EXAMINE': ('AUTH', 'SELECTED'),
 'EXPUNGE': ('SELECTED',),
 'FETCH': ('SELECTED',),
 'GETACL': ('AUTH', 'SELECTED'),
 'GETANNOTATION': ('AUTH', 'SELECTED'),
 'GETQUOTA': ('AUTH', 'SELECTED'),
 'GETQUOTAROOT': ('AUTH', 'SELECTED'),
 'MYRIGHTS': ('AUTH', 'SELECTED'),
 'LIST': ('AUTH', 'SELECTED'),
 'LOGIN': ('NONAUTH',),
 'LOGOUT': ('NONAUTH',
            'AUTH',
            'SELECTED',
            'LOGOUT'),
 'LSUB': ('AUTH', 'SELECTED'),
 'NAMESPACE': ('AUTH', 'SELECTED'),
 'NOOP': ('NONAUTH',
          'AUTH',
          'SELECTED',
          'LOGOUT'),
 'PARTIAL': ('SELECTED',),
 'PROXYAUTH': ('AUTH',),
 'RENAME': ('AUTH', 'SELECTED'),
 'SEARCH': ('SELECTED',),
 'SELECT': ('AUTH', 'SELECTED'),
 'SETACL': ('AUTH', 'SELECTED'),
 'SETANNOTATION': ('AUTH', 'SELECTED'),
 'SETQUOTA': ('AUTH', 'SELECTED'),
 'SORT': ('SELECTED',),
 'STATUS': ('AUTH', 'SELECTED'),
 'STORE': ('SELECTED',),
 'SUBSCRIBE': ('AUTH', 'SELECTED'),
 'THREAD': ('SELECTED',),
 'UID': ('SELECTED',),
 'UNSUBSCRIBE': ('AUTH', 'SELECTED')}
Continuation = re.compile('\\+( (?P<data>.*))?')
Flags = re.compile('.*FLAGS \\((?P<flags>[^\\)]*)\\)')
InternalDate = re.compile('.*INTERNALDATE "(?P<day>[ 0123][0-9])-(?P<mon>[A-Z][a-z][a-z])-(?P<year>[0-9][0-9][0-9][0-9]) (?P<hour>[0-9][0-9]):(?P<min>[0-9][0-9]):(?P<sec>[0-9][0-9]) (?P<zonen>[-+])(?P<zoneh>[0-9][0-9])(?P<zonem>[0-9][0-9])"')
Literal = re.compile('.*{(?P<size>\\d+)}$')
MapCRLF = re.compile('\\r\\n|\\r|\\n')
Response_code = re.compile('\\[(?P<type>[A-Z-]+)( (?P<data>[^\\]]*))?\\]')
Untagged_response = re.compile('\\* (?P<type>[A-Z-]+)( (?P<data>.*))?')
Untagged_status = re.compile('\\* (?P<data>\\d+) (?P<type>[A-Z-]+)( (?P<data2>.*))?')

class IMAP4():
    r"""IMAP4 client class.
    
    Instantiate with: IMAP4([host[, port]])
    
            host - host's name (default: localhost);
            port - port number (default: standard IMAP4 port).
    
    All IMAP4rev1 commands are supported by methods of the same
    name (in lower-case).
    
    All arguments to commands are converted to strings, except for
    AUTHENTICATE, and the last argument to APPEND which is passed as
    an IMAP4 literal.  If necessary (the string contains any
    non-printing characters or white-space and isn't enclosed with
    either parentheses or double quotes) each string is quoted.
    However, the 'password' argument to the LOGIN command is always
    quoted.  If you want to avoid having an argument string quoted
    (eg: the 'flags' argument to STORE) then enclose the string in
    parentheses (eg: "(\Deleted)").
    
    Each command returns a tuple: (type, [data, ...]) where 'type'
    is usually 'OK' or 'NO', and 'data' is either the text from the
    tagged response, or untagged results from command. Each 'data'
    is either a string, or a tuple. If a tuple, then the first part
    is the header of the response, and the second part contains
    the data (ie: 'literal' value).
    
    Errors raise the exception class <instance>.error("<reason>").
    IMAP4 server errors raise <instance>.abort("<reason>"),
    which is a sub-class of 'error'. Mailbox status changes
    from READ-WRITE to READ-ONLY raise the exception class
    <instance>.readonly("<reason>"), which is a sub-class of 'abort'.
    
    "error" exceptions imply a program error.
    "abort" exceptions imply the connection should be reset, and
            the command re-tried.
    "readonly" exceptions imply the command should be re-tried.
    
    Note: to use this module, you must read the RFCs pertaining to the
    IMAP4 protocol, as the semantics of the arguments to each IMAP4
    command are left to the invoker, not to mention the results. Also,
    most IMAP servers implement a sub-set of the commands available here.
    """

    class error(Exception):
        pass

    class abort(error):
        pass

    class readonly(abort):
        pass

    mustquote = re.compile("[^\\w!#$%&'*+,.:;<=>?^`|~-]")

    def __init__(self, host = '', port = IMAP4_PORT):
        self.debug = Debug
        self.state = 'LOGOUT'
        self.literal = None
        self.tagged_commands = {}
        self.untagged_responses = {}
        self.continuation_response = ''
        self.is_readonly = False
        self.tagnum = 0
        self.open(host, port)
        self.tagpre = Int2AP(random.randint(4096, 65535))
        self.tagre = re.compile('(?P<tag>' + self.tagpre + '\\d+) (?P<type>[A-Z]+) (?P<data>.*)')
        self._cmd_log_len = 10
        self._cmd_log_idx = 0
        self._cmd_log = {}
        if self.debug >= 1:
            self._mesg('imaplib version %s' % __version__)
            self._mesg('new IMAP4 connection, tag=%s' % self.tagpre)
        self.welcome = self._get_response()
        if 'PREAUTH' in self.untagged_responses:
            self.state = 'AUTH'
        elif 'OK' in self.untagged_responses:
            self.state = 'NONAUTH'
        else:
            raise self.error(self.welcome)
        typ, dat = self.capability()
        if dat == [None]:
            raise self.error('no CAPABILITY response from server')
        self.capabilities = tuple(dat[-1].upper().split())
        if self.debug >= 3:
            self._mesg('CAPABILITIES: %r' % (self.capabilities,))
        for version in AllowedVersions:
            if version not in self.capabilities:
                continue
            self.PROTOCOL_VERSION = version
            return

        raise self.error('server not IMAP4 compliant')
        return

    def __getattr__(self, attr):
        if attr in Commands:
            return getattr(self, attr.lower())
        raise AttributeError("Unknown IMAP4 command: '%s'" % attr)

    def open(self, host = '', port = IMAP4_PORT):
        """Setup connection to remote server on "host:port"
            (default: localhost:standard IMAP4 port).
        This connection will be used by the routines:
            read, readline, send, shutdown.
        """
        self.host = host
        self.port = port
        self.sock = socket.create_connection((host, port))
        self.file = self.sock.makefile('rb')

    def read(self, size):
        """Read 'size' bytes from remote."""
        return self.file.read(size)

    def readline(self):
        """Read line from remote."""
        line = self.file.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            raise self.error('got more than %d bytes' % _MAXLINE)
        return line

    def send(self, data):
        """Send data to remote."""
        self.sock.sendall(data)

    def shutdown(self):
        """Close I/O established in "open"."""
        self.file.close()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            if e.errno != errno.ENOTCONN:
                raise
        finally:
            self.sock.close()

    def socket(self):
        """Return socket instance used to connect to IMAP4 server.
        
        socket = <instance>.socket()
        """
        return self.sock

    def recent(self):
        """Return most recent 'RECENT' responses if any exist,
        else prompt server for an update using the 'NOOP' command.
        
        (typ, [data]) = <instance>.recent()
        
        'data' is None if no new messages,
        else list of RECENT responses, most recent last.
        """
        name = 'RECENT'
        typ, dat = self._untagged_response('OK', [None], name)
        if dat[-1]:
            return (typ, dat)
        else:
            typ, dat = self.noop()
            return self._untagged_response(typ, dat, name)

    def response(self, code):
        """Return data for response 'code' if received, or None.
        
        Old value for response 'code' is cleared.
        
        (code, [data]) = <instance>.response(code)
        """
        return self._untagged_response(code, [None], code.upper())

    def append(self, mailbox, flags, date_time, message):
        """Append message to named mailbox.
        
        (typ, [data]) = <instance>.append(mailbox, flags, date_time, message)
        
                All args except `message' can be None.
        """
        name = 'APPEND'
        if not mailbox:
            mailbox = 'INBOX'
        if flags:
            if (flags[0], flags[-1]) != ('(', ')'):
                flags = '(%s)' % flags
        else:
            flags = None
        if date_time:
            date_time = Time2Internaldate(date_time)
        else:
            date_time = None
        self.literal = MapCRLF.sub(CRLF, message)
        return self._simple_command(name, mailbox, flags, date_time)

    def authenticate(self, mechanism, authobject):
        """Authenticate command - requires response processing.
        
        'mechanism' specifies which authentication mechanism is to
        be used - it must appear in <instance>.capabilities in the
        form AUTH=<mechanism>.
        
        'authobject' must be a callable object:
        
                data = authobject(response)
        
        It will be called to process server continuation responses.
        It should return data that will be encoded and sent to server.
        It should return None if the client abort response '*' should
        be sent instead.
        """
        mech = mechanism.upper()
        self.literal = _Authenticator(authobject).process
        typ, dat = self._simple_command('AUTHENTICATE', mech)
        if typ != 'OK':
            raise self.error(dat[-1])
        self.state = 'AUTH'
        return (typ, dat)

    def capability(self):
        """(typ, [data]) = <instance>.capability()
        Fetch capabilities list from server."""
        name = 'CAPABILITY'
        typ, dat = self._simple_command(name)
        return self._untagged_response(typ, dat, name)

    def check(self):
        """Checkpoint mailbox on server.
        
        (typ, [data]) = <instance>.check()
        """
        return self._simple_command('CHECK')

    def close(self):
        """Close currently selected mailbox.
        
        Deleted messages are removed from writable mailbox.
        This is the recommended command before 'LOGOUT'.
        
        (typ, [data]) = <instance>.close()
        """
        try:
            typ, dat = self._simple_command('CLOSE')
        finally:
            self.state = 'AUTH'

        return (typ, dat)

    def copy(self, message_set, new_mailbox):
        """Copy 'message_set' messages onto end of 'new_mailbox'.
        
        (typ, [data]) = <instance>.copy(message_set, new_mailbox)
        """
        return self._simple_command('COPY', message_set, new_mailbox)

    def create(self, mailbox):
        """Create new mailbox.
        
        (typ, [data]) = <instance>.create(mailbox)
        """
        return self._simple_command('CREATE', mailbox)

    def delete(self, mailbox):
        """Delete old mailbox.
        
        (typ, [data]) = <instance>.delete(mailbox)
        """
        return self._simple_command('DELETE', mailbox)

    def deleteacl(self, mailbox, who):
        """Delete the ACLs (remove any rights) set for who on mailbox.
        
        (typ, [data]) = <instance>.deleteacl(mailbox, who)
        """
        return self._simple_command('DELETEACL', mailbox, who)

    def expunge(self):
        """Permanently remove deleted items from selected mailbox.
        
        Generates 'EXPUNGE' response for each deleted message.
        
        (typ, [data]) = <instance>.expunge()
        
        'data' is list of 'EXPUNGE'd message numbers in order received.
        """
        name = 'EXPUNGE'
        typ, dat = self._simple_command(name)
        return self._untagged_response(typ, dat, name)

    def fetch(self, message_set, message_parts):
        """Fetch (parts of) messages.
        
        (typ, [data, ...]) = <instance>.fetch(message_set, message_parts)
        
        'message_parts' should be a string of selected parts
        enclosed in parentheses, eg: "(UID BODY[TEXT])".
        
        'data' are tuples of message part envelope and data.
        """
        name = 'FETCH'
        typ, dat = self._simple_command(name, message_set, message_parts)
        return self._untagged_response(typ, dat, name)

    def getacl(self, mailbox):
        """Get the ACLs for a mailbox.
        
        (typ, [data]) = <instance>.getacl(mailbox)
        """
        typ, dat = self._simple_command('GETACL', mailbox)
        return self._untagged_response(typ, dat, 'ACL')

    def getannotation(self, mailbox, entry, attribute):
        """(typ, [data]) = <instance>.getannotation(mailbox, entry, attribute)
        Retrieve ANNOTATIONs."""
        typ, dat = self._simple_command('GETANNOTATION', mailbox, entry, attribute)
        return self._untagged_response(typ, dat, 'ANNOTATION')

    def getquota(self, root):
        """Get the quota root's resource usage and limits.
        
        Part of the IMAP4 QUOTA extension defined in rfc2087.
        
        (typ, [data]) = <instance>.getquota(root)
        """
        typ, dat = self._simple_command('GETQUOTA', root)
        return self._untagged_response(typ, dat, 'QUOTA')

    def getquotaroot(self, mailbox):
        """Get the list of quota roots for the named mailbox.
        
        (typ, [[QUOTAROOT responses...], [QUOTA responses]]) = <instance>.getquotaroot(mailbox)
        """
        typ, dat = self._simple_command('GETQUOTAROOT', mailbox)
        typ, quota = self._untagged_response(typ, dat, 'QUOTA')
        typ, quotaroot = self._untagged_response(typ, dat, 'QUOTAROOT')
        return (typ, [quotaroot, quota])

    def list(self, directory = '""', pattern = '*'):
        """List mailbox names in directory matching pattern.
        
        (typ, [data]) = <instance>.list(directory='""', pattern='*')
        
        'data' is list of LIST responses.
        """
        name = 'LIST'
        typ, dat = self._simple_command(name, directory, pattern)
        return self._untagged_response(typ, dat, name)

    def login(self, user, password):
        """Identify client using plaintext password.
        
        (typ, [data]) = <instance>.login(user, password)
        
        NB: 'password' will be quoted.
        """
        typ, dat = self._simple_command('LOGIN', user, self._quote(password))
        if typ != 'OK':
            raise self.error(dat[-1])
        self.state = 'AUTH'
        return (typ, dat)

    def login_cram_md5(self, user, password):
        """ Force use of CRAM-MD5 authentication.
        
        (typ, [data]) = <instance>.login_cram_md5(user, password)
        """
        self.user, self.password = user, password
        return self.authenticate('CRAM-MD5', self._CRAM_MD5_AUTH)

    def _CRAM_MD5_AUTH(self, challenge):
        """ Authobject to use with CRAM-MD5 authentication. """
        import hmac
        return self.user + ' ' + hmac.HMAC(self.password, challenge).hexdigest()

    def logout(self):
        """Shutdown connection to server.
        
        (typ, [data]) = <instance>.logout()
        
        Returns server 'BYE' response.
        """
        self.state = 'LOGOUT'
        try:
            typ, dat = self._simple_command('LOGOUT')
        except:
            typ, dat = 'NO', ['%s: %s' % sys.exc_info()[:2]]

        self.shutdown()
        if 'BYE' in self.untagged_responses:
            return ('BYE', self.untagged_responses['BYE'])
        return (typ, dat)

    def lsub(self, directory = '""', pattern = '*'):
        """List 'subscribed' mailbox names in directory matching pattern.
        
        (typ, [data, ...]) = <instance>.lsub(directory='""', pattern='*')
        
        'data' are tuples of message part envelope and data.
        """
        name = 'LSUB'
        typ, dat = self._simple_command(name, directory, pattern)
        return self._untagged_response(typ, dat, name)

    def myrights(self, mailbox):
        """Show my ACLs for a mailbox (i.e. the rights that I have on mailbox).
        
        (typ, [data]) = <instance>.myrights(mailbox)
        """
        typ, dat = self._simple_command('MYRIGHTS', mailbox)
        return self._untagged_response(typ, dat, 'MYRIGHTS')

    def namespace(self):
        """ Returns IMAP namespaces ala rfc2342
        
        (typ, [data, ...]) = <instance>.namespace()
        """
        name = 'NAMESPACE'
        typ, dat = self._simple_command(name)
        return self._untagged_response(typ, dat, name)

    def noop(self):
        """Send NOOP command.
        
        (typ, [data]) = <instance>.noop()
        """
        if self.debug >= 3:
            self._dump_ur(self.untagged_responses)
        return self._simple_command('NOOP')

    def partial(self, message_num, message_part, start, length):
        """Fetch truncated part of a message.
        
        (typ, [data, ...]) = <instance>.partial(message_num, message_part, start, length)
        
        'data' is tuple of message part envelope and data.
        """
        name = 'PARTIAL'
        typ, dat = self._simple_command(name, message_num, message_part, start, length)
        return self._untagged_response(typ, dat, 'FETCH')

    def proxyauth(self, user):
        """Assume authentication as "user".
        
        Allows an authorised administrator to proxy into any user's
        mailbox.
        
        (typ, [data]) = <instance>.proxyauth(user)
        """
        name = 'PROXYAUTH'
        return self._simple_command('PROXYAUTH', user)

    def rename(self, oldmailbox, newmailbox):
        """Rename old mailbox name to new.
        
        (typ, [data]) = <instance>.rename(oldmailbox, newmailbox)
        """
        return self._simple_command('RENAME', oldmailbox, newmailbox)

    def search(self, charset, *criteria):
        """Search mailbox for matching messages.
        
        (typ, [data]) = <instance>.search(charset, criterion, ...)
        
        'data' is space separated list of matching message numbers.
        """
        name = 'SEARCH'
        if charset:
            typ, dat = self._simple_command(name, 'CHARSET', charset, *criteria)
        else:
            typ, dat = self._simple_command(name, *criteria)
        return self._untagged_response(typ, dat, name)

    def select(self, mailbox = 'INBOX', readonly = False):
        """Select a mailbox.
        
        Flush all untagged responses.
        
        (typ, [data]) = <instance>.select(mailbox='INBOX', readonly=False)
        
        'data' is count of messages in mailbox ('EXISTS' response).
        
        Mandated responses are ('FLAGS', 'EXISTS', 'RECENT', 'UIDVALIDITY'), so
        other responses should be obtained via <instance>.response('FLAGS') etc.
        """
        self.untagged_responses = {}
        self.is_readonly = readonly
        if readonly:
            name = 'EXAMINE'
        else:
            name = 'SELECT'
        typ, dat = self._simple_command(name, mailbox)
        if typ != 'OK':
            self.state = 'AUTH'
            return (typ, dat)
        else:
            self.state = 'SELECTED'
            if 'READ-ONLY' in self.untagged_responses and not readonly:
                if self.debug >= 1:
                    self._dump_ur(self.untagged_responses)
                raise self.readonly('%s is not writable' % mailbox)
            return (typ, self.untagged_responses.get('EXISTS', [None]))

    def setacl(self, mailbox, who, what):
        """Set a mailbox acl.
        
        (typ, [data]) = <instance>.setacl(mailbox, who, what)
        """
        return self._simple_command('SETACL', mailbox, who, what)

    def setannotation(self, *args):
        """(typ, [data]) = <instance>.setannotation(mailbox[, entry, attribute]+)
        Set ANNOTATIONs."""
        typ, dat = self._simple_command('SETANNOTATION', *args)
        return self._untagged_response(typ, dat, 'ANNOTATION')

    def setquota(self, root, limits):
        """Set the quota root's resource limits.
        
        (typ, [data]) = <instance>.setquota(root, limits)
        """
        typ, dat = self._simple_command('SETQUOTA', root, limits)
        return self._untagged_response(typ, dat, 'QUOTA')

    def sort(self, sort_criteria, charset, *search_criteria):
        """IMAP4rev1 extension SORT command.
        
        (typ, [data]) = <instance>.sort(sort_criteria, charset, search_criteria, ...)
        """
        name = 'SORT'
        if (sort_criteria[0], sort_criteria[-1]) != ('(', ')'):
            sort_criteria = '(%s)' % sort_criteria
        typ, dat = self._simple_command(name, sort_criteria, charset, *search_criteria)
        return self._untagged_response(typ, dat, name)

    def status(self, mailbox, names):
        """Request named status conditions for mailbox.
        
        (typ, [data]) = <instance>.status(mailbox, names)
        """
        name = 'STATUS'
        typ, dat = self._simple_command(name, mailbox, names)
        return self._untagged_response(typ, dat, name)

    def store(self, message_set, command, flags):
        """Alters flag dispositions for messages in mailbox.
        
        (typ, [data]) = <instance>.store(message_set, command, flags)
        """
        if (flags[0], flags[-1]) != ('(', ')'):
            flags = '(%s)' % flags
        typ, dat = self._simple_command('STORE', message_set, command, flags)
        return self._untagged_response(typ, dat, 'FETCH')

    def subscribe(self, mailbox):
        """Subscribe to new mailbox.
        
        (typ, [data]) = <instance>.subscribe(mailbox)
        """
        return self._simple_command('SUBSCRIBE', mailbox)

    def thread(self, threading_algorithm, charset, *search_criteria):
        """IMAPrev1 extension THREAD command.
        
        (type, [data]) = <instance>.thread(threading_algorithm, charset, search_criteria, ...)
        """
        name = 'THREAD'
        typ, dat = self._simple_command(name, threading_algorithm, charset, *search_criteria)
        return self._untagged_response(typ, dat, name)

    def uid(self, command, *args):
        """Execute "command arg ..." with messages identified by UID,
                rather than message number.
        
        (typ, [data]) = <instance>.uid(command, arg1, arg2, ...)
        
        Returns response appropriate to 'command'.
        """
        command = command.upper()
        if command not in Commands:
            raise self.error('Unknown IMAP4 UID command: %s' % command)
        if self.state not in Commands[command]:
            raise self.error('command %s illegal in state %s, only allowed in states %s' % (command, self.state, ', '.join(Commands[command])))
        name = 'UID'
        typ, dat = self._simple_command(name, command, *args)
        if command in ('SEARCH', 'SORT', 'THREAD'):
            name = command
        else:
            name = 'FETCH'
        return self._untagged_response(typ, dat, name)

    def unsubscribe(self, mailbox):
        """Unsubscribe from old mailbox.
        
        (typ, [data]) = <instance>.unsubscribe(mailbox)
        """
        return self._simple_command('UNSUBSCRIBE', mailbox)

    def xatom(self, name, *args):
        """Allow simple extension commands
                notified by server in CAPABILITY response.
        
        Assumes command is legal in current state.
        
        (typ, [data]) = <instance>.xatom(name, arg, ...)
        
        Returns response appropriate to extension command `name'.
        """
        name = name.upper()
        if name not in Commands:
            Commands[name] = (self.state,)
        return self._simple_command(name, *args)

    def _append_untagged(self, typ, dat):
        if dat is None:
            dat = ''
        ur = self.untagged_responses
        if self.debug >= 5:
            self._mesg('untagged_responses[%s] %s += ["%s"]' % (typ, len(ur.get(typ, '')), dat))
        if typ in ur:
            ur[typ].append(dat)
        else:
            ur[typ] = [dat]
        return

    def _check_bye(self):
        bye = self.untagged_responses.get('BYE')
        if bye:
            raise self.abort(bye[-1])

    def _command(self, name, *args):
        if self.state not in Commands[name]:
            self.literal = None
            raise self.error('command %s illegal in state %s, only allowed in states %s' % (name, self.state, ', '.join(Commands[name])))
        for typ in ('OK', 'NO', 'BAD'):
            if typ in self.untagged_responses:
                del self.untagged_responses[typ]

        if 'READ-ONLY' in self.untagged_responses and not self.is_readonly:
            raise self.readonly('mailbox status changed to READ-ONLY')
        tag = self._new_tag()
        data = '%s %s' % (tag, name)
        for arg in args:
            if arg is None:
                continue
            data = '%s %s' % (data, self._checkquote(arg))

        literal = self.literal
        if literal is not None:
            self.literal = None
            if type(literal) is type(self._command):
                literator = literal
            else:
                literator = None
                data = '%s {%s}' % (data, len(literal))
        if self.debug >= 4:
            self._mesg('> %s' % data)
        else:
            self._log('> %s' % data)
        try:
            self.send('%s%s' % (data, CRLF))
        except (socket.error, OSError) as val:
            raise self.abort('socket error: %s' % val)

        if literal is None:
            return tag
        else:
            while 1:
                while self._get_response():
                    if self.tagged_commands[tag]:
                        return tag

                if literator:
                    literal = literator(self.continuation_response)
                if self.debug >= 4:
                    self._mesg('write literal size %s' % len(literal))
                try:
                    self.send(literal)
                    self.send(CRLF)
                except (socket.error, OSError) as val:
                    raise self.abort('socket error: %s' % val)

                if not literator:
                    break

            return tag

    def _command_complete(self, name, tag):
        if name != 'LOGOUT':
            self._check_bye()
        try:
            typ, data = self._get_tagged_response(tag)
        except self.abort as val:
            raise self.abort('command: %s => %s' % (name, val))
        except self.error as val:
            raise self.error('command: %s => %s' % (name, val))

        if name != 'LOGOUT':
            self._check_bye()
        if typ == 'BAD':
            raise self.error('%s command error: %s %s' % (name, typ, data))
        return (typ, data)

    def _get_response(self):
        resp = self._get_line()
        if self._match(self.tagre, resp):
            tag = self.mo.group('tag')
            if tag not in self.tagged_commands:
                raise self.abort('unexpected tagged response: %s' % resp)
            typ = self.mo.group('type')
            dat = self.mo.group('data')
            self.tagged_commands[tag] = (typ, [dat])
        else:
            dat2 = None
            if not self._match(Untagged_response, resp):
                if self._match(Untagged_status, resp):
                    dat2 = self.mo.group('data2')
            if self.mo is None:
                if self._match(Continuation, resp):
                    self.continuation_response = self.mo.group('data')
                    return
                raise self.abort("unexpected response: '%s'" % resp)
            typ = self.mo.group('type')
            dat = self.mo.group('data')
            if dat is None:
                dat = ''
            if dat2:
                dat = dat + ' ' + dat2
            while self._match(Literal, dat):
                size = int(self.mo.group('size'))
                if self.debug >= 4:
                    self._mesg('read literal size %s' % size)
                data = self.read(size)
                self._append_untagged(typ, (dat, data))
                dat = self._get_line()

            self._append_untagged(typ, dat)
        if typ in ('OK', 'NO', 'BAD') and self._match(Response_code, dat):
            self._append_untagged(self.mo.group('type'), self.mo.group('data'))
        if self.debug >= 1 and typ in ('NO', 'BAD', 'BYE'):
            self._mesg('%s response: %s' % (typ, dat))
        return resp

    def _get_tagged_response(self, tag):
        while 1:
            result = self.tagged_commands[tag]
            if result is not None:
                del self.tagged_commands[tag]
                return result
            self._check_bye()
            try:
                self._get_response()
            except self.abort as val:
                if self.debug >= 1:
                    self.print_log()
                raise

        return

    def _get_line(self):
        line = self.readline()
        if not line:
            raise self.abort('socket error: EOF')
        if not line.endswith('\r\n'):
            raise self.abort('socket error: unterminated line')
        line = line[:-2]
        if self.debug >= 4:
            self._mesg('< %s' % line)
        else:
            self._log('< %s' % line)
        return line

    def _match(self, cre, s):
        self.mo = cre.match(s)
        if self.mo is not None and self.debug >= 5:
            self._mesg("\tmatched r'%s' => %r" % (cre.pattern, self.mo.groups()))
        return self.mo is not None

    def _new_tag(self):
        tag = '%s%s' % (self.tagpre, self.tagnum)
        self.tagnum = self.tagnum + 1
        self.tagged_commands[tag] = None
        return tag

    def _checkquote(self, arg):
        if type(arg) is not type(''):
            return arg
        elif len(arg) >= 2 and (arg[0], arg[-1]) in (('(', ')'), ('"', '"')):
            return arg
        elif arg and self.mustquote.search(arg) is None:
            return arg
        else:
            return self._quote(arg)

    def _quote(self, arg):
        arg = arg.replace('\\', '\\\\')
        arg = arg.replace('"', '\\"')
        return '"%s"' % arg

    def _simple_command(self, name, *args):
        return self._command_complete(name, self._command(name, *args))

    def _untagged_response(self, typ, dat, name):
        if typ == 'NO':
            return (typ, dat)
        elif name not in self.untagged_responses:
            return (typ, [None])
        else:
            data = self.untagged_responses.pop(name)
            if self.debug >= 5:
                self._mesg('untagged_responses[%s] => %s' % (name, data))
            return (typ, data)

    def _mesg(self, s, secs = None):
        if secs is None:
            secs = time.time()
        tm = time.strftime('%M:%S', time.localtime(secs))
        sys.stderr.write('  %s.%02d %s\n' % (tm, secs * 100 % 100, s))
        sys.stderr.flush()
        return

    def _dump_ur(self, dict):
        l = dict.items()
        if not l:
            return
        t = '\n\t\t'
        l = map(lambda x: '%s: "%s"' % (x[0], x[1][0] and '" "'.join(x[1]) or ''), l)
        self._mesg('untagged responses dump:%s%s' % (t, t.join(l)))

    def _log(self, line):
        self._cmd_log[self._cmd_log_idx] = (line, time.time())
        self._cmd_log_idx += 1
        if self._cmd_log_idx >= self._cmd_log_len:
            self._cmd_log_idx = 0

    def print_log(self):
        self._mesg('last %d IMAP4 interactions:' % len(self._cmd_log))
        i, n = self._cmd_log_idx, self._cmd_log_len
        while n:
            try:
                self._mesg(*self._cmd_log[i])
            except:
                pass

            i += 1
            if i >= self._cmd_log_len:
                i = 0
            n -= 1


try:
    import ssl
except ImportError:
    pass
else:

    class IMAP4_SSL(IMAP4):
        """IMAP4 client class over SSL connection
        
        Instantiate with: IMAP4_SSL([host[, port[, keyfile[, certfile]]]])
        
                host - host's name (default: localhost);
                port - port number (default: standard IMAP4 SSL port).
                keyfile - PEM formatted file that contains your private key (default: None);
                certfile - PEM formatted certificate chain file (default: None);
        
        for more documentation see the docstring of the parent class IMAP4.
        """

        def __init__(self, host = '', port = IMAP4_SSL_PORT, keyfile = None, certfile = None):
            self.keyfile = keyfile
            self.certfile = certfile
            IMAP4.__init__(self, host, port)

        def open(self, host = '', port = IMAP4_SSL_PORT):
            """Setup connection to remote server on "host:port".
                (default: localhost:standard IMAP4 SSL port).
            This connection will be used by the routines:
                read, readline, send, shutdown.
            """
            self.host = host
            self.port = port
            self.sock = socket.create_connection((host, port))
            self.sslobj = ssl.wrap_socket(self.sock, self.keyfile, self.certfile)
            self.file = self.sslobj.makefile('rb')

        def read(self, size):
            """Read 'size' bytes from remote."""
            return self.file.read(size)

        def readline(self):
            """Read line from remote."""
            return self.file.readline()

        def send(self, data):
            """Send data to remote."""
            bytes = len(data)
            while bytes > 0:
                sent = self.sslobj.write(data)
                if sent == bytes:
                    break
                data = data[sent:]
                bytes = bytes - sent

        def shutdown(self):
            """Close I/O established in "open"."""
            self.file.close()
            self.sock.close()

        def socket(self):
            """Return socket instance used to connect to IMAP4 server.
            
            socket = <instance>.socket()
            """
            return self.sock

        def ssl(self):
            """Return SSLObject instance used to communicate with the IMAP4 server.
            
            ssl = ssl.wrap_socket(<instance>.socket)
            """
            return self.sslobj


    __all__.append('IMAP4_SSL')

class IMAP4_stream(IMAP4):
    """IMAP4 client class over a stream
    
    Instantiate with: IMAP4_stream(command)
    
            where "command" is a string that can be passed to subprocess.Popen()
    
    for more documentation see the docstring of the parent class IMAP4.
    """

    def __init__(self, command):
        self.command = command
        IMAP4.__init__(self)

    def open(self, host = None, port = None):
        """Setup a stream connection.
        This connection will be used by the routines:
            read, readline, send, shutdown.
        """
        self.host = None
        self.port = None
        self.sock = None
        self.file = None
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, close_fds=True)
        self.writefile = self.process.stdin
        self.readfile = self.process.stdout
        return

    def read(self, size):
        """Read 'size' bytes from remote."""
        return self.readfile.read(size)

    def readline(self):
        """Read line from remote."""
        return self.readfile.readline()

    def send(self, data):
        """Send data to remote."""
        self.writefile.write(data)
        self.writefile.flush()

    def shutdown(self):
        """Close I/O established in "open"."""
        self.readfile.close()
        self.writefile.close()
        self.process.wait()


class _Authenticator():
    """Private class to provide en/decoding
            for base64-based authentication conversation.
    """

    def __init__(self, mechinst):
        self.mech = mechinst

    def process(self, data):
        ret = self.mech(self.decode(data))
        if ret is None:
            return '*'
        else:
            return self.encode(ret)

    def encode(self, inp):
        oup = ''
        while inp:
            if len(inp) > 48:
                t = inp[:48]
                inp = inp[48:]
            else:
                t = inp
                inp = ''
            e = binascii.b2a_base64(t)
            if e:
                oup = oup + e[:-1]

        return oup

    def decode(self, inp):
        if not inp:
            return ''
        return binascii.a2b_base64(inp)


Mon2num = {'Jan': 1,
 'Feb': 2,
 'Mar': 3,
 'Apr': 4,
 'May': 5,
 'Jun': 6,
 'Jul': 7,
 'Aug': 8,
 'Sep': 9,
 'Oct': 10,
 'Nov': 11,
 'Dec': 12}

def Internaldate2tuple(resp):
    """Parse an IMAP4 INTERNALDATE string.
    
    Return corresponding local time.  The return value is a
    time.struct_time instance or None if the string has wrong format.
    """
    mo = InternalDate.match(resp)
    if not mo:
        return None
    else:
        mon = Mon2num[mo.group('mon')]
        zonen = mo.group('zonen')
        day = int(mo.group('day'))
        year = int(mo.group('year'))
        hour = int(mo.group('hour'))
        min = int(mo.group('min'))
        sec = int(mo.group('sec'))
        zoneh = int(mo.group('zoneh'))
        zonem = int(mo.group('zonem'))
        zone = (zoneh * 60 + zonem) * 60
        if zonen == '-':
            zone = -zone
        tt = (year,
         mon,
         day,
         hour,
         min,
         sec,
         -1,
         -1,
         -1)
        utc = time.mktime(tt)
        lt = time.localtime(utc)
        if time.daylight and lt[-1]:
            zone = zone + time.altzone
        else:
            zone = zone + time.timezone
        return time.localtime(utc - zone)


def Int2AP(num):
    """Convert integer to A-P string representation."""
    val = ''
    AP = 'ABCDEFGHIJKLMNOP'
    num = int(abs(num))
    while num:
        num, mod = divmod(num, 16)
        val = AP[mod] + val

    return val


def ParseFlags(resp):
    """Convert IMAP4 flags response to python tuple."""
    mo = Flags.match(resp)
    if not mo:
        return ()
    return tuple(mo.group('flags').split())


def Time2Internaldate(date_time):
    """Convert date_time to IMAP4 INTERNALDATE representation.
    
    Return string in form: '"DD-Mmm-YYYY HH:MM:SS +HHMM"'.  The
    date_time argument can be a number (int or float) representing
    seconds since epoch (as returned by time.time()), a 9-tuple
    representing local time (as returned by time.localtime()), or a
    double-quoted string.  In the last case, it is assumed to already
    be in the correct format.
    """
    if isinstance(date_time, (int, float)):
        tt = time.localtime(date_time)
    elif isinstance(date_time, (tuple, time.struct_time)):
        tt = date_time
    else:
        if isinstance(date_time, str) and (date_time[0], date_time[-1]) == ('"', '"'):
            return date_time
        raise ValueError('date_time not of a known type')
    dt = time.strftime('%d-%b-%Y %H:%M:%S', tt)
    if dt[0] == '0':
        dt = ' ' + dt[1:]
    if time.daylight and tt[-1]:
        zone = -time.altzone
    else:
        zone = -time.timezone
    return '"' + dt + ' %+03d%02d' % divmod(zone // 60, 60) + '"'


if __name__ == '__main__':
    import getopt, getpass
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'd:s:')
    except getopt.error as val:
        optlist, args = ((), ())

    stream_command = None
    for opt, val in optlist:
        if opt == '-d':
            Debug = int(val)
        elif opt == '-s':
            stream_command = val
            if not args:
                args = (stream_command,)

    if not args:
        args = ('',)
    host = args[0]
    USER = getpass.getuser()
    PASSWD = getpass.getpass('IMAP password for %s on %s: ' % (USER, host or 'localhost'))
    test_mesg = 'From: %(user)s@localhost%(lf)sSubject: IMAP4 test%(lf)s%(lf)sdata...%(lf)s' % {'user': USER,
     'lf': '\n'}
    test_seq1 = (('login', (USER, PASSWD)),
     ('create', ('/tmp/xxx 1',)),
     ('rename', ('/tmp/xxx 1', '/tmp/yyy')),
     ('CREATE', ('/tmp/yyz 2',)),
     ('append', ('/tmp/yyz 2',
       None,
       None,
       test_mesg)),
     ('list', ('/tmp', 'yy*')),
     ('select', ('/tmp/yyz 2',)),
     ('search', (None, 'SUBJECT', 'test')),
     ('fetch', ('1', '(FLAGS INTERNALDATE RFC822)')),
     ('store', ('1', 'FLAGS', '(\\Deleted)')),
     ('namespace', ()),
     ('expunge', ()),
     ('recent', ()),
     ('close', ()))
    test_seq2 = (('select', ()),
     ('response', ('UIDVALIDITY',)),
     ('uid', ('SEARCH', 'ALL')),
     ('response', ('EXISTS',)),
     ('append', (None,
       None,
       None,
       test_mesg)),
     ('recent', ()),
     ('logout', ()))

    def run(cmd, args):
        M._mesg('%s %s' % (cmd, args))
        typ, dat = getattr(M, cmd)(*args)
        M._mesg('%s => %s %s' % (cmd, typ, dat))
        if typ == 'NO':
            raise dat[0]
        return dat


    try:
        if stream_command:
            M = IMAP4_stream(stream_command)
        else:
            M = IMAP4(host)
        if M.state == 'AUTH':
            test_seq1 = test_seq1[1:]
        M._mesg('PROTOCOL_VERSION = %s' % M.PROTOCOL_VERSION)
        M._mesg('CAPABILITIES = %r' % (M.capabilities,))
        for cmd, args in test_seq1:
            run(cmd, args)

        for ml in run('list', ('/tmp/', 'yy%')):
            mo = re.match('.*"([^"]+)"$', ml)
            if mo:
                path = mo.group(1)
            else:
                path = ml.split()[-1]
            run('delete', (path,))

        for cmd, args in test_seq2:
            dat = run(cmd, args)
            if (cmd, args) != ('uid', ('SEARCH', 'ALL')):
                continue
            uid = dat[-1].split()
            if not uid:
                continue
            run('uid', ('FETCH', '%s' % uid[-1], '(FLAGS INTERNALDATE RFC822.SIZE RFC822.HEADER RFC822.TEXT)'))

        print '\nAll tests OK.'
    except:
        print '\nTests failed.'
        if not Debug:
            print '\nIf you would like to see debugging output,\ntry: %s -d5\n' % sys.argv[0]
        raise