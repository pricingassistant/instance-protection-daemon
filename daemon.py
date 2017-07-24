import os
import sys
import signal
import BaseHTTPServer
import urllib2
import json

GLOBAL_TIMEOUT = int(os.getenv("GLOBAL_TIMEOUT") or 3600 * 4)
UNSET_TIMEOUT = int(os.getenv("UNSET_TIMEOUT") or 30)

ASG_NAME = sys.argv[1]
INSTANCE_ID = os.getenv("INSTANCE_ID") or urllib2.urlopen("http://169.254.169.254/latest/meta-data/instance-id").read()
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY
# AWS_DEFAULT_REGION

PROTECTED_IDS = set()


def set_protection():
    print "Setting protection"
    os.system("aws autoscaling set-instance-protection --instance-ids \"" + INSTANCE_ID + "\" --auto-scaling-group-name \"" + ASG_NAME + "\" --protected-from-scale-in")


def unset_protection():
    print "Unsetting protection"
    os.system("aws autoscaling set-instance-protection --instance-ids \"" + INSTANCE_ID + "\" --auto-scaling-group-name \"" + ASG_NAME + "\" --no-protected-from-scale-in")


def sig_handler(signum, frame):
    # if signum == 14:
    print 'Signal handler called with signal', signum
    unset_protection()

signal.signal(signal.SIGALRM, sig_handler)


class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/setprotection/"):
            _id = self.path[15:]
            if len(PROTECTED_IDS) == 0:
                signal.alarm(GLOBAL_TIMEOUT)
                set_protection()
            PROTECTED_IDS.add(_id)

        elif self.path.startswith("/unsetprotection/"):
            _id = self.path[17:]
            if _id in PROTECTED_IDS:
                PROTECTED_IDS.remove(_id)
                if len(PROTECTED_IDS) == 0:
                    signal.alarm(UNSET_TIMEOUT)

        self.send_response(200)
        self.wfile.write(json.dumps({"ids": list(PROTECTED_IDS)}))
        self.end_headers()

port = int(os.getenv("PORT") or 29456)
print "Server listening on %s" % port
httpd = BaseHTTPServer.HTTPServer(("127.0.0.1", port), HTTPHandler)
httpd.serve_forever()
