import os
import sys
import signal
import BaseHTTPServer
import urllib2
import json
import subprocess
import time

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
    for _ in range(12):
        out = subprocess.check_output("aws autoscaling set-instance-protection --instance-ids \"" + INSTANCE_ID + "\" --auto-scaling-group-name \"" + ASG_NAME + "\" --protected-from-scale-in", shell=True, env=os.environ)

        # The instance may still be starting up? Wait a bit more.
        if "is not in InService " in out:
            time.sleep(10)
        else:
            break


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
        content = []
        if self.path.startswith("/setprotection/"):
            _id = self.path[15:]
            if len(PROTECTED_IDS) == 0:
                content.append("Setting instance protection (timeout=%ss)" % GLOBAL_TIMEOUT)
                signal.alarm(GLOBAL_TIMEOUT)
                set_protection()
            PROTECTED_IDS.add(_id)

        elif self.path.startswith("/unsetprotection/"):
            _id = self.path[17:]
            if _id in PROTECTED_IDS:
                PROTECTED_IDS.remove(_id)
                if len(PROTECTED_IDS) == 0:
                    content.append("Unsetting instance protection in %ss" % UNSET_TIMEOUT)
                    signal.alarm(UNSET_TIMEOUT)

        content.append(json.dumps({"ids": list(PROTECTED_IDS)}))

        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(("\n".join(content)) + "\n")


port = int(os.getenv("PORT") or 29456)
print "Server listening on %s" % port
httpd = BaseHTTPServer.HTTPServer(("127.0.0.1", port), HTTPHandler)
httpd.serve_forever()
