"""Cookie manager for Grail.  This still doesn't do dialogs when preferences
are set to 'ask'; these are always treated as the 'always ...' option.
"""
__version__ = '$Revision: 2.1 $'


import cookielib
import grailutil
import os
import string


class CookieManager:
    GROUP = "cookies"

    def __init__(self, app):
        self.__db = cookielib.CookieDB()
        home = grailutil.gethome()
        fname = grailutil.which('cookies', [os.path.join(home, '.grail'),
                                            os.path.join(home, '.netscape')])
        if fname:
            cookielib.load(open(fname), self.__db)
        # for now, force it to private area for debugging
        fname = os.path.join(grailutil.getgraildir(), 'cookies')
        self.__db.set_filename(fname)
        app.register_on_exit(self.__close)
        self.__prefs = app.prefs
        self.on_prefs_change()
        self.__prefs.AddGroupCallback(self.GROUP, self.on_prefs_change)

    def __close(self):
        self.__db.save()

    def on_prefs_change(self):
        self.__on_receipt_action = self.__prefs.Get(
            self.GROUP, "receive-action")
        self.__on_request_action = self.__prefs.Get(
            self.GROUP, "send-action")

    def on_receipt(self, api, headers):
        if self.__on_receipt_action == "reject":
            return
        try:
            set_cookie_headers = headers.getallmatchingheaders('set-cookie')
        except AttributeError:
            # HTTP/0.9; headers is a real dictionary & never has cookies
            return
        if set_cookie_headers:
            print "Received set-cookie headers:"
            print set_cookie_headers
            for hdr in set_cookie_headers:
                cookies = cookielib.parse_cookies(
                    string.split(hdr, None, 1)[1])
                for cookie in cookies:
                    if not cookie.path:
                        cookie.path = api.selector
                    if not cookie.domain:
                        cookie.domain = string.lower(api.host)
                        cookie.isdomain = 0
                    # Set it in the database, but only if insecure;
                    # Grail doesn't yet support any secure transports.
                    if not cookie.secure:
                        print "Adding cookie: %s=%s" \
                              % (cookie.name, cookie.value)
                        self.__db.set_cookie(cookie)

    def on_request(self, api, request):
        if self.__on_request_action == "never-send":
            return
        cookies = self.__db.lookup(api.host, api.selector)
        if not cookies:
            return
        s = ''
        for cookie in cookies:
            if not hasattr(cookie, 'version'):
                s = "%s; %s=%s" % (s, cookie.name, cookie.value)
        if s:
            # strip off leading '; '
            s = s[2:]
            request.putheader('Cookie', s)
            print "put cookies:", s
        for cookie in cookies:
            if hasattr(cookie, 'version'):
                # cookie was *probably* set using Set-Cookie2: header
                s = "$Version=%s; %s=%s" \
                    % (cookie.version, cookie.name, cookie.value)
                if api.selector != cookie.path:
                    s = "%s; $Path=%s" % (s, cookie.path)
                if cookie.isdomain:
                    s = "%s; $Domain=%s" % (s, cookie.domain)
                if hasattr(cookie, 'port'):
                    s = '%s; $Port="%s"' % (s, cookie.port)
                request.putheader('Cookie', s)
                print "put cookie:", s
