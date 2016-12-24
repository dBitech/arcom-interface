"""
Web server function of arcom-server
"""
import logging
import ssl

try:                 # Python 3
  from http.server import (SimpleHTTPRequestHandler)
  from socketserver import ThreadingMixIn
  from xmlrpc.server import (SimpleXMLRPCServer,
                             SimpleXMLRPCRequestHandler)
except ImportError:  # Python 2
  from SimpleHTTPServer import SimpleHTTPRequestHandler
  from SocketServer import ThreadingMixIn
  from SimpleXMLRPCServer import (SimpleXMLRPCServer,
                                  SimpleXMLRPCRequestHandler)

log = logging.getLogger('arcom')

class ArcomWebServer(ThreadingMixIn, SimpleXMLRPCServer):
  """Basic XMLRPC and GET server class with localhost only access."""
  def verify_request(self, request, client_address):
    host, port = client_address
    print '\nconnection from %s:%s' % (host, port)
    return SimpleXMLRPCServer.verify_request(self, request, client_address)


class ArcomAuthorizingRequestHandler(SimpleHTTPRequestHandler,
                                     SimpleXMLRPCRequestHandler):
  """Add functionality to basic XMLRPC handler.
     We need to add authentication and handling of GETs.
     """
  rpc_paths = ('/RPC2')

  def __init__(self, *args, **kwargs):
    print 'ArcomAuthorizingRequestHandler.__init__ called'
    SimpleXMLRPCRequestHandler.__init__(self, *args, **kwargs)
    self.HTTPRequestHandler = SimpleHTTPRequestHandler.__init__(self, *args, **kwargs)

  def do_AUTHHEAD(self):
    print "do AUTHHEAD"
    self.send_response(401)
    self.send_header('WWW-Authenticate', 'Basic realm=\"Arcom\"')
    self.send_header('Content-type', 'text/html')
    self.end_headers()

  def do_GET(self):
    """Add authentication to the XMLRPC handlers."""
    #TODO(dpk): Need to implement proper AUTH here

    print 'do_GET: %s' % self
    #print '  headers: %s' % self.headers
    print '  path: %s' % self.path
    SimpleHTTPRequestHandler.do_GET(self)

  def do_POST(self):
    """Add authentication to the XMLRPC handlers."""
    #TODO(dpk): Need to implement proper AUTH here

    print 'do_POST: %s' % self
    #print '  headers: %s' % self.headers
    print '  path: %s' % self.path
    print '  content-length: %s' % int(self.headers.getheader('content-length', 0))
    SimpleXMLRPCRequestHandler.do_POST(self)


def run_server(arcom):
  """Creat and run the core XMLRPC webserver."""
  server = ArcomWebServer(('', 8080), ArcomAuthorizingRequestHandler)
  server.socket = ssl.wrap_socket (server.socket,
        keyfile="key.pem",
        certfile='cert.pem', server_side=True)
  server.register_introspection_functions()
  arcom.register_functions(server)
  server.serve_forever()
